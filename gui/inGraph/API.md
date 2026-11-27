# inGraph HTTP API reference

inGraph is a Flask service in front of a GraphDB triplestore. It exposes 16 HTTP endpoints for:

- managing GraphDB repositories;
- uploading JSON-LD knowledge graphs;
- running SPARQL queries and updates;
- validating KGs against the INTEND ontology with SHACL.

The web interface at `/` is a client of this same API. Everything it does can also be done with `curl` or a script.

Source of truth: [`inGraphApp.py`](inGraphApp.py). If this file and the code disagree, the code wins. A machine-readable OpenAPI 3 (Swagger) version of this reference is in [`openapi.yaml`](openapi.yaml).

## Base URL

| How it runs | Base URL |
|---|---|
| `docker compose up` (dev stack, default) | `http://localhost:5050` |
| `python inGraphApp.py` (no Docker) | `http://localhost:5000` |
| `docker-compose.prod.yml` | `http://<host>:80` |

The examples below use `http://localhost:5050` and assume you run them from `gui/inGraph/`.

## Conventions

- **Requests are form fields, not JSON.**
  - Endpoints that take files expect `multipart/form-data` (`curl -F`).
  - Endpoints without files also accept `application/x-www-form-urlencoded` (`curl --data-urlencode`).
  - A JSON request body is ignored.
- **Responses are JSON.** The one exception is `/query` with a non-JSON `format`.
  - Success responses carry `"status": "success"`.
  - Errors are `{"error": "<message>"}` with a 4xx/5xx status code.
- **GraphDB errors come back as `500`.** This includes an unknown repository or data GraphDB rejects.
  - `error` contains the HTTP status GraphDB answered with and the URL that was called.
  - GraphDB's own explanation is not passed through. To see it, run `docker compose logs graphdb`.
- **Accepted file extensions:** `.jsonld`, `.json`, `.sparql`, `.rq`.
  - The same list applies to every file field.
  - The content is then checked for what the endpoint expects (JSON / JSON-LD / SPARQL).
- **Maximum request size:** 16 MB. A larger request gets `413 {"error": "File too large"}`.
- **`repository` defaults to `second-graph`** on `/upload`, `/query` and `/update` when the field is omitted. Always pass it explicitly.
- **No authentication.** Any client that can reach the port can write to or clear any repository.
- **No CORS headers.** A web page served from another origin cannot call the API from the browser. Server-to-server calls and the built-in web interface are unaffected.
- **Unknown paths** return `404 {"error": "Endpoint not found"}`.

## Endpoint overview

