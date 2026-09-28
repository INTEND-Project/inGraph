from flask import Flask, request, jsonify, send_file, render_template
import requests
import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

from rdflib import Graph
from rdflib.namespace import RDF, Namespace
from pyshacl import validate as shacl_validate

app = Flask(__name__)

# Configuration
GRAPHDB_BASE_URL = os.getenv("GRAPHDB_BASE_URL", "http://localhost:7200")
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'jsonld', 'json', 'sparql', 'rq'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Ontology/SHACL validation store -----------------------------------
#
# An ontology (TBox + SHACL shapes) can be loaded once via POST
# /ontology/load and is then used to validate every subsequent /upload
# (and any ad-hoc /validate call) against it. Validation is "soft": it
# NEVER blocks an upload, it only attaches a violations report to the
# response -- see README.md for the reasoning. Files are persisted to
# disk under ONTOLOGY_STORE_DIR (which lives inside the bind-mounted
# project directory in docker-compose.yml, so it survives container
# restarts) and re-hydrated into in-memory rdflib Graphs both at startup
# and after every /ontology/load call.
SH = Namespace("http://www.w3.org/ns/shacl#")
ONTOLOGY_STORE_DIR = os.getenv("ONTOLOGY_STORE_DIR", "ontology_store")
ONTOLOGY_DIR = os.path.join(ONTOLOGY_STORE_DIR, "ontology")
SHAPES_DIR = os.path.join(ONTOLOGY_STORE_DIR, "shapes")
os.makedirs(ONTOLOGY_DIR, exist_ok=True)
os.makedirs(SHAPES_DIR, exist_ok=True)

_ontology_graph = Graph()
_shapes_graph = Graph()
_ontology_meta: Dict[str, Any] = {"loaded": False, "ontology_files": [], "shapes_files": []}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _load_graph_from_dir(directory: str) -> Tuple[Graph, List[str]]:
    """Parse every file in `directory` (JSON-LD) into one combined Graph."""
    g = Graph()
    filenames = []
    for fname in sorted(os.listdir(directory)):
        path = os.path.join(directory, fname)
        if os.path.isfile(path):
            g.parse(path, format="json-ld")
            filenames.append(fname)
    return g, filenames


def _hydrate_ontology_store() -> None:
    """(Re)build the in-memory ontology/shapes graphs from whatever is
    currently on disk under ONTOLOGY_DIR/SHAPES_DIR. Called at startup (so
    a previously loaded ontology survives an app restart) and again at the
    end of /ontology/load and /ontology (DELETE)."""
    global _ontology_graph, _shapes_graph, _ontology_meta
    ontology_graph, ontology_files = _load_graph_from_dir(ONTOLOGY_DIR)
    shapes_graph, shapes_files = _load_graph_from_dir(SHAPES_DIR)
    _ontology_graph = ontology_graph
    _shapes_graph = shapes_graph
    _ontology_meta = {
        "loaded": bool(ontology_files or shapes_files),
        "ontology_files": ontology_files,
        "shapes_files": shapes_files,
    }


def _parse_shacl_report(results_graph: Graph, conforms: bool) -> Dict[str, Any]:
    """Turn pyshacl's results_graph into a plain, JSON-friendly structure
    instead of only the raw human-readable report text.

    Walks only the TOP-LEVEL results (report -> sh:result -> ...), matching
    pyshacl's own "Results (N)" count in its text report. Iterating every
    node typed sh:ValidationResult instead would double count: a
    QualifiedValueShapeConstraintComponent violation nests a second, full
    sh:ValidationResult under sh:detail to explain what actually failed --
    that nested node is typed sh:ValidationResult too, but it is a detail
    of its parent result, not an independent violation. Each top-level
    violation's own sh:detail messages (if any) are folded into a
    "details" list instead, so that explanatory information is not lost."""
    def _get(node, pred):
        v = results_graph.value(node, pred)
        return str(v) if v is not None else None

    violations = []
    report_node = results_graph.value(predicate=RDF.type, object=SH.ValidationReport)
    result_nodes = results_graph.objects(report_node, SH.result) if report_node is not None else []
    for result in result_nodes:
        details = [
            _get(d, SH.resultMessage)
            for d in results_graph.objects(result, SH.detail)
            if _get(d, SH.resultMessage)
        ]
        violations.append({
            "focusNode": _get(result, SH.focusNode),
            "resultPath": _get(result, SH.resultPath),
            "value": _get(result, SH.value),
            "resultMessage": _get(result, SH.resultMessage),
            "resultSeverity": _get(result, SH.resultSeverity),
            "sourceConstraintComponent": _get(result, SH.sourceConstraintComponent),
            "sourceShape": _get(result, SH.sourceShape),
            "details": details,
        })
    return {"conforms": conforms, "violation_count": len(violations), "violations": violations}


