# inGraph HTTP API reference

inGraph is a Flask service in front of a GraphDB triplestore. It exposes 20 HTTP endpoints for:

- managing GraphDB repositories;
- uploading JSON-LD knowledge graphs;
- running SPARQL queries and updates;
- validating KGs against the INTEND ontology with SHACL;
- sending a KG to inChat (Onlim knowledge graph).

The web interface at `/` is a client of this same API. Everything it does can also be done with `curl` or a script.

Source of truth: [`inGraphApp.py`](inGraphApp.py). If this file and the code disagree, the code wins. A machine-readable OpenAPI 3 (Swagger) version of this reference is in [`openapi.yaml`](openapi.yaml).

The status codes, response bodies and counts in this file were checked against a running instance (Docker dev stack, GraphDB 10.6.2) on 2026-11-27.

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
- **Responses are JSON.** There are two exceptions: `/query` with a non-JSON `format`, and the `405` page.
  - Success responses carry `"status": "success"`.
  - Errors are `{"error": "<message>"}` with a 4xx/5xx status code.
- **GraphDB errors come back as `500`.** The `error` message names the operation, the HTTP status GraphDB answered with, and the URL that was called (GraphDB's address inside Docker):

  ```json
  {"error": "Upload failed: 404 Client Error:  for url: http://graphdb:7200/repositories/FILLX/statements"}
  ```

  Read the GraphDB status like this:

  | GraphDB status in `error` | Usual cause |
  |---|---|
  | `404` | The repository does not exist |
  | `400` | GraphDB rejected the request: invalid JSON-LD, a SPARQL syntax error, or a repository ID that already exists |
  | `406` | GraphDB cannot produce the requested `format` for this kind of query (see `/query`) |
  | no status, `Max retries exceeded` / `Failed to resolve` | GraphDB is down or unreachable |

  GraphDB's own explanation is not passed through. To see it, run `docker compose logs graphdb`.
- **Accepted file extensions:** `.jsonld`, `.json`, `.sparql`, `.rq`.
  - The same list applies to every file field.
  - The content is then checked for what the endpoint expects (JSON / JSON-LD / SPARQL).
- **Maximum request size:** 16 MB. A larger request gets `413 {"error": "File too large"}`.
- **`repository` defaults to `second-graph`** on `/upload`, `/query` and `/update` when the field is omitted. Always pass it explicitly.
- **No authentication.** Any client that can reach the port can write to or clear any repository.
- **No CORS headers.** A web page served from another origin cannot call the API from the browser. Server-to-server calls and the built-in web interface are unaffected.
- **Unknown paths** return `404 {"error": "Endpoint not found"}`.
- **A wrong HTTP method** (e.g. `GET /upload`) returns `405` with Flask's HTML error page, not JSON.

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
| GET | [`/inchat/status`](#get-inchatstatus) | Is the inChat sync configured, recent sync jobs |
| POST | [`/inchat/sync`](#post-inchatsync) | Send a KG file to inChat (background job, or `dry_run` preview) |
| GET | [`/inchat/sync/<job_id>`](#get-inchatsyncjob_id) | Progress of a sync job |
| DELETE | [`/inchat/sync/<job_id>`](#delete-inchatsyncjob_id) | Stop a sync job |

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
| 503 | GraphDB unreachable (container stopped, wrong address): `{"status": "unhealthy", "error": "HTTPConnectionPool(host='graphdb', port=7200): Max retries exceeded …"}` |
| 503 | GraphDB reachable but answering with an error: `{"status": "unhealthy", "graphdb": "disconnected"}` |

`/ontology/*`, `/validate` and `/inchat/*` do not need GraphDB, so they keep working while it is down. The other endpoints answer `500`.

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
  "details": [
    {
      "id": "FILL",
      "title": "FILL",
      "state": "RUNNING",
      "type": "graphdb",
      "sesameType": "graphdb:SailRepository",
      "uri": "http://graphdb:7200/repositories/FILL",
      "externalUrl": "http://graphdb:7200/repositories/FILL",
      "location": "",
      "local": true,
      "readable": true,
      "writable": true,
      "unsupported": false
    }
  ]
}
```

`details` is GraphDB's own record of each repository, passed through unchanged. `state` is `RUNNING` once the repository has been used, and `INACTIVE` for a repository that was just created and not used yet.

Errors: `500` if GraphDB cannot be reached.

### `GET /repositories/active`

Same as above, filtered to repositories whose `state` is `RUNNING`. The keys are `active_repositories`, `count` and `details`.

A repository you have just created is `INACTIVE` until its first use, so it does **not** appear here yet. Any request to it (a query, an upload, `/size`) starts it. Use `GET /repositories` to see every repository.

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
| 500 | GraphDB refused. If the repository already exists you get `{"error": "Failed to create repository: 400 Client Error:  for url: http://graphdb:7200/rest/repositories"}` |

**Rulesets and triple counts.** With a reasoning ruleset, GraphDB adds triples of its own:

- a fresh `rdfsplus-optimized` repository already gives `COUNT(*)` = 70 (axiomatic triples), while `/size` says 0;
- after uploading the FILL file (872 triples), `COUNT(*)` gives 1044, because the ruleset also infers triples from your data.

Use `ruleset=empty` if you need counts that match your files exactly: the same file then gives exactly 872.

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
  "info": {
    "id": "FILL",
    "title": "FILL",
    "state": "RUNNING",
    "…": "the other GraphDB fields, as in GET /repositories",
    "triple_count": 872,
    "named_graphs": []
  },
  "status": "success"
}
```

`triple_count` is the same number as `/size`: explicit triples only.

Errors:

- `404` with `{"error": "Repository 'FILL' not found"}` if the repository does not exist;
- `500` if GraphDB cannot be reached.

### `GET /repository/<name>/size`

Returns `{"repository": "FILL", "size": 872, "status": "success"}`.

The value comes from GraphDB's `/size` endpoint, which counts **explicit** triples only: what was uploaded or inserted. Triples inferred by the ruleset are not counted. For the total including inferred triples, use `/query` with `SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }`.

For an unknown repository it answers `500` (GraphDB `404`), not `404`.

### `DELETE /repository/<name>/clear`

Runs `DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }` against the repository. **Not reversible.** The repository itself is kept, only its data is removed. This includes triples in named graphs.

```bash
curl -X DELETE http://localhost:5050/repository/FILL/clear
```

Returns `{"message": "Repository 'FILL' cleared successfully", "repository": "FILL", "status": "success"}`.

Errors: `500` if the repository does not exist (GraphDB `404`) or GraphDB cannot be reached.

To delete a repository itself, there is no inGraph endpoint: use GraphDB's REST API, `DELETE http://localhost:7200/rest/repositories/<name>`, or the GraphDB Workbench.

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

This response is for an empty repository created with `ruleset=empty`, and an ontology loaded with the core + FILL shapes:

```json
{
  "message": "File uploaded successfully",
  "repository": "FILL",
  "filename": "fill-merged-data.jsonld",
  "total_triples": "872",
  "status": "success",
  "validation": { "conforms": true, "violation_count": 0, "violations": [], "report_text": "Validation Report\nConforms: True\n…" }
}
```

- `total_triples` is a **string**. It is a live `COUNT(*)` over the whole repository after the upload, not the size of the file.
  - It includes data already in the repository: uploading the Telenor file (7711 triples) next gives `"8583"`.
  - It includes the triples the ruleset adds: the same FILL file in a fresh `rdfsplus-optimized` repository gives `"1044"`.
- Non-ASCII text (e.g. "Umeå", "Malmö" in the Telenor data) is stored and returned correctly.
- Both `{"@context", "@graph"}` documents and bare arrays of nodes are accepted.
- `validation` takes one of three forms:
  - a [validation report](#validation-report);
  - `{"skipped": "No ontology loaded. …"}`;
  - `{"error": "Validation could not run: …"}`. The upload itself still succeeded in this case.

| Status | When |
|---|---|
| 200 | Uploaded (whatever the validation result) |
| 400 | `No file provided`, `No file selected`, wrong extension, or `Invalid JSON format` (also for a `.rq`/`.sparql` file, which passes the extension check but is not JSON) |
| 413 | The file is larger than 16 MB |
| 500 | GraphDB rejected the data (valid JSON but invalid JSON-LD: GraphDB `400`), or the repository does not exist (GraphDB `404`). Omitting `repository` gives `404` on `second-graph` |

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

For an ASK query, `results` is `{"head": {}, "boolean": true}`.

With any other `format`, the body is GraphDB's raw output with the matching `Content-Type`:

| `format` | `Content-Type` | Use for |
|---|---|---|
| `xml` | `application/sparql-results+xml` | SELECT / ASK |
| `csv` | `text/csv` | SELECT |
| `turtle` | `text/turtle` | CONSTRUCT / DESCRIBE |
| `rdf` | `application/rdf+xml` | CONSTRUCT / DESCRIBE |

Formats and query types must match:

- `json`, `xml` and `csv` are SPARQL *result* formats, for SELECT / ASK. A CONSTRUCT / DESCRIBE with one of them (including the default `json`) fails with `500` and a GraphDB `406`:

  ```json
  {"error": "Query execution failed: 406 Client Error:  for url: http://graphdb:7200/repositories/FILL"}
  ```

- `turtle` and `rdf` are RDF formats, for CONSTRUCT / DESCRIBE. A SELECT with one of them fails the same way.
- An unrecognised `format` value returns the raw SPARQL JSON results, not wrapped in `{"query", "repository", "results", "status"}`, with `Content-Type: application/sparql-results+json`.

Errors:

- `400`: no `file` and no `query` (`{"error": "No query provided (file or query parameter)"}`), or a wrong file extension. A JSON request body also gives this `400`, because it is ignored;
- `500`: a SPARQL syntax error (GraphDB `400`), an unknown repository (GraphDB `404`), or a format that does not match the query type (GraphDB `406`).

### `POST /update`

Runs a SPARQL 1.1 Update (`INSERT DATA`, `DELETE DATA`, `DELETE … INSERT … WHERE`, …) against a repository. The fields are the same as for `/query`: `file` or `query`, plus `repository`. There is no `format`.

```bash
curl -X POST http://localhost:5050/update -F repository=TELENOR -F file=@query_test/query_delete.sparql
```

Returns `{"message": "Update operation completed successfully", "query": "…", "repository": "TELENOR", "status": "success"}`.

Errors:

- `400`: no query provided (`{"error": "No update query provided (file or query parameter)"}`), or a wrong file extension;
- `500`: GraphDB rejected the update, e.g. a syntax error (`"Update operation failed: 400 Client Error: …"`), or the repository does not exist.

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

At least one file is required in either field. Files are stored by **file name**, so names must be unique within each field: a second file with the same name overwrites the first, and only one name is listed. The file lists in the response are sorted by name.

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
| 400 | No files, a wrong extension, or a file that is not valid JSON-LD. Nothing changes. Example: `{"error": "One or more files are not valid JSON-LD, nothing was changed: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}` |
| 413 | The files together are larger than 16 MB |
| 500 | Writing to the store failed |

**Load only the shapes of the domain you check.** The FILL and Telenor shapes each check one fixed node: `FillContinuum` and `TelenorNordicContinuum`. With all three domains' shapes loaded, every single-domain KG gets a violation on the other domain's node, because that node is not in the file. That violation says nothing about your data. These are the results with the full ontology above:

| File validated | Triples | Result with all shapes | Violations on |
|---|---|---|---|
| `fill-merged-data.jsonld` | 872 | 1 violation | `TelenorNordicContinuum` |
| `telenor-network-data.jsonld` | 7711 | 1 violation | `FillContinuum` |
| `gate-microservices-data.jsonld` | 2089 | 2 violations | both nodes |

With only the core shapes plus `intend-shapes-telenor-extension.jsonld`, the Telenor file **conforms** (0 violations).

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

With the core + Telenor shapes loaded:

```json
{
  "filename": "telenor-network-data.jsonld",
  "kg_triples": 7711,
  "validation": { "conforms": true, "violation_count": 0, "violations": [], "report_text": "Validation Report\nConforms: True\n…" },
  "status": "success"
}
```

With the full ontology the same file gives the report shown under [Validation report](#validation-report).

| Status | When |
|---|---|
| 200 | Validation ran (check `validation.conforms` for the result) |
| 400 | No file, a wrong extension, or the file is not valid JSON-LD (`{"error": "Could not parse file as JSON-LD: …"}`) |
| 409 | No ontology loaded: `{"error": "No ontology loaded. POST to /ontology/load first."}` |
| 413 | The file is larger than 16 MB |
| 500 | The validator itself failed |

Validation is fast: about 0.2 s for the Telenor file (7711 triples) on a laptop.

Only the file is validated, together with the loaded TBox. The rest of the repository's content is not taken into account. For FILL, validate [`fill-merged-data.jsonld`](../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld) (catalog + instances) rather than the two halves separately: the instance file refers to catalog entries it does not contain.

### Validation report

`/validate` and `/upload` return the same structure. This is the real report for `telenor-network-data.jsonld` with the full ontology loaded:

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
      "sourceShape": "nde8f8f5f996343278730c4d88b401c88b7",
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
| `violations[]` | One entry per top-level result. Any field can be `null`. `sourceShape` is an internal blank-node ID (it changes from run to run) when the shape has no IRI |
| `violations[].details` | Messages of the nested `sh:detail` results that explain *why* a qualified constraint failed |
| `report_text` | pyshacl's human-readable report, unchanged |

Validation runs without RDFS inference, so data must state its `rdf:type`s explicitly. A KG that does not use the ontology's classes at all, such as the pre-alignment files in `KG/`, gets *few* violations rather than many: most shapes simply find nothing to check.

---

## inChat sync

Sends a KG file to inChat's knowledge graph on the Onlim platform (`https://proxy.onlim.com/api/ts/v1/kg/things`). This is the API version of the `InGraphInChatComunication.py` script, which now uses the same code ([`inchat_sync.py`](inchat_sync.py)).

For each top-level node of the file, in order:

1. `DELETE /kg/things/<local name>?ns=<namespace>&dryRun=false&force=true` removes the node's current version from inChat. A `404` here is normal: the node was not in inChat yet.
2. `POST /kg/things/imports` sends the node as a one-element JSON-LD array, with the file's `@context` attached.
3. The job **waits 10 seconds** before the next node. The pause is fixed on purpose.

How the file is turned into nodes:

- **Formats:** both `{"@context", "@graph"}` documents (all KGs in this repo) and bare arrays of nodes (the old `KG/*.jsonld` files) are accepted.
- **Namespace and local name** for the `DELETE` call come from each node's IRI, split at the last `#` or `/`.
  - `https://intendproject.eu/gate/28_station` gives `ns=https://intendproject.eu/gate/` and `28_station`. This is exactly what the original script did.
  - `…/telenor-data#EC_3` gives `ns=…/telenor-data#` and `EC_3`.
- **Blank nodes** are embedded into the node that references them. An example is the expectations and targets of the FILL intents, written `[ … ]` in Turtle. A blank node label only means something inside one document, so a reference to it would not survive a separate request. A blank node that no node references cannot be deleted before re-import, so it is skipped and listed in `skipped`.
- **Nothing is lost:** for every KG in this repo, the union of the payloads is the same RDF graph as the file.

**Credentials.** Nothing is sent unless all three of these are set:

| Environment variable | or in `config.py` |
|---|---|
| `INCHAT_API_KEY` | `API_KEY` |
| `INCHAT_PUBLISHER` | `PUBLISHER` |
| `INCHAT_DATASOURCE` | `DATASOURCE` |

- Environment variables win over `config.py`.
- With Docker, put the variables in a `.env` file next to `docker-compose.yml`. Without Docker, copy [`config.example.py`](config.example.py) to `config.py`.
- Both `.env` and `config.py` are gitignored and dockerignored.
- Settings are read on every request, so no restart is needed after adding them.
- `INCHAT_API_BASE_URL` overrides the Onlim URL, for a test server.

**Jobs.** A sync runs in a background thread of the app, one at a time.

| Nodes | Time at 10 s per node |
|---|---|
| 126 (FILL, merged file) | ~21 min |
| 254 (GATE) | ~42 min |
| 822 (TELENOR) | ~2 h 17 min |

- Jobs are kept in memory only. An app restart stops a running job and forgets all of them. This includes the automatic reload of the Docker dev stack when a `.py` file changes.
- If Onlim answers `401` or `403`, the job stops at once with state `failed`: the credentials or their permissions are wrong, and every further request would fail the same way.
- Any other per-node error is recorded in `errors` and the job goes on. As in the original script, the import is attempted even when the `DELETE` failed.

### `GET /inchat/status`

```bash
curl http://localhost:5050/inchat/status
```

```json
{
  "configured": false,
  "missing": ["INCHAT_API_KEY", "INCHAT_PUBLISHER", "INCHAT_DATASOURCE"],
  "sources": {},
  "api_base_url": "https://proxy.onlim.com/api/ts/v1/kg/things",
  "delay_seconds": 10,
  "active_job": null,
  "jobs": []
}
```

- `sources` says where each setting came from (`env` or `config.py`). The values themselves are never returned.
- `jobs` lists the most recent sync jobs, newest first, with the same fields as `GET /inchat/sync/<job_id>` minus the details.

### `POST /inchat/sync`

| Field | Required | Notes |
|---|---|---|
| `file` | yes | JSON-LD (`.jsonld` / `.json`) |
| `dry_run` | no | `true` = send nothing, just show what would be sent. Default `false` |

**Dry run.** It works without credentials and never contacts Onlim:

```bash
curl -X POST http://localhost:5050/inchat/sync -F dry_run=true \
  -F file=@../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld
```

```json
{
  "dry_run": true,
  "configured": false,
  "missing": ["INCHAT_API_KEY", "INCHAT_PUBLISHER", "INCHAT_DATASOURCE"],
  "filename": "fill-merged-data.jsonld",
  "total_elements": 126,
  "skipped": [],
  "delay_seconds": 10,
  "estimated_seconds": 1250,
  "import_url": "https://proxy.onlim.com/api/ts/v1/kg/things/imports",
  "elements": [
    {"id": "https://w3id.org/intend/examples/fill-data#MA03",
     "delete_url": "https://proxy.onlim.com/api/ts/v1/kg/things/MA03?ns=https%3A%2F%2Fw3id.org%2Fintend%2Fexamples%2Ffill-data%23&dryRun=false&force=true"},
    "… one entry per node …"
  ],
  "sample_payload": [{"@context": {"…": "…"}, "@id": "data:MA03", "…": "…"}],
  "status": "success"
}
```

**Real run** (without `dry_run`):

```bash
curl -X POST http://localhost:5050/inchat/sync \
  -F file=@../../INTEND-ontology/jsonld/examples/fill-merged-data.jsonld
```

Without credentials it answers `503`, and nothing is sent or started:

```json
{
  "error": "inChat sync is not configured, nothing was sent. Set INCHAT_API_KEY, INCHAT_PUBLISHER and INCHAT_DATASOURCE (environment or .env), or create config.py from config.example.py.",
  "missing": ["INCHAT_API_KEY", "INCHAT_PUBLISHER", "INCHAT_DATASOURCE"]
}
```

When configured, it starts the job and answers `202`, with a `Location: /inchat/sync/<job_id>` header. The body is the job (see below) plus `status_url` and `estimated_seconds`.

| Status | When |
|---|---|
| 200 | Dry run |
| 202 | Job started |
| 400 | No file, wrong extension, `Invalid JSON format`, `Expected a JSON-LD object or an array of nodes`, or `No node with an @id found in the file: nothing to send` (with the `skipped` list) |
| 409 | Another sync is running: `active_job` and `status_url` point at it |
| 413 | The file is larger than 16 MB |
| 503 | Not configured |

### `GET /inchat/sync/<job_id>`

```json
{
  "job_id": "e487360218a8",
  "state": "running",
  "filename": "fill-merged-data.jsonld",
  "total_elements": 126,
  "processed": 40,
  "succeeded": 39,
  "failed": 1,
  "skipped": [],
  "current_element": "https://w3id.org/intend/examples/fill-catalog#Container12",
  "delay_seconds": 10,
  "estimated_remaining_seconds": 850,
  "created_at": "2026-11-27T21:23:29+00:00",
  "started_at": "2026-11-27T21:23:29+00:00",
  "finished_at": null,
  "error": null,
  "errors": [
    {"id": "https://w3id.org/intend/examples/fill-catalog#Container7", "ok": false,
     "delete_status": 404, "import_status": 500, "import_error": "…"}
  ]
}
```

`state` takes one of these values:

| `state` | Meaning |
|---|---|
| `queued`, `running` | The job is working |
| `cancelling` | A stop was requested; the job stops after the node in progress |
| `completed` | Every node was processed. Check `failed` and `errors` for per-node problems |
| `cancelled` | Stopped by `DELETE /inchat/sync/<job_id>` |
| `failed` | Stopped by an error: `error` says why (e.g. Onlim answered 401/403) |

Each entry in `errors` carries:

- `delete_status` and `import_status`: the HTTP codes Onlim answered with;
- `delete_error` and `import_error`: the start of Onlim's answer, when there was one;
- `network_error`: when Onlim could not be reached.

Returns `404` for an unknown job ID, for example after a restart.

### `DELETE /inchat/sync/<job_id>`

Stops a running job after the node in progress. Nodes already sent stay in inChat.

```bash
curl -X DELETE http://localhost:5050/inchat/sync/e487360218a8
```

| Status | When |
|---|---|
| 202 | Stop requested: the body is the job, with state `cancelling` |
| 404 | Unknown job ID |
| 409 | The job is not running |

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