| Method | Path | Purpose |
|---|---|---|
| GET | [`/`](#get-) | Web interface (HTML) |
| GET | [`/health`](#get-health) | Service and GraphDB status |
| GET | [`/examples`](#get-examples) | Usage snippets, as JSON |
| GET | [`/repositories`](#get-repositories) | List all GraphDB repositories |
| GET | [`/repositories/active`](#get-repositoriesactive) | List running repositories only |
| POST | [`/repositories/create`](#post-repositoriescreate) | Create a repository |
| GET | [`/repository/<name>/info`](#get-repositorynameinfo) | Repository details, triple count, named graphs |
| GET | [`/repository/<name>/size`](#get-repositorynamesize) | Number of triples in a repository |
| DELETE | [`/repository/<name>/clear`](#delete-repositorynameclear) | Delete all triples in a repository |
| POST | [`/upload`](#post-upload) | Upload a JSON-LD file (+ SHACL report if an ontology is loaded) |
| POST | [`/query`](#post-query) | Run a SPARQL SELECT / ASK / CONSTRUCT / DESCRIBE |
| POST | [`/update`](#post-update) | Run a SPARQL INSERT / DELETE update |
| POST | [`/ontology/load`](#post-ontologyload) | Load the ontology TBox + SHACL shapes used for validation |
| GET | [`/ontology/status`](#get-ontologystatus) | Is an ontology loaded, and what |
| DELETE | [`/ontology`](#delete-ontology) | Unload the ontology |
| POST | [`/validate`](#post-validate) | Validate a KG file without uploading it (dry run) |

---

## Service

### `GET /`

Serves the web interface: repository browser, ontology & validation panel, SPARQL editor and graph view.

### `GET /health`

Checks that the app is up and can reach GraphDB.

```bash
curl http://localhost:5050/health
```

| Status | Body |
|---|---|
| 200 | `{"status": "healthy", "graphdb": "connected"}` |
| 503 | `{"status": "unhealthy", "graphdb": "disconnected"}` or `{"status": "unhealthy", "error": "..."}` |

### `GET /examples`

Returns a JSON object of `curl` and Python snippets for:

- `upload_jsonld`
- `sparql_query`
- `sparql_update`
- `load_ontology`
- `validate_kg`

The snippets use `http://0.0.0.0:5000`. Adjust the port when running under Docker.

---

## Repositories

### `GET /repositories`

Lists every repository GraphDB knows about.

```bash
curl http://localhost:5050/repositories
```

```json
{
  "repositories": ["FILL", "GATE", "TELENOR"],
  "count": 3,
  "details": [ { "id": "FILL", "title": "FILL", "state": "RUNNING", "...": "GraphDB's own repository fields" } ]
}
```

Errors: `500` if GraphDB cannot be reached.

### `GET /repositories/active`

Same as above, filtered to repositories whose `state` is `RUNNING`. The keys are `active_repositories`, `count` and `details`.

### `POST /repositories/create`

Creates a GraphDB repository.

| Field | Required | Default | Notes |
|---|---|---|---|
| `id` | yes | | Repository ID, used as `<name>` everywhere else |
| `title` | no | same as `id` | Human-readable title |
| `ruleset` | no | `rdfsplus-optimized` | Any GraphDB ruleset name, e.g. `empty`, `rdfsplus-optimized`, `owl2-rl` |

The repository's other settings are fixed by the app:

- file repository;
- `owl:sameAs` disabled;
- predicate, literal and context indexes enabled;
- not read-only.

```bash
curl -X POST http://localhost:5050/repositories/create -F id=FILL -F ruleset=rdfsplus-optimized
```

| Status | Body |
|---|---|
| 201 | `{"message": "Repository 'FILL' created successfully", "repository": "FILL", "config": {…}, "status": "success"}` |
| 400 | `{"error": "Repository ID is required"}` |
| 500 | GraphDB refused. This is also what you get if the repository already exists. |

With a reasoning ruleset, GraphDB adds a fixed set of axiomatic triples to the repository. This is why `COUNT(*)` on a fresh `rdfsplus-optimized` repository is not 0. Use `ruleset=empty` if you need counts that match your files exactly.

### `GET /repository/<name>/info`

Returns GraphDB's description of the repository, plus two extra fields:

- `triple_count`: a number, or `"Unknown"` if the size call fails;
- `named_graphs`: the list of named graph IRIs.

```bash
curl http://localhost:5050/repository/FILL/info
```

```json
{
  "repository": "FILL",
  "info": { "id": "FILL", "state": "RUNNING", "...": "…", "triple_count": 872, "named_graphs": [] },
  "status": "success"
}
```

Errors:

- `404` if the repository does not exist;
- `500` if GraphDB cannot be reached.

### `GET /repository/<name>/size`

Returns `{"repository": "FILL", "size": 872, "status": "success"}`.

The value comes from GraphDB's `/size` endpoint, which can lag a few seconds behind a write. For an exact count right after an upload, use `/query` with `SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }`.

### `DELETE /repository/<name>/clear`

Runs `DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }` against the repository. **Not reversible.** The repository itself is kept, only its data is removed.

```bash
curl -X DELETE http://localhost:5050/repository/FILL/clear
```

Returns `{"message": "Repository 'FILL' cleared successfully", "repository": "FILL", "status": "success"}`.

---

## Data

### `POST /upload`

Adds the triples of a JSON-LD file to a repository, in its default graph. Data already in the repository is kept.

If an ontology is loaded (see [`/ontology/load`](#post-ontologyload)), the file is also validated against it and the report is attached to the response. Validation is **informational only**: a non-conforming file is still uploaded.

| Field | Required | Notes |
|---|---|---|
| `file` | yes | JSON-LD (`.jsonld` / `.json`), UTF-8 |
| `repository` | yes in practice | Target repository ID (defaults to `second-graph`) |

```bash
curl -X POST http://localhost:5050/upload \
  -F repository=FILL \
  -F file=@../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld
```

```json
{
  "message": "File uploaded successfully",
  "repository": "FILL",
  "filename": "fill-merged-data.jsonld",
  "total_triples": "990",
  "status": "success",
  "validation": { "conforms": true, "violation_count": 0, "violations": [], "report_text": "…" }
}
```

- `total_triples` is a **string**. It is a live `COUNT(*)` over the whole repository after the upload, not the size of the file, so it includes earlier data and any triples the ruleset adds.
- `validation` takes one of three forms:
  - a [validation report](#validation-report);
  - `{"skipped": "No ontology loaded. …"}`;
  - `{"error": "Validation could not run: …"}`. The upload itself still succeeded in this case.

| Status | When |
|---|---|
| 200 | Uploaded (whatever the validation result) |
| 400 | `No file provided`, `No file selected`, wrong extension, or `Invalid JSON format` |
| 500 | GraphDB rejected the data, or the repository does not exist |

### `POST /query`

Runs a read-only SPARQL query. Send the query either as a file or as text.

| Field | Required | Notes |
|---|---|---|
| `file` | one of the two | `.sparql` / `.rq` file containing the query |
| `query` | one of the two | The query as text (ignored if `file` is present) |
| `repository` | yes in practice | Defaults to `second-graph` |
| `format` | no | `json` (default), `xml`, `csv`, `turtle`, `rdf` |

```bash
# from a file
curl -X POST http://localhost:5050/query -F repository=TELENOR -F file=@query_test/machine5-query.sparql

# inline
curl -X POST http://localhost:5050/query \
  --data-urlencode repository=FILL \
  --data-urlencode 'query=SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10'
```

`curl` refuses to mix `-F` and `--data-urlencode` in one call: use one style for every field. `-F 'query=…'` works too, but `curl` treats a value starting with `@` or `<` as a file to read.

With `format=json` the response wraps GraphDB's SPARQL JSON results:

```json
{
  "query": "SELECT ?s ?type WHERE { ?s a ?type } LIMIT 10",
  "repository": "FILL",
  "results": { "head": { "vars": ["s", "type"] }, "results": { "bindings": [ … ] } },
  "status": "success"
}
```

With any other `format`, the body is GraphDB's raw output with the matching `Content-Type`:

| `format` | `Content-Type` | Use for |
|---|---|---|
| `xml` | `application/sparql-results+xml` | SELECT / ASK |
| `csv` | `text/csv` | SELECT |
| `turtle` | `text/turtle` | CONSTRUCT / DESCRIBE |
| `rdf` | `application/rdf+xml` | CONSTRUCT / DESCRIBE |

`json`, `xml` and `csv` are SPARQL *result* formats. GraphDB does not produce them for CONSTRUCT / DESCRIBE, so use `turtle` or `rdf` for those queries. An unrecognised `format` value falls back to JSON results returned unwrapped.

Errors:

- `400`: no `file` and no `query`, or a wrong file extension;
- `500`: GraphDB rejected the query, or the repository does not exist.

### `POST /update`

Runs a SPARQL 1.1 Update (`INSERT DATA`, `DELETE DATA`, `DELETE … INSERT … WHERE`, …) against a repository. The fields are the same as for `/query`: `file` or `query`, plus `repository`. There is no `format`.

```bash
curl -X POST http://localhost:5050/update -F repository=TELENOR -F file=@query_test/query_delete.sparql
```

Returns `{"message": "Update operation completed successfully", "query": "…", "repository": "TELENOR", "status": "success"}`.

Errors:

- `400`: no query provided, or a wrong file extension;
- `500`: GraphDB rejected the update.

---

## Ontology & validation

The app holds **one** ontology at a time, made of a TBox and SHACL shapes. It is used by `/validate` and by every `/upload`.

- It is stored under `ontology_store/` on disk, so it survives app and container restarts.
- It is **not** written into GraphDB. If you want the ontology's axioms queryable inside a repository, upload the ontology files to that repository with `/upload` as well.

### `POST /ontology/load`

Loads the ontology, **replacing** whatever was loaded before. Calls do not accumulate.

All files are parsed first. If any one of them is not valid JSON-LD, nothing changes and the previous ontology stays loaded.

| Field | Repeatable | Notes |
|---|---|---|
| `ontology_files` | yes | TBox files: core ontology, modules, extensions (JSON-LD) |
| `shapes_files` | yes | SHACL shapes files (JSON-LD) |

At least one file is required in either field. Files are stored by **file name**, so names must be unique within each field: a second file with the same name overwrites the first.

Example with the full INTEND ontology (all three domains). Run it from `gui/inGraph/`:

```bash
O=../../INTEND-ontology/jsonld
args=()
for f in $O/ontology/intend.jsonld $O/ontology/modules/*.jsonld $O/ontology/external/*.jsonld $O/extensions/*.jsonld; do
  args+=(-F "ontology_files=@$f")
done
for f in $O/shapes/*.jsonld; do args+=(-F "shapes_files=@$f"); done
curl -X POST http://localhost:5050/ontology/load "${args[@]}"
```

```json
{
  "message": "Ontology loaded successfully (replaced any previously loaded ontology)",
  "ontology_files": ["intend-application.jsonld", "…"],
  "shapes_files": ["intend-shapes-application.jsonld", "…"],
  "ontology_triples": 863,
  "shapes_triples": 756,
  "status": "success"
}
```

| Status | When |
|---|---|
| 200 | Loaded |
| 400 | No files, a wrong extension, or a file that is not valid JSON-LD (nothing changed) |
| 500 | Writing to the store failed |

The FILL and Telenor shapes each check one fixed node: `FillContinuum` and `TelenorNordicContinuum`. If you load all three domains' shapes and then validate a single-domain KG, you will get a violation on the other domain's node, because it is not in your file. That violation says nothing about your data. To avoid it, load only the core shapes plus the shapes of the domain you are checking.

### `GET /ontology/status`

```json
{
  "loaded": true,
  "ontology_files": ["intend-application.jsonld", "…"],
  "shapes_files": ["intend-shapes-application.jsonld", "…"],
  "ontology_triples": 863,
  "shapes_triples": 756
}
```

Always `200`. `loaded` is `false` and the lists are empty when nothing is loaded.

### `DELETE /ontology`

Unloads the ontology. Afterwards:

- `/validate` answers `409`;
- `/upload` reports validation as `skipped`.

Returns `{"message": "Ontology cleared", "status": "success"}`.

### `POST /validate`

Validates a KG file against the loaded ontology **without** sending anything to GraphDB.

| Field | Required | Notes |
|---|---|---|
| `file` | yes | JSON-LD (`.jsonld` / `.json`) |

```bash
curl -X POST http://localhost:5050/validate \
  -F file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld
```

```json
{
  "filename": "telenor-network-data.jsonld",
  "kg_triples": 7711,
  "validation": { "conforms": true, "violation_count": 0, "violations": [], "report_text": "…" },
  "status": "success"
}
```

| Status | When |
|---|---|
| 200 | Validation ran (check `validation.conforms` for the result) |
| 400 | No file, a wrong extension, or the file is not valid JSON-LD |
| 409 | No ontology loaded: call `/ontology/load` first |
| 500 | The validator itself failed |

Only the file is validated, together with the loaded TBox. The rest of the repository's content is not taken into account. For FILL, validate [`fill-merged-data.jsonld`](../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld) (catalog + instances) rather than the two halves separately: the instance file refers to catalog entries it does not contain.

### Validation report

`/validate` and `/upload` return the same structure:

```json
{
  "conforms": false,
  "violation_count": 1,
  "violations": [
    {
      "focusNode": "https://w3id.org/intend/examples/fill-data#FillContinuum",
      "resultPath": null,
      "value": "https://w3id.org/intend/examples/fill-data#FillContinuum",
      "resultMessage": "Value does not conform to Shape intend:ResourcePoolAggregateShape. See details for more information.",
      "resultSeverity": "http://www.w3.org/ns/shacl#Violation",
      "sourceConstraintComponent": "http://www.w3.org/ns/shacl#NodeConstraintComponent",
      "sourceShape": "…",
      "details": ["The Resource-layer aggregate must consist of at least one BusinessResource (Figure 2: cardinality 1..*)."]
    }
  ],
  "report_text": "Validation Report\nConforms: False\n…"
}
```

| Field | Meaning |
|---|---|
| `conforms` | `true` if there are no violations of severity `sh:Violation` |
| `violation_count` | Number of top-level SHACL results (matches pyshacl's "Results (N)") |
| `violations[]` | One entry per top-level result. Any field can be `null` |
| `violations[].details` | Messages of the nested `sh:detail` results that explain *why* a qualified constraint failed |
| `report_text` | pyshacl's human-readable report, unchanged |

Validation runs without RDFS inference, so data must state its `rdf:type`s explicitly. A KG that does not use the ontology's classes at all, such as the pre-alignment files in `KG/`, gets *few* violations rather than many: most shapes simply find nothing to check.

---

## End-to-end example

Starting from an empty GraphDB, in `gui/inGraph/`:

```bash
API=http://localhost:5050
E=../../INTEND-ontology/jsonld/examples

curl $API/health

for r in FILL TELENOR GATE; do curl -X POST $API/repositories/create -F id=$r; done

# (optional) load the ontology first, so every upload returns a validation report
# … see POST /ontology/load above …

curl -X POST $API/upload -F repository=FILL    -F file=@$E/fill-merged-data.jsonld
curl -X POST $API/upload -F repository=TELENOR -F file=@$E/telenor-network-data.jsonld
curl -X POST $API/upload -F repository=GATE    -F file=@$E/gate-microservices-data.jsonld

curl -X POST $API/query -F repository=FILL \
  -F 'query=SELECT ?type (COUNT(?s) AS ?n) WHERE { ?s a ?type } GROUP BY ?type ORDER BY DESC(?n)'
```

## Python

```python
import requests

API = "http://localhost:5050"

# upload
with open("../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld", "rb") as f:
    r = requests.post(f"{API}/upload", data={"repository": "FILL"}, files={"file": f})
r.raise_for_status()
print(r.json()["total_triples"], r.json()["validation"])

# query
r = requests.post(f"{API}/query", data={
    "repository": "FILL",
    "query": "SELECT ?s WHERE { ?s a <https://w3id.org/intend/extensions/fill#Service> }",
})
for row in r.json()["results"]["results"]["bindings"]:
    print(row["s"]["value"])

# load an ontology: repeat the field name once per file
# (shortened here: pass the full file list shown in the POST /ontology/load example)
O = "../../INTEND-ontology/jsonld"
files = [
    ("ontology_files", open(f"{O}/ontology/intend.jsonld", "rb")),
    ("ontology_files", open(f"{O}/extensions/intend-fill-extension.jsonld", "rb")),
    ("shapes_files", open(f"{O}/shapes/intend-shapes-fill-extension.jsonld", "rb")),
]
print(requests.post(f"{API}/ontology/load", files=files).json())
```
