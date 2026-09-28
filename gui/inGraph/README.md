# inGraph (Web Interface edition)

## Overview

inGraph is a REST API (Flask) in front of a [GraphDB](https://www.ontotext.com/products/graphdb/) triplestore, plus — in this fork — a browser-based **Knowledge Graph Visualizer** served at `/`. It builds and maintains the Knowledge Graphs (KGs) for the INTEND use cases (FILL, Telenor, GATE), lets other tools (e.g. inChat) read/write that data over HTTP, lets you explore a repository visually (SPARQL editor + D3.js graph view) without leaving the browser, and — since this update — can **load the INTEND ontology once and check every KG you upload against it**, returning a structured SHACL violations report without ever blocking the upload.

This fork tracks the same `inGraphApp.py` API as the non-GUI `inGraph` project (same GraphDB backend, same endpoints); the two diverge only in the web interface and the Docker packaging around it (multi-stage `Dockerfile`, a dedicated `docker-compose.prod.yml`).

## Features

- **Web interface**: browse repositories, write and run SPARQL queries with syntax highlighting, see the results as an interactive D3.js graph (force/circular/hierarchical layouts), inspect node/edge properties, export results to CSV.
- **Knowledge Graph Construction**: builds a structured KG per use case (FILL, Telenor, GATE).
- **REST API**: upload JSON-LD, run SPARQL queries/updates, manage GraphDB repositories, all over HTTP — the web interface is a client of this same API, so everything below also works from `curl`/scripts.
- **Ontology-conformance checking**: load the INTEND ontology (TBox + SHACL shapes) once, then every `/upload` (and any ad-hoc `/validate` call) is checked against it and returns a violations report — from the API directly, or from the **Ontology & Validation** panel in the web interface. See [Ontology conformance checking](#ontology-conformance-checking) below.
- **Docker-first**: `docker compose up` gets you GraphDB + the web app running with no local Python/pip install at all, in dev or production mode.

## Project structure

```
gui/inGraph/
├── inGraphApp.py                 Flask app — API + serves the web interface (see Endpoint reference below)
├── templates/index.html          web interface markup
├── static/css/style.css          web interface styling
├── static/js/app.js              web interface logic (repository browser, SPARQL editor, D3 graph, ontology panel)
├── InGraphInChatComunication.py  standalone script syncing individual KG elements to the
│                                 external Onlim/Semantify platform for inChat (unrelated
│                                 to inGraphApp.py / GraphDB — separate integration)
├── createRepoScript.py, createRepoAndUpload.py, uploadScript.py   example scripts using the API
├── test_api.py                   scripted smoke test against a running instance
├── KG/                           knowledge graphs built from the Telenor/FILL/GATE use cases
├── query_test/                   example SPARQL query/update files
├── requirements.txt
├── Dockerfile                    multi-stage: `development` and `production` targets
├── docker-compose.yml            dev stack (GraphDB + hot-reloading web app)
├── docker-compose.prod.yml       production stack (built `production` image, no bind mounts)
├── docker-dev.ps1                Windows PowerShell helper for the commands below
├── DOCKER_README.md, TUTORIAL.md more detail on Docker usage and on using the web interface (Italian)
└── ontology_store/               created at runtime by /ontology/load (gitignored, see below)
```

`ontology_store/` and `uploads/` are created automatically the first time you use the
API and are gitignored — they hold runtime state (whatever ontology you loaded, whatever
files you uploaded), not source.

## Quick start (Docker — recommended)

No local Python, pip, or GraphDB install needed. Everything runs in containers.

```bash
docker compose up
```

This starts two containers (see `docker-compose.yml`):
- **`graphdb`** — GraphDB 10.6.2, on `http://localhost:7200`
- **`kg-visualizer`** — this Flask app + web interface, with the whole project directory
  bind-mounted for hot reload (edit `inGraphApp.py`, the running server picks it up)

The web app listens on port 5000 *inside* the container, but the host-side mapping is
**5050**, not 5000: on macOS, port 5000 is taken by default by the system AirPlay Receiver
(ControlCenter), which makes "port 5000 already in use" the very first thing most Mac users
hit here. Override with `HOST_PORT=xxxx` in a `.env` file if 5050 is also taken for you.

Wait for both to report healthy, then either open **http://localhost:5050** in a browser,
or check from the command line:

```bash
curl http://localhost:5050/health
# {"status": "healthy", "graphdb": "connected"}
```

`ontology_store/` and `uploads/` live on your host filesystem (bind-mounted, not just
inside the container), so anything you load or upload survives `docker compose down` /
`docker compose up` again. Use `docker compose down -v` only if you also want to wipe
GraphDB's own data volumes.

For a production-like run (`docker-compose.prod.yml`: the Dockerfile's `production` target,
`FLASK_DEBUG=0`, a non-root container user, no source bind mount), see `DOCKER_README.md`;
that stack maps the web app to host port **80**, not 5050.

See `DOCKER_README.md` for more Docker-specific detail (Windows PowerShell helper script,
volume internals, troubleshooting container issues) and `TUTORIAL.md` for a walkthrough of
the web interface itself.

### Without Docker

```bash
pip install -r requirements.txt
# ... and have GraphDB running locally on http://localhost:7200
python inGraphApp.py
```

This runs Flask's own dev server directly on port 5000 (no Docker port remap involved) —
open `http://localhost:5000`.

## Web interface

Opening the app in a browser (`/`) gives you:

- **Repository Selection** — pick a GraphDB repository, see its triple count.
- **Ontology & Validation** — see whether an ontology is currently loaded (and its file/triple
  counts); load a new one by selecting ontology (TBox) and SHACL shapes JSON-LD files and
  clicking **Load Ontology** (this replaces any previously loaded ontology, same as the API);
  **Clear** the loaded ontology; **Validate** a KG file against it as a dry run; or
  **Upload to Repository** to send that same file to whichever repository is selected above
  in **Repository Selection** — either way the report (conforms/not, each violation's
  message/severity/focus node/path, and any nested `sh:detail` messages) renders directly
  under the panel, and a successful upload also shows the repository and its new triple
  count. This is a thin client over `/ontology/status`, `/ontology/load`, `DELETE /ontology`,
  `/validate` and `/upload` — see below.
- **SPARQL editor** — CodeMirror-based, with a one-click example query.
- **Graph visualization** — query results rendered as an interactive D3.js graph (drag nodes,
  zoom/pan, switch layouts, click a node/edge for its full properties in fullscreen mode).
- **Results table** — every binding as a row, with CSV export.

Creating a repository in the first place is still API/script-only in this fork
(`createRepoScript.py`, `createRepoAndUpload.py`, or `POST /repositories/create` directly) —
you need an existing repository selected in **Repository Selection** before **Upload to
Repository** has anywhere to send a file to.

## Endpoint reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Web interface |
| GET | `/health` | Check the service and GraphDB are up |
| GET | `/repositories` | List all GraphDB repositories |
| GET | `/repositories/active` | List only running repositories |
| POST | `/repositories/create` | Create a new repository |
| POST | `/upload` | Upload a JSON-LD/JSON file to a repository (+ SHACL report if an ontology is loaded) |
| POST | `/query` | Execute a SPARQL SELECT/ASK/CONSTRUCT/DESCRIBE query |
| POST | `/update` | Execute a SPARQL INSERT/DELETE/UPDATE |
| GET | `/repository/<name>/size` | Number of triples in a repository |
| GET | `/repository/<name>/info` | Repository details (size, named graphs) |
| DELETE | `/repository/<name>/clear` | Delete all triples in a repository |
| **POST** | **`/ontology/load`** | **Load the ontology TBox + SHACL shapes used for conformance checking** |
| **GET** | **`/ontology/status`** | **Check whether an ontology is currently loaded, and basic stats** |
| **DELETE** | **`/ontology`** | **Clear the loaded ontology** |
| **POST** | **`/validate`** | **Check a KG file against the loaded ontology without uploading it anywhere (dry run)** |
| GET | `/examples` | This same set of examples, as JSON |

### Upload a KG

```bash
curl -X POST http://localhost:5050/upload \
  -F "repository=telenor" \
  -F "file=@KG/telenorKG.jsonld"
```

### Run a SPARQL query

```bash
curl -X POST http://localhost:5050/query \
  -F "repository=telenor" \
  -F "file=@query_test/machine5-query.sparql" \
  -F "format=json"
```

### SPARQL update/delete

```bash
curl -X POST http://localhost:5050/update \
  -F "repository=telenor" \
  -F "file=@query_test/query_delete.sparql"
```

## Ontology conformance checking

### Why "soft" validation

A KG that fails validation is still uploaded. The check is informational — it attaches a
report, it never blocks. This was a deliberate choice (not the only reasonable one: the
alternative is a hard gate that refuses non-conformant data outright) — soft validation is
better suited to active development, where you want to *see* what is non-conformant in a
real KG without being blocked from getting it into GraphDB to look at. If you want hard
rejection later, the validation logic (`_run_shacl_validation` in `inGraphApp.py`) already
computes `conforms: true/false` before `/upload` writes anything — swap the order (validate
first, only call GraphDB if `conforms` is true) to make it a real gate.

### Loading the ontology

`/ontology/load` takes any number of JSON-LD files under two form fields:
`ontology_files` (the TBox: core ontology + whichever domain extensions you want) and
`shapes_files` (the matching SHACL shapes). **It replaces the whole store on every call** —
it is not additive across calls, "load the ontology" is meant as one deliberate action, not
an accumulation of fragments. All files are parsed and checked *before* anything is written
to disk, so one malformed file in a call cannot corrupt a previously good, working ontology
— the call either fully replaces the store or fails with nothing changed.

From the web interface, this is the **Load Ontology** card in the **Ontology & Validation**
panel — pick the files with the two file inputs and click the button.

From the command line, using the INTEND ontology project's own generated JSON-LD clone
(`INTEND-ontology/jsonld/`, a sibling of `gui/`, hence the `../../` below — see that
project's README for how it's generated from the canonical Turtle):

```bash
curl -X POST http://localhost:5050/ontology/load \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/intend.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-intent.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-user.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-resource.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-application.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-workflow.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/external/tio-reference.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/extensions/intend-fill-extension.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/extensions/intend-telenor-extension.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/extensions/intend-gate-extension.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-intent.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-user.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-resource.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-application.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-workflow.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-fill-extension.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-telenor-extension.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-gate-extension.jsonld"
```

```json
{
  "message": "Ontology loaded successfully (replaced any previously loaded ontology)",
  "ontology_files": ["intend-application.jsonld", "...", "tio-reference.jsonld"],
  "shapes_files": ["intend-shapes-application.jsonld", "...", "intend-shapes-workflow.jsonld"],
  "ontology_triples": 863,
  "shapes_triples": 756,
  "status": "success"
}
```

`GET /ontology/status` reports the same information at any later time, and survives an app
restart (the store is re-read from disk at startup) — this is what the panel's status line
polls. `DELETE /ontology` clears it.

### Checking a KG

Either as a dry run, with no GraphDB interaction at all (the **Validate a KG** card in the
web interface, or directly):

```bash
curl -X POST http://localhost:5050/validate -F "file=@KG/telenorKG.jsonld"
```

or as a side effect of a real upload — `/upload`'s response gains a `"validation"` key
whenever an ontology is loaded:

```bash
curl -X POST http://localhost:5050/upload \
  -F "repository=telenor" -F "file=@KG/telenorKG.jsonld"
```

Both return the same report shape:

```json
{
  "validation": {
    "conforms": false,
    "violation_count": 2,
    "violations": [
      {
        "focusNode": "https://w3id.org/intend/examples/fill-data#FillContinuum",
        "resultPath": null,
        "value": "https://w3id.org/intend/examples/fill-data#FillContinuum",
        "resultMessage": "Value does not conform to Shape intend:ResourcePoolAggregateShape. See details for more information.",
        "resultSeverity": "http://www.w3.org/ns/shacl#Violation",
        "sourceConstraintComponent": "http://www.w3.org/ns/shacl#NodeConstraintComponent",
        "sourceShape": "n...",
        "details": ["The Resource-layer aggregate must consist of at least one BusinessResource (Figure 2: cardinality 1..*)."]
      }
    ],
    "report_text": "Validation Report\nConforms: False\n..."
  }
}
```

`violations` is `results_graph` parsed into plain JSON — only the SHACL report's top-level
results (matching pyshacl's own "Results (N)" count); each result's nested `sh:detail`
messages (used by qualified-cardinality constraints to explain *what* failed) are folded
into that result's own `"details"` list rather than counted as separate violations.
`report_text` is pyshacl's raw human-readable report, kept alongside for convenience. The
web interface panel renders `conforms`/`violation_count` as a badge and each violation as a
card with its message, severity, focus node, path and any details.

If no ontology is loaded: `/validate` returns `409` (the **Validate** button in the web
interface is disabled until `/ontology/status` reports `loaded: true`), `/upload` still
succeeds and its `"validation"` is `{"skipped": "No ontology loaded. ..."}`.

### Three things worth knowing before you read a report

These are not bugs — they are how SHACL target selection actually works — but they can be
surprising the first time you see them, so both were deliberately reproduced and confirmed
while building this feature, not just guessed at:

1. **The FILL and Telenor shapes each include one `sh:targetNode`-bound aggregate shape**
   (`intend-shapes-fill-extension.jsonld` targets `data:FillContinuum`,
   `intend-shapes-telenor-extension.jsonld` targets `data:TelenorNordicContinuum`). A
   `sh:targetNode` shape checks that *exact* IRI regardless of whether your uploaded KG
   file actually defines it. If you load the **full** ontology (all three extensions'
   shapes) but only validate/upload the Telenor KG on its own, you will see one violation
   on `data:FillContinuum` for having zero `intend:consistsIn` — not because your Telenor
   data is wrong, but because `data:FillContinuum` simply is not present in that graph at
   all. Two ways to avoid it: load only the shapes for the domain(s) you're actually
   checking (e.g. core + `intend-shapes-telenor-extension.jsonld` only), or validate a
   combined file that includes all the domains' instance data together.
2. **`total_triples` in `/upload`'s response can be higher than the file you just
   uploaded, even into an empty repository — and that's correct, not a bug.**
   Repositories created with a reasoning ruleset (the default here is
   `rdfsplus-optimized`, both in `createRepoScript.py` and `/repositories/create`'s
   own default config) come pre-seeded by GraphDB with a small, fixed set of
   RDF/RDFS/OWL axiomatic triples (e.g. "rdf:type is an rdf:Property") *before you
   upload anything* — confirmed during development: the exact same file that lands
   at 7711 triples in a `ruleset=empty` repository lands at 7829 in a fresh
   `rdfsplus-optimized` one, a constant +118 contributed by the ruleset itself, not
   by your data. `total_triples` (a live `COUNT(*)` SPARQL query, run fresh on every
   `/upload`) is accurate for whatever ruleset the target repository actually has —
   just don't expect it to equal your source file's own triple count unless the
   repository was created with `ruleset=empty`. Also worth knowing: GraphDB's own
   `/repositories/<name>/size` REST endpoint (used by this API's
   `/repository/<name>/size`) can lag behind a live count for a few seconds after a
   write — prefer a live `COUNT(*)` via `/query` if you need the number immediately
   after an upload.
3. **A KG that uses none of the ontology's classes will show *few* violations, not many.**
   SHACL's `sh:targetClass` only checks individuals actually asserted with that class (or a
   subclass of it) in the data — if a KG uses a completely different vocabulary (e.g. the
   raw, pre-alignment files in `KG/`, which still use the flat `intendproject.eu/schema/*`
   predicates rather than the INTEND ontology's classes), almost none of the shapes have
   anything to check, so most of them simply produce zero results. `conforms: false` with a
   low violation count on unfamiliar data usually means "barely anything here matched my
   shapes' target classes" — not "I checked thoroughly and found only two problems."

## A pre-existing bug found and fixed while porting this update

This fork's `/query` already had its own, independent fix for the GraphDB content-type
detection issue that the non-GUI `inGraph` project also hit (it parses the response as JSON
inside a `try`/`except` instead of checking the `Content-Type` header, which sidesteps the
problem a different way) — nothing to change there.

It did **not** yet have the fix for the other one: **non-ASCII characters (an em-dash in an
`rdfs:comment`, an accented Nordic city name like "Umeå"/"Malmö" in the Telenor data, ...)
silently corrupted the request body sent to GraphDB**, which then rejected it outright
("Could not parse JSONLD" for `/upload`, an equivalent SPARQL parse failure for
`/query`/`/update`). Root cause, confirmed by minimal reproduction: `requests==2.31.0`
(pinned in `requirements.txt`) does not reliably UTF-8-encode a plain Python `str` request
body — the fix (in `make_graphdb_request`, the single function all endpoints funnel
through) explicitly encodes any `str` body to UTF-8 bytes before handing it to `requests`.
This is now ported here too. Neither bug is new code from this update — both were latent
since before it, and only surfaced once real testing (in Docker, against real GraphDB, with
data containing non-ASCII characters) actually exercised those endpoints rather than just
inspecting the code.

## Architecture

- **GraphDB repositories are created with the `rdfsplus-optimized` ruleset by default**
  (`createRepoScript.py`, and `/repositories/create`'s default config) — this means GraphDB
  performs real RDFS reasoning at query time once the ontology's own triples are also
  uploaded into a repository (via the normal `/upload` endpoint, same as any other file).
  `rdfs:subClassOf`/`rdfs:subPropertyOf` entailment then applies automatically, unlike the
  local `pyshacl`-based validation here (and the INTEND-ontology project's own
  `scripts/validate.py`), which both run with `inference="none"` and rely on explicit
  typing instead.
- **The ontology store used for `/upload` and `/validate` validation is separate from
  what's actually inside any given GraphDB repository.** Loading the ontology via
  `/ontology/load` does not by itself push anything into GraphDB — if you also want the
  ontology's own axioms queryable/reasoned-over inside a specific repository, upload the
  same ontology files to that repository through the normal `/upload` endpoint.
- **Validation always combines the *uploaded file's own content* with the loaded ontology
  TBox** — not the target repository's full existing contents. "Is this KG conformant" is
  answered per-file, not "is the whole repository conformant right now."
- **Two Docker targets, one Dockerfile.** `development` (the default, used by
  `docker-compose.yml`) bind-mounts the source for hot reload and keeps `FLASK_DEBUG=1`.
  `production` (used by `docker-compose.prod.yml`, built with `target: production`) copies
  only the files it needs, sets `FLASK_DEBUG=0`, and drops to a non-root `app` user — a
  meaningfully better starting point for anything beyond local development, though see
  Deployment below for what's still missing even there.

## Requirements

- Docker + Docker Compose (recommended), **or** Python 3.9+ and a local GraphDB instance
  (see `requirements.txt`: `flask`, `requests`, `werkzeug`, `rdflib`, `pyshacl`).

## Deployment

The infrastructure is currently deployed in test mode at
[http://notae-system.diag.uniroma1.it:5000/](http://notae-system.diag.uniroma1.it:5000/).

**Before exposing this beyond local/test use**, be aware `docker-compose.yml` (the
*development* stack) sets `FLASK_DEBUG=1` (Werkzeug's interactive debugger, which allows
arbitrary code execution if reached on an unhandled error — fine for local development, a
real risk on anything internet-reachable) and none of `/update`, `/repositories/create`,
`/repository/<name>/clear`, or `/ontology/load`+`/ontology` (DELETE) require
authentication. `docker-compose.prod.yml` already fixes the debug-mode part
(`FLASK_DEBUG=0`, non-root user) but not the missing authentication — that part is
pre-existing and worth addressing before treating any public deployment, test or
otherwise, as anything but disposable.

## License

MIT.
