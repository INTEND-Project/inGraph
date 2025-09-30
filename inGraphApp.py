from flask import Flask, request, jsonify, send_file
import requests
import os
import json
import logging
from typing import Optional, Dict, Any

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

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def make_graphdb_request(method: str, url: str, headers: Dict[str, str] = None, 
                        data: str = None, files: Dict = None) -> requests.Response:
    """Make HTTP request to GraphDB with error handling"""
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
    """Upload JSON-LD file to specified repository"""
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
        
        return jsonify({
            "message": "File uploaded successfully",
            "repository": repository,
            "filename": file.filename,
            "total_triples": total_triples,
            "status": "success"
        }), 200
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

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
            return jsonify({
                "query": query,
                "repository": repository,
                "results": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
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
    print("🚀 GraphDB REST API starting...")
    print("📚 Available endpoints:")
    print("  GET  /health              - Health check")
    print("  GET  /repositories        - List repositories")
    print("  POST /upload              - Upload JSON-LD file")
    print("  POST /query               - Execute SPARQL query")
    print("  POST /update              - Execute SPARQL update")
    print("  GET  /repository/<name>/size - Get repository size")
    print("  DELETE /repository/<name>/clear - Clear repository")
    print("  GET  /examples            - API usage examples")
    print("\n🌐 Server running on http://0.0.0.0:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)