def _run_shacl_validation(kg_graph: Graph) -> Dict[str, Any]:
    """Validate kg_graph (combined with the loaded ontology TBox, so
    sh:class / sh:targetClass checks that rely on rdfs:subClassOf can
    fire) against the loaded SHACL shapes. Caller must check
    _ontology_meta['loaded'] first."""
    combined = Graph()
    for t in _ontology_graph:
        combined.add(t)
    for t in kg_graph:
        combined.add(t)

    conforms, results_graph, results_text = shacl_validate(
        data_graph=combined,
        shacl_graph=_shapes_graph,
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )
    report = _parse_shacl_report(results_graph, conforms)
    report["report_text"] = results_text
    return report


# Re-hydrate from disk at import time (covers both `python inGraphApp.py`
# and running under a WSGI server that imports this module directly).
_hydrate_ontology_store()

def make_graphdb_request(method: str, url: str, headers: Dict[str, str] = None,
                        data: str = None, files: Dict = None) -> requests.Response:
    """Make HTTP request to GraphDB with error handling.

    IMPORTANT: if `data` is a plain `str`, it is explicitly UTF-8-encoded to
    bytes before being handed to requests. requests==2.31.0 (pinned in
    requirements.txt) does not reliably UTF-8-encode a str body itself --
    confirmed by reproduction: any non-ASCII character (an em-dash in an
    rdfs:comment, an accented city name like "Malmoe"/"Umea" in the Telenor
    data, ...) makes GraphDB reject the request as "Could not parse
    JSONLD" (or a malformed SPARQL request for /query and /update) even
    though the exact same content succeeds when sent as bytes. Encoding
    explicitly here fixes it once for every caller instead of requiring
    each call site to remember to do it."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            if files:
                response = requests.post(url, headers=headers, files=files)
            else:
                response = requests.post(url, headers=headers, data=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"GraphDB request failed: {str(e)}")
        raise

@app.route('/', methods=['GET'])
def index():
    """Serve the web interface"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        response = requests.get(f"{GRAPHDB_BASE_URL}/rest/repositories", timeout=5)
        if response.status_code == 200:
            return jsonify({"status": "healthy", "graphdb": "connected"}), 200
        else:
            return jsonify({"status": "unhealthy", "graphdb": "disconnected"}), 503
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route('/repositories', methods=['GET'])
def list_repositories():
    """List all available GraphDB repositories"""
    try:
        response = make_graphdb_request('GET', f"{GRAPHDB_BASE_URL}/rest/repositories")
        repositories = response.json()
        return jsonify({
            "repositories": [repo['id'] for repo in repositories],
            "count": len(repositories),
            "details": repositories
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch repositories: {str(e)}"}), 500

@app.route('/upload', methods=['POST'])
def upload_jsonld():
    """Upload JSON-LD file to specified repository.

    If an ontology has been loaded via POST /ontology/load, the file is
    ALSO checked against it with SHACL and the violations report is
    attached to the response as "validation" -- this is informational
    only and never blocks or undoes the upload above it, even when a KG
    does not conform (see README.md: "soft" validation)."""
    # Get repository name from form data or default
    repository = request.form.get('repository', 'second-graph')

    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use: jsonld, json"}), 400

    try:
        # Read file content
        file_content = file.read().decode('utf-8')

        # Validate JSON-LD
        try:
            json.loads(file_content)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format"}), 400

        # Upload to GraphDB
        headers = {'Content-Type': 'application/ld+json'}
        url = f"{GRAPHDB_BASE_URL}/repositories/{repository}/statements"

        response = make_graphdb_request('POST', url, headers=headers, data=file_content)

        # Count triples for confirmation
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        count_headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        count_response = make_graphdb_request('POST',
                                            f"{GRAPHDB_BASE_URL}/repositories/{repository}",
                                            headers=count_headers,
                                            data=count_query)

        count_result = count_response.json()
        total_triples = count_result['results']['bindings'][0]['count']['value']

        result = {
            "message": "File uploaded successfully",
            "repository": repository,
            "filename": file.filename,
            "total_triples": total_triples,
            "status": "success"
        }

        # SHACL validation is best-effort and purely informational: any
        # failure here is reported inside "validation" but must never
        # change the HTTP status or undo the upload that already succeeded.
        if _ontology_meta["loaded"]:
            try:
                kg_graph = Graph()
                kg_graph.parse(data=file_content, format='json-ld')
                result["validation"] = _run_shacl_validation(kg_graph)
            except Exception as e:
                logger.warning(f"Post-upload SHACL validation could not run: {str(e)}")
                result["validation"] = {"error": f"Validation could not run: {str(e)}"}
        else:
            result["validation"] = {"skipped": "No ontology loaded. POST to /ontology/load to enable validation."}

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route('/ontology/load', methods=['POST'])
def load_ontology():
    """Load the ontology TBox + SHACL shapes used to validate future KG
    uploads/checks. Accepts any number of JSON-LD files under the
    'ontology_files' and 'shapes_files' multipart fields.

    Replaces (does not merge with) any previously loaded ontology: this
    is "load the ontology", a single deliberate action, not an
    accumulation of fragments across calls. All files are parsed and
    checked BEFORE anything is written to the on-disk store, so a
    malformed file in this call cannot corrupt or partially overwrite a
    previously good ontology -- the call either fully replaces the store
    or fails with nothing changed."""
    ontology_files = request.files.getlist('ontology_files')
    shapes_files = request.files.getlist('shapes_files')

    if not ontology_files and not shapes_files:
        return jsonify({"error": "Provide at least one file under 'ontology_files' and/or 'shapes_files'"}), 400

    for f in ontology_files + shapes_files:
        if not f.filename or not allowed_file(f.filename):
            return jsonify({"error": f"File type not allowed for '{f.filename}'. Use: jsonld, json"}), 400

    try:
        ontology_contents = []
        for f in ontology_files:
            content = f.read().decode('utf-8')
            Graph().parse(data=content, format='json-ld')  # raises on malformed JSON-LD
            ontology_contents.append((os.path.basename(f.filename), content))
        shapes_contents = []
        for f in shapes_files:
            content = f.read().decode('utf-8')
            Graph().parse(data=content, format='json-ld')
            shapes_contents.append((os.path.basename(f.filename), content))
    except Exception as e:
        return jsonify({"error": f"One or more files are not valid JSON-LD, nothing was changed: {str(e)}"}), 400

    try:
        for d in (ONTOLOGY_DIR, SHAPES_DIR):
            for fname in os.listdir(d):
                os.remove(os.path.join(d, fname))
        for fname, content in ontology_contents:
            with open(os.path.join(ONTOLOGY_DIR, fname), 'w', encoding='utf-8') as out:
                out.write(content)
        for fname, content in shapes_contents:
            with open(os.path.join(SHAPES_DIR, fname), 'w', encoding='utf-8') as out:
                out.write(content)

        _hydrate_ontology_store()

        return jsonify({
            "message": "Ontology loaded successfully (replaced any previously loaded ontology)",
            "ontology_files": _ontology_meta["ontology_files"],
            "shapes_files": _ontology_meta["shapes_files"],
            "ontology_triples": len(_ontology_graph),
            "shapes_triples": len(_shapes_graph),
            "status": "success"
        }), 200
    except Exception as e:
        logger.error(f"Ontology load failed: {str(e)}")
        return jsonify({"error": f"Ontology load failed: {str(e)}"}), 500


@app.route('/ontology/status', methods=['GET'])
def ontology_status():
    """Report whether an ontology is currently loaded and its basic stats."""
    return jsonify({
        "loaded": _ontology_meta["loaded"],
        "ontology_files": _ontology_meta["ontology_files"],
        "shapes_files": _ontology_meta["shapes_files"],
        "ontology_triples": len(_ontology_graph),
        "shapes_triples": len(_shapes_graph),
    }), 200


@app.route('/ontology', methods=['DELETE'])
def clear_ontology():
    """Remove the currently loaded ontology + shapes. Future /upload and
    /validate calls skip validation (reporting it as skipped) until a new
    ontology is loaded."""
    try:
        for d in (ONTOLOGY_DIR, SHAPES_DIR):
            for fname in os.listdir(d):
                os.remove(os.path.join(d, fname))
        _hydrate_ontology_store()
        return jsonify({"message": "Ontology cleared", "status": "success"}), 200
    except Exception as e:
        logger.error(f"Failed to clear ontology: {str(e)}")
        return jsonify({"error": f"Failed to clear ontology: {str(e)}"}), 500


@app.route('/validate', methods=['POST'])
def validate_kg():
    """Validate a JSON-LD/JSON KG file against the currently loaded
    ontology + SHACL shapes WITHOUT uploading it anywhere (dry run). Like
    /upload's validation, this always returns the full report -- there is
    nothing to block here, this endpoint only checks and reports."""
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use: jsonld, json"}), 400
    if not _ontology_meta["loaded"]:
        return jsonify({"error": "No ontology loaded. POST to /ontology/load first."}), 409

    try:
        content = file.read().decode('utf-8')
        kg_graph = Graph()
        kg_graph.parse(data=content, format='json-ld')
    except Exception as e:
        return jsonify({"error": f"Could not parse file as JSON-LD: {str(e)}"}), 400

    try:
        report = _run_shacl_validation(kg_graph)
        return jsonify({
            "filename": file.filename,
            "kg_triples": len(kg_graph),
            "validation": report,
            "status": "success"
        }), 200
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500

@app.route('/query', methods=['POST'])
def execute_sparql_query():
    """Execute SPARQL SELECT/ASK/CONSTRUCT/DESCRIBE query"""
    repository = request.form.get('repository', 'second-graph')

    # Handle file upload or direct query
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Use: sparql, rq"}), 400
        query = file.read().decode('utf-8')
    elif 'query' in request.form:
        query = request.form['query']
    else:
        return jsonify({"error": "No query provided (file or query parameter)"}), 400

    # Get output format
    output_format = request.form.get('format', 'json')

    accept_headers = {
        'json': 'application/sparql-results+json',
        'xml': 'application/sparql-results+xml',
        'csv': 'text/csv',
        'turtle': 'text/turtle',
        'rdf': 'application/rdf+xml'
    }

    accept_header = accept_headers.get(output_format, 'application/sparql-results+json')

    try:
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': accept_header
        }

        url = f"{GRAPHDB_BASE_URL}/repositories/{repository}"
        response = make_graphdb_request('POST', url, headers=headers, data=query)

        # Return appropriate response based on format
        if output_format == 'json':
            # Always try to parse JSON for SPARQL results
            try:
                results_data = response.json()
            except:
                results_data = response.text

            return jsonify({
                "query": query,
                "repository": repository,
                "results": results_data,
                "status": "success"
            }), 200
        else:
            return response.text, 200, {'Content-Type': accept_header}

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return jsonify({"error": f"Query execution failed: {str(e)}"}), 500

@app.route('/update', methods=['POST'])
def execute_sparql_update():
    """Execute SPARQL INSERT/DELETE/UPDATE operations"""
    repository = request.form.get('repository', 'second-graph')

    # Handle file upload or direct query
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Use: sparql, rq"}), 400
        update_query = file.read().decode('utf-8')
    elif 'query' in request.form:
        update_query = request.form['query']
    else:
        return jsonify({"error": "No update query provided (file or query parameter)"}), 400

    try:
        headers = {'Content-Type': 'application/sparql-update'}
        url = f"{GRAPHDB_BASE_URL}/repositories/{repository}/statements"

        response = make_graphdb_request('POST', url, headers=headers, data=update_query)

        return jsonify({
            "message": "Update operation completed successfully",
            "query": update_query,
            "repository": repository,
            "status": "success"
        }), 200

    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
        return jsonify({"error": f"Update operation failed: {str(e)}"}), 500

@app.route('/repository/<repository_name>/size', methods=['GET'])
def get_repository_size(repository_name: str):
    """Get the number of triples in a repository"""
    try:
        response = make_graphdb_request('GET', f"{GRAPHDB_BASE_URL}/repositories/{repository_name}/size")
        return jsonify({
            "repository": repository_name,
            "size": int(response.text),
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get repository size: {str(e)}"}), 500

@app.route('/repository/<repository_name>/clear', methods=['DELETE'])
def clear_repository(repository_name: str):
    """Clear all data from a repository"""
    try:
        headers = {'Content-Type': 'application/sparql-update'}
        clear_query = "DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }"
        url = f"{GRAPHDB_BASE_URL}/repositories/{repository_name}/statements"

        response = make_graphdb_request('POST', url, headers=headers, data=clear_query)

        return jsonify({
            "message": f"Repository '{repository_name}' cleared successfully",
            "repository": repository_name,
            "status": "success"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to clear repository: {str(e)}"}), 500

@app.route('/repository/<repository_name>/info', methods=['GET'])
def get_repository_info(repository_name: str):
    """Get detailed information about a specific repository"""
    try:
        # Get repository details
        response = make_graphdb_request('GET', f"{GRAPHDB_BASE_URL}/rest/repositories")
        repositories = response.json()

        repo_info = next((repo for repo in repositories if repo['id'] == repository_name), None)
        if not repo_info:
            return jsonify({"error": f"Repository '{repository_name}' not found"}), 404

        # Get repository size
        try:
            size_response = make_graphdb_request('GET', f"{GRAPHDB_BASE_URL}/repositories/{repository_name}/size")
            repo_info['triple_count'] = int(size_response.text)
        except:
            repo_info['triple_count'] = "Unknown"

        # Get namespace info
        try:
            ns_query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
            ns_headers = {
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            }
            ns_response = make_graphdb_request('POST',
                                             f"{GRAPHDB_BASE_URL}/repositories/{repository_name}",
                                             headers=ns_headers,
                                             data=ns_query)

            ns_result = ns_response.json()
            repo_info['named_graphs'] = [binding['g']['value'] for binding in ns_result['results']['bindings']]
        except:
            repo_info['named_graphs'] = []

        return jsonify({
            "repository": repository_name,
            "info": repo_info,
            "status": "success"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get repository info: {str(e)}"}), 500

@app.route('/repositories/active', methods=['GET'])
def list_active_repositories():
    """List only active/running repositories"""
    try:
        response = make_graphdb_request('GET', f"{GRAPHDB_BASE_URL}/rest/repositories")
        repositories = response.json()

        active_repos = [repo for repo in repositories if repo.get('state') == 'RUNNING']

        return jsonify({
            "active_repositories": [repo['id'] for repo in active_repos],
            "count": len(active_repos),
            "details": active_repos
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch active repositories: {str(e)}"}), 500

@app.route('/repositories/create', methods=['POST'])
def create_repository():
    """Create a new GraphDB repository"""
    repository_id = request.form.get('id')
    repository_title = request.form.get('title', repository_id)

    if not repository_id:
        return jsonify({"error": "Repository ID is required"}), 400

    # Basic repository configuration
    config = {
        "id": repository_id,
        "title": repository_title,
        "type": "graphdb",
        "params": {
            "baseURL": {
                "name": "baseURL",
                "label": "Base URL",
                "value": "http://example.org/owlim#"
            },
            "defaultNS": {
                "name": "defaultNS",
                "label": "Default namespaces for imports(';' delimited)",
                "value": ""
            },
            "imports": {
                "name": "imports",
                "label": "Imported RDF files(';' delimited)",
                "value": ""
            },
            "ruleset": {
                "name": "ruleset",
                "label": "Ruleset",
                "value": request.form.get('ruleset', 'rdfsplus-optimized')
            },
            "storageFolder": {
                "name": "storageFolder",
                "label": "Storage folder",
                "value": "storage"
            },
            "repositoryType": {
                "name": "repositoryType",
                "label": "Repository type",
                "value": "file-repository"
            },
            "checkForInconsistencies": {
                "name": "checkForInconsistencies",
                "label": "Enable consistency checks",
                "value": "false"
            },
            "disableSameAs": {
                "name": "disableSameAs",
                "label": "Disable owl:sameAs",
                "value": "true"
            },
            "enablePredicateList": {
                "name": "enablePredicateList",
                "label": "Enable predicate list index",
                "value": "true"
            },
            "enableLiteralIndex": {
                "name": "enableLiteralIndex",
                "label": "Enable literal index",
                "value": "true"
            },
            "enableContextIndex": {
                "name": "enableContextIndex",
                "label": "Enable context index",
                "value": "true"
            },
            "readOnly": {
                "name": "readOnly",
                "label": "Read-only",
                "value": "false"
            }
        }
    }

    try:
        headers = {'Content-Type': 'application/json'}
        url = f"{GRAPHDB_BASE_URL}/rest/repositories"

        response = make_graphdb_request('POST', url, headers=headers, data=json.dumps(config))

        return jsonify({
            "message": f"Repository '{repository_id}' created successfully",
            "repository": repository_id,
            "config": config,
            "status": "success"
        }), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create repository: {str(e)}"}), 500

@app.route('/examples', methods=['GET'])
def get_examples():
    """Get API usage examples"""
    examples = {
        "upload_jsonld": {
            "description": "Upload JSON-LD file",
            "curl": 'curl -X POST http://0.0.0.0:5000/upload -F "repository=second-graph" -F "file=@FILL__KG.jsonld"',
            "python": '''
import requests
files = {"file": open("FILL__KG.jsonld", "rb")}
data = {"repository": "second-graph"}
response = requests.post("http://0.0.0.0:5000/upload", files=files, data=data)
'''
        },
        "sparql_query": {
            "description": "Execute SPARQL query from file",
            "curl": 'curl -X POST http://0.0.0.0:5000/query -F "repository=second-graph" -F "file=@machine5-query.sparql" -F "format=json"',
            "python": '''
import requests
files = {"file": open("machine5-query.sparql", "rb")}
data = {"repository": "second-graph", "format": "json"}
response = requests.post("http://0.0.0.0:5000/query", files=files, data=data)
'''
        },
        "sparql_update": {
            "description": "Execute SPARQL update/delete",
            "curl": 'curl -X POST http://0.0.0.0:5000/update -F "repository=second-graph" -F "file=@query_delete.sparql"',
            "python": '''
import requests
files = {"file": open("query_delete.sparql", "rb")}
data = {"repository": "second-graph"}
response = requests.post("http://0.0.0.0:5000/update", files=files, data=data)
'''
        },
        "load_ontology": {
            "description": "Load the ontology TBox + SHACL shapes used to validate future uploads (replaces any previously loaded ontology)",
            "curl": 'curl -X POST http://0.0.0.0:5000/ontology/load '
                    '-F "ontology_files=@ontology/intend.jsonld" -F "ontology_files=@extensions/intend-fill-extension.jsonld" '
                    '-F "shapes_files=@shapes/intend-shapes-fill-extension.jsonld"',
            "python": '''
import requests
files = [
    ("ontology_files", open("ontology/intend.jsonld", "rb")),
    ("ontology_files", open("extensions/intend-fill-extension.jsonld", "rb")),
    ("shapes_files", open("shapes/intend-shapes-fill-extension.jsonld", "rb")),
]
response = requests.post("http://0.0.0.0:5000/ontology/load", files=files)
'''
        },
        "validate_kg": {
            "description": "Check a KG file against the loaded ontology without uploading it anywhere (dry run)",
            "curl": 'curl -X POST http://0.0.0.0:5000/validate -F "file=@FILL__KG.jsonld"',
            "python": '''
import requests
files = {"file": open("FILL__KG.jsonld", "rb")}
response = requests.post("http://0.0.0.0:5000/validate", files=files)
'''
        }
    }
    return jsonify(examples), 200

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404
@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 Knowledge Graph Visualizer starting...")
    print("🌐 Web Interface: http://0.0.0.0:5000")
    print("📚 API endpoints:")
    print("  GET  /                    - Web interface")
    print("  GET  /health              - Health check")
    print("  GET  /repositories        - List repositories")
    print("  POST /upload              - Upload JSON-LD file (+ SHACL report if an ontology is loaded)")
    print("  POST /query               - Execute SPARQL query")
    print("  POST /update              - Execute SPARQL update")
    print("  GET  /repository/<name>/size - Get repository size")
    print("  DELETE /repository/<name>/clear - Clear repository")
    print("  POST /ontology/load       - Load ontology TBox + SHACL shapes for validation")
    print("  GET  /ontology/status     - Check whether an ontology is loaded")
    print("  DELETE /ontology          - Clear the loaded ontology")
    print("  POST /validate            - Check a KG against the loaded ontology (dry run)")
    print("  GET  /examples            - API usage examples")
    print(f"\n📦 Ontology store: {'loaded (' + str(len(_ontology_meta['ontology_files'])) + ' ontology + ' + str(len(_ontology_meta['shapes_files'])) + ' shapes files)' if _ontology_meta['loaded'] else 'empty -- POST /ontology/load to enable validation'}")
    print("\n✨ Open http://localhost:5000 in your browser to start visualizing!")

    app.run(debug=True, host='0.0.0.0', port=5000)
