# inGraph

inGraph builds and maintains the Knowledge Graphs (KGs) of the INTEND use cases.

- It stores the KGs in a [GraphDB](https://www.ontotext.com/products/graphdb/) triplestore.
- Other tools, read and update them through a REST API.
- A web interface lets you explore them with SPARQL.
- The KGs follow the **INTEND ontology**, which is defined in this repository. inGraph can check every KG you upload against it with SHACL.

## What's in this repository

| Folder | What it is | Docs |
|---|---|---|
| [`INTEND-ontology/`](INTEND-ontology/) | The INTEND ontology:<br>• modular OWL in Turtle, with FILL / Telenor / GATE extensions<br>• SHACL shapes<br>• example KGs aligned to the ontology<br>• SPARQL competency queries<br>• a JSON-LD copy | [README](INTEND-ontology/README.md) (Italian) |
| [`gui/inGraph/`](gui/inGraph/) | The inGraph application: Flask REST API + web interface + Docker setup | [README](gui/inGraph/README.md), [API reference](gui/inGraph/API.md), [OpenAPI / Swagger](gui/inGraph/openapi.yaml) |

## Features

- **Knowledge Graph construction**: one KG per use case, aligned to the INTEND ontology.
- **Web interface**:
  - repository browser;
  - SPARQL editor with an interactive graph view and CSV export;
  - an ontology & validation panel where files and folders can be dragged and dropped.
- **REST API** with 20 endpoints. It covers:
  - repositories;
  - JSON-LD upload;
  - SPARQL query and update;
  - ontology loading;
  - SHACL validation;
  - sync to inChat.

  Documented in [API.md](gui/inGraph/API.md) and as an [OpenAPI 3 file](gui/inGraph/openapi.yaml).
- **Ontology conformance checking**: load the ontology once, then every upload comes back with a SHACL report. The check is informational: a non-conforming KG is still uploaded.
- **inChat integration**: sends a KG to inChat's knowledge graph on the Onlim platform. It stays off until credentials are configured ([details](gui/inGraph/API.md#inchat-sync)).
- **Docker-first**: `docker compose up` starts GraphDB and the app. No local Python or GraphDB install is needed.

## Quick start

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/), with about 4 GB of RAM available for GraphDB.

```bash
cd gui/inGraph
docker compose up -d --build
```

| Service | URL |
|---|---|
| inGraph web interface and API | http://localhost:5050 |
| GraphDB Workbench | http://localhost:7200 |

The app listens on port 5000 inside the container, but on the host it is mapped to **5050**: on macOS, port 5000 is taken by AirPlay. To change it, set `HOST_PORT` in a `.env` file next to `docker-compose.yml`.

Check that everything is up:

```bash
curl http://localhost:5050/health
# {"graphdb": "connected", "status": "healthy"}
```

### First run: create the repositories and load the KGs

GraphDB starts empty. From `gui/inGraph/`:

```bash
API=http://localhost:5050
E=../../INTEND-ontology/jsonld/examples

for r in FILL TELENOR GATE; do curl -X POST $API/repositories/create -F id=$r; done

curl -X POST $API/upload -F repository=FILL    -F file=@$E/fill-merged-data.jsonld
curl -X POST $API/upload -F repository=TELENOR -F file=@$E/telenor-network-data.jsonld
curl -X POST $API/upload -F repository=GATE    -F file=@$E/gate-microservices-data.jsonld
```

Then open http://localhost:5050, pick a repository and run a query. GraphDB data is kept in Docker volumes, so you only do this once.

- To stop: `docker compose down`.
- To stop **and delete** the GraphDB data: `docker compose down -v`.

To also get a SHACL report on every upload, load the ontology first. Use the *Ontology & Validation* panel of the web interface, or the `curl` example in [API.md](gui/inGraph/API.md#post-ontologyload).

### Without Docker

You need Python 3.9+ and GraphDB running on `http://localhost:7200`:

```bash
cd gui/inGraph
pip install -r requirements.txt
python inGraphApp.py      # http://localhost:5000
```

### Validating the ontology itself

```bash
cd INTEND-ontology
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/validate.py              # parse every .ttl file + SHACL validation
python scripts/validate.py --queries    # same, plus the 14 competency queries
```

## Knowledge graphs

The KGs aligned to the INTEND ontology are in `INTEND-ontology/`:

- Turtle, the source files, in [`examples/`](INTEND-ontology/examples/);
- JSON-LD, the files to upload to inGraph, in [`jsonld/examples/`](INTEND-ontology/jsonld/examples/).

| Use case | JSON-LD file | Triples |
|---|---|---|
| FILL | `fill-merged-data.jsonld`: catalog + instances in one file. They also exist separately, as `fill-catalog-data` and `fill-instance-data` | 872 |
| Telenor | `telenor-network-data.jsonld`: 40 edge clusters, 780 network links | 7711 |
| GATE | `gate-microservices-data.jsonld`: 16 microservices, 18 Kafka topics, 219 parameters | 2089 |

[`gui/inGraph/KG/`](gui/inGraph/KG/) still holds the original KGs, built from the raw data before the ontology existed. They use the older `intendproject.eu/schema/` vocabulary.

## Repository layout

```
INTEND-ontology/
├── ontology/            core ontology (intend.ttl) and its modules
├── extensions/          FILL, Telenor and GATE extensions
├── shapes/              SHACL shapes, one file per module / extension
├── examples/            KGs aligned to the ontology (Turtle)
├── queries/             SPARQL competency queries
├── scripts/             validate.py, generate_jsonld.py
└── jsonld/              JSON-LD copy of all of the above (generated)

gui/inGraph/
├── inGraphApp.py        Flask app: REST API + web interface
├── inchat_sync.py       sync of a KG to inChat (used by /inchat/* and by InGraphInChatComunication.py)
├── templates/, static/  web interface
├── KG/                  original (pre-ontology) KGs
├── query_test/          example SPARQL queries and updates
├── API.md, openapi.yaml API reference (Markdown and OpenAPI 3)
├── Dockerfile, docker-compose.yml, docker-compose.prod.yml
└── config.example.py    template for the inChat credentials (config.py is gitignored)
```

## Deployment

The infrastructure is deployed in test mode at [http://notae-system.diag.uniroma1.it:5000/](http://notae-system.diag.uniroma1.it:5000/).

The API has no authentication. Read the *Deployment* section of the [app README](gui/inGraph/README.md#deployment) before exposing it beyond local or test use. For production, use `docker-compose.prod.yml`: it turns debug mode off and runs the app as a non-root user.

## License

MIT.
