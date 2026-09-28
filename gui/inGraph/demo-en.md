# Demo: inGraph usage pipeline (web interface)

A guided walkthrough, meant to be followed step by step in front of an audience: starting
the stack, loading the ontology, validating, uploading a real Knowledge Graph, exploring
and querying from the web interface. Every command was actually run against GraphDB while
writing this guide — the numbers reported (triples, violations, result rows) are the ones
really observed, not estimates.

All terminal commands assume the shell is in `gui/inGraph/` (this folder). The paths to
the ontology (`../../INTEND-ontology/...`) assume `INTEND-ontology/` is a sibling folder
of `gui/`, i.e. `INTEND/INTEND-ontology/` while this app lives at `INTEND/gui/inGraph/`.

## Quick answer: ontology first, or KG first?

**Ontology first, then the KG.** `/upload` only attaches a SHACL report automatically if
an ontology is *already* loaded at the moment the file arrives — if you upload the KG
first, that upload won't have any validation attached (you'd have to call `/validate`
separately on the same file to get it). Loading the ontology first, instead, means a
single upload gives you **both the insert into GraphDB and the conformance verdict**,
which is also the most effective moment in a demo: one call, two results.

## Prerequisites

- Docker and Docker Compose working.
- This demo uses the example files already present in `INTEND-ontology/` (nothing extra
  to prepare).

## Step-by-step pipeline

### 1. Start the stack

```bash
docker compose up -d --build
```

Wait for both containers to come up (GraphDB takes roughly 30-60s to become "healthy").
Check:

```bash
curl http://localhost:5050/health
# {"status": "healthy", "graphdb": "connected"}
```

> Note on the port: 5050 on the host, not 5000 — on macOS, port 5000 is taken by default
> by the system AirPlay Receiver. Inside the container the app still listens on 5000.

**Say this:** "One single command starts both GraphDB and the web interface — no local
Python or GraphDB install needed."

### 2. Open the interface

Open **http://localhost:5050** in the browser. At this point you should see:

- **Repository Selection**: empty dropdown (no repository yet).
- **Ontology & Validation**: "No ontology loaded. Load one below to enable KG validation."
- SPARQL editor, graph panel and results table, all empty.

**Say this:** "We're starting from zero: no repository, no ontology loaded."

### 3. Create the target repository

Creating a repository doesn't have a form in the web interface yet — it's done from the
terminal (or with `createRepoScript.py`):

```bash
curl -X POST http://localhost:5050/repositories/create \
  -F "id=telenor" \
  -F "ruleset=rdfsplus-optimized"
```

`rdfsplus-optimized` is the default ruleset: it enables real RDFS reasoning on the
GraphDB side (useful later on if you also upload the ontology's own triples into the same
repository, not just into the validation store — see README.md, Architecture section).

**Say this:** "A GraphDB repository is like a standalone database — we need to create one
before we can upload anything into it."

### 4. Load the full ontology

**From the interface** (**Ontology & Validation** panel → **Load Ontology** card): select
all the ontology (TBox) files in the first field, all the SHACL shapes in the second,
then click **Load Ontology**.

**From the terminal**, the same result:

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

Expected response (really observed):

```json
{
  "message": "Ontology loaded successfully (replaced any previously loaded ontology)",
  "ontology_triples": 863,
  "shapes_triples": 756,
  "status": "success"
}
```

In the interface, the status line at the top of the **Ontology & Validation** panel
switches from "No ontology loaded" to something like *"Ontology loaded: 10 ontology
file(s), 8 shapes file(s) — 863 ontology triples, 756 shapes triples"*.

**Say this:** "We're loading the whole ontology — the five core modules plus all three
domain extensions (FILL, Telenor, GATE) — in one go. `/ontology/load` always
**replaces** the entire store, it never adds to it: it's meant as one deliberate action,
not an accumulation."

### 5. Dry-run validate the KG before uploading it

We'll use the Telenor data (Scandinavian edge network) as the example KG.

**From the interface**: **Validate & Upload a KG** card → select
`INTEND-ontology/jsonld/examples/telenor-network-data.jsonld` → **Validate**.

**From the terminal:**

```bash
curl -X POST http://localhost:5050/validate \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Observed result: **`conforms: false`, 1 violation**, on the node
`fill-data#FillContinuum` — nothing about Telenor itself.

**Say this (this is the teaching moment of the demo):** "This isn't a bug in the Telenor
data — we also loaded FILL's shapes, and one of them checks one specific node
(`data:FillContinuum`) regardless of whether the file we're validating defines it or not.
We're only validating Telenor, so that node simply isn't there: the violation flags an
absence, not a modeling error. We fix it in step 9 by scoping the loaded ontology down to
just the domain we actually care about."

### 6. Upload the KG into the repository

**From the interface**: in the same **Validate & Upload a KG** card used in step 5 —
select the same file (if it isn't already selected) and click **Upload to Repository**.
It goes into whichever repository is currently selected in **Repository Selection**
(step 3), so make sure `telenor` is picked there before clicking. The panel shows both
the upload confirmation (repository, total triples) and the same validation report just
seen in step 5 — it's the exact same call, no need to validate separately.

**From the terminal**, the same result:

```bash
curl -X POST http://localhost:5050/upload \
  -F "repository=telenor" \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Expected response (really observed):

```json
{
  "status": "success",
  "total_triples": "7829",
  "validation": {
    "conforms": false,
    "violation_count": 1
  }
}
```

**Say this:**
- "The uploaded file has 7711 triples, but the repository reports 7829 — the difference
  (118) is the RDF/RDFS/OWL axiomatic triples GraphDB pre-loads into every repository
  with the `rdfsplus-optimized` ruleset, before we've uploaded any data at all. It's not
  a counting error."
- "And most importantly: **the upload still succeeded**, despite the violation we just
  saw. Validation here is *soft*: it reports, it doesn't block. The idea is being able to
  see what's non-conformant in a real KG without being locked out of GraphDB — if you
  ever need a real gate (hard rejection of non-conformant data), the logic for it is
  already all in the backend, you just invert the order of the two operations (see
  README.md)."

### 7. Explore the repository from the interface

Back in the browser:

1. **Repository Selection** panel → **Refresh** → select `telenor` from the dropdown.
2. The line under the dropdown shows total triples and repository status.

### 8. Query with SPARQL and look at the graph

The interface draws edges in the graph **only when the query returns columns named
exactly `?subject ?predicate ?object`** (`convertResultsToGraph` in `static/js/app.js`
only recognizes that shape). With any other column names, the values still become
nodes, but with no edges between them, because the code has no way to know which value
is the subject and which is the predicate. It's worth showing both cases.

#### 8a. "Question-shaped" query (table — competency question)

In the **SPARQL editor**, replace the example query with a real competency question over
the data just uploaded — which edge clusters have the most compute capacity:

```sparql
PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?resource ?name ?gpuCount ?cpuCount WHERE {
    ?resource a telenor:EdgeCluster ;
              rdfs:label ?name ;
              telenor:gpuCount ?gpuCount ;
              telenor:cpuCount ?cpuCount .
}
ORDER BY DESC(?gpuCount) DESC(?cpuCount)
```

Click **Execute Query**. Observed result: **40 rows**, topped by clusters like
Copenhagen, Stockholm, Gothenburg, Malmö, Luleå (all with gpu:64, cpu:128) — including
accented names rendered correctly, direct proof that uploading the non-ASCII data worked
without corruption. Look at the **results table** below.

If you now switch to the **Graph Visualization** panel, you'll see **84 nodes and 0
edges** — not an error: that's 40 distinct values of `?resource` + 40 of `?name` + 2 of
`?gpuCount` (16, 64) + 2 of `?cpuCount` (32, 128) = 84 isolated nodes, one per distinct
value in each column, exactly for the reason explained above.

**Say this:** "This query answers a precise question and is perfect for the table — but
watch what happens in the graph: isolated nodes, zero edges. It's not broken, it's just
that `resource`/`name`/`gpuCount`/`cpuCount` aren't `subject`/`predicate`/`object`, so the
visualizer has no way to draw any relationship."

#### 8b. The same question, rewritten as triples (targeted graph)

The query from 8a **can be rewritten** in subject/predicate/object form while keeping the
exact same meaning ("the clusters with the most GPU/CPU") — the trick is that the ranking
(`ORDER BY` + `LIMIT`) has to happen inside a subquery, because the outer query can only
select `subject`/`predicate`/`object` and can no longer order by `?gpuCount`, which at
that point isn't a column anymore but one value among many in the `?object` column:

```sparql
PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?predicate ?object WHERE {
    {
        SELECT ?subject ?gpuCount ?cpuCount WHERE {
            ?subject a telenor:EdgeCluster ;
                     telenor:gpuCount ?gpuCount ;
                     telenor:cpuCount ?cpuCount .
        }
        ORDER BY DESC(?gpuCount) DESC(?cpuCount)
        LIMIT 10
    }
    ?subject ?predicate ?object .
    FILTER(?predicate IN (rdfs:label, telenor:gpuCount, telenor:cpuCount))
}
```

The inner subquery does exactly the work of 8a (filters the `EdgeCluster`s, orders them
by GPU/CPU descending, keeps only the top 10); the outer query takes those 10 subjects
and, for each, fetches only the three properties we care about (`rdfs:label`,
`gpuCount`, `cpuCount` — the `FILTER... IN (...)` avoids dragging in `location`,
`memoryTB`, etc. too, unlike the query in 8c below).

Observed result: **30 rows** (10 clusters × 3 properties), **22 distinct nodes, 30
edges**. All 10 top-ranked clusters share the same `gpuCount` value (64) and `cpuCount`
value (128), so the graph clearly shows a "star" structure: 10 cluster nodes (plus their
10 name nodes) converging on the same two shared nodes, "64" and "128".

**Say this:** "Same question as before, same answer — but now we're seeing it as a
graph: ten different clusters that all end up on the same '64 GPU' node and the same
'128 CPU' node. It's the exact same mechanism that produced isolated nodes in 8a, used on
purpose: here the subquery does the ranking, the outer query unpacks the result into
triples."

#### 8c. Generic triple query (graph with real edges, no filters)

If the goal instead is to explore everything known about a cluster, not just GPU/CPU, a
plain triple query without a `FILTER` is enough:

```sparql
PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>

SELECT ?subject ?predicate ?object WHERE {
    ?subject a telenor:EdgeCluster .
    ?subject ?predicate ?object .
}
LIMIT 100
```

Click **Execute Query**. Observed result: **100 rows** (the `LIMIT` cuts off partway
through the cluster list — each cluster alone has 15-19 properties, so 100 rows is
enough for only a few complete clusters), **99 distinct nodes, 100 edges** — a bigger,
denser graph than 8b, because here we're no longer filtering for one specific question.

With either triple-shaped query (8b or 8c), in the **Graph Visualization** panel:
- Try the layouts (Force / Circular / Hierarchical), zoom, drag the nodes around.
- Click **Fullscreen**, then click a node or edge to see the properties panel with the
  full triple.
- **Export CSV** to download the results (works with any query, including 8a).

**Say this:** "Same API, three ways of reading the same data: table for the details
(8a), a targeted graph for one precise question (8b), a generic exploratory graph (8c) —
the choice depends only on how the query is written."

### 9. (Bonus) From 1 violation to conformant: a scoped ontology

Reload the ontology, this time with **only** the core modules plus the Telenor extension
(no FILL, no GATE):

```bash
curl -X POST http://localhost:5050/ontology/load \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/intend.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-intent.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-user.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-resource.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-application.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/modules/intend-workflow.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/ontology/external/tio-reference.jsonld" \
  -F "ontology_files=@../../INTEND-ontology/jsonld/extensions/intend-telenor-extension.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-intent.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-user.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-resource.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-application.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-workflow.jsonld" \
  -F "shapes_files=@../../INTEND-ontology/jsonld/shapes/intend-shapes-telenor-extension.jsonld"
```

(`ontology_triples: 655`, `shapes_triples: 561`, observed — `/ontology/load`
**replaces** the previous store, so FILL/GATE's shapes are no longer in play.)

Re-validate the same file:

```bash
curl -X POST http://localhost:5050/validate \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Observed result: **`conforms: true`, 0 violations.**

**Say this:** "Same Telenor data as before, zero changes — only the ontology we compare
it against changed. The lesson: `sh:targetNode` checks one precise IRI regardless of
what we're validating, so it pays to load only the shapes for the domain(s) you're
actually checking together, or to validate a file that includes all of them."

### 10. From the terminal: the same query via curl, and clearing the ontology

To close out: the same queries from before can also be run without a browser, plus a
look at how to empty the ontology store (useful to start over, or before loading a
different one — although, as seen in step 9, `/ontology/load` always replaces the whole
store on every call anyway, so the explicit DELETE is only needed to get back to "no
ontology loaded", not to swap one for another).

**SPARQL query from the terminal**

> Be careful **not** to use `-F` for the `query` field with a multi-line query like this
> one: verified that with `-F` (multipart) curl does not reliably transmit a multi-line
> value — the request arrives at GraphDB malformed and fails with a 400.
> `--data-urlencode` works correctly with multi-line queries instead.

```bash
QUERY='PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?resource ?name ?gpuCount ?cpuCount WHERE {
    ?resource a telenor:EdgeCluster ;
              rdfs:label ?name ;
              telenor:gpuCount ?gpuCount ;
              telenor:cpuCount ?cpuCount .
}
ORDER BY DESC(?gpuCount) DESC(?cpuCount)'

curl -X POST http://localhost:5050/query \
  --data-urlencode "repository=telenor" \
  --data-urlencode "query=$QUERY" \
  --data-urlencode "format=json"
```

Expected response (really observed, truncated to the first result row — there are 40 in
total, same number as step 8a):

```json
{
  "query": "PREFIX telenor: ...",
  "repository": "telenor",
  "results": {
    "head": { "vars": ["resource", "name", "gpuCount", "cpuCount"] },
    "results": {
      "bindings": [
        {
          "resource": { "type": "uri", "value": "https://w3id.org/intend/examples/telenor-data#EC_1" },
          "name": { "type": "literal", "value": "Copenhagen Edge Cluster" },
          "gpuCount": { "type": "literal", "value": "64", "datatype": "http://www.w3.org/2001/XMLSchema#integer" },
          "cpuCount": { "type": "literal", "value": "128", "datatype": "http://www.w3.org/2001/XMLSchema#integer" }
        }
      ]
    }
  },
  "status": "success"
}
```

**Clearing the ontology**

Same thing the **Clear** button does in the **Ontology & Validation** panel in the
interface — from the terminal:

```bash
curl -X DELETE http://localhost:5050/ontology
```

Expected response (really observed):

```json
{
  "message": "Ontology cleared",
  "status": "success"
}
```

From this point on `GET /ontology/status` goes back to `"loaded": false`, and both the
**Ontology & Validation** panel in the interface and a call to `/validate` reflect it
right away: the **Validate** button goes back to disabled in the GUI, `/validate` from
the terminal would answer `409` again like in step 5 — exactly the starting state from
step 2.

**Say this:** "Everything we did from the browser has a command-line equivalent — handy
for automating the pipeline in a script, or in CI. And to close the loop: clearing the
ontology brings us right back to where we started."

## Command cheat sheet (in order)

```bash
# 1. Start
docker compose up -d --build

# 2. Check
curl http://localhost:5050/health

# 3. Repository
curl -X POST http://localhost:5050/repositories/create -F "id=telenor" -F "ruleset=rdfsplus-optimized"

# 4. Ontology (full)
curl -X POST http://localhost:5050/ontology/load -F "ontology_files=@..." -F "shapes_files=@..."

# 5. Dry-run validation
curl -X POST http://localhost:5050/validate -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"

# 6. Upload
curl -X POST http://localhost:5050/upload -F "repository=telenor" -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"

# 7-8. From here on: all in the browser, http://localhost:5050
#      (8a: "question-shaped" query -> table, 84 nodes/0 edges in the graph
#       8b: same question as triples -> targeted graph, 22 nodes/30 edges
#       8c: generic triple query     -> exploratory graph, 99 nodes/100 edges)

# 9. Bonus: reload the scoped ontology, repeat step 5

# 10. Same query from the terminal (careful: --data-urlencode, not -F, for a multi-line query)
QUERY='PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?resource ?name ?gpuCount ?cpuCount WHERE {
    ?resource a telenor:EdgeCluster ;
              rdfs:label ?name ;
              telenor:gpuCount ?gpuCount ;
              telenor:cpuCount ?cpuCount .
}
ORDER BY DESC(?gpuCount) DESC(?cpuCount)'
curl -X POST http://localhost:5050/query \
  --data-urlencode "repository=telenor" \
  --data-urlencode "query=$QUERY" \
  --data-urlencode "format=json"

# 10. Clear the ontology
curl -X DELETE http://localhost:5050/ontology
```

## Endpoints used in this demo

| Step | Endpoint | Where |
|---|---|---|
| 1-2 | `GET /health` | terminal |
| 3 | `POST /repositories/create` | terminal (no form in the GUI) |
| 4, 9 | `POST /ontology/load` | GUI (**Load Ontology**) or terminal |
| 5, 9 | `POST /validate` | GUI (**Validate a KG**) or terminal |
| 6 | `POST /upload` | GUI (**Upload to Repository** in the **Ontology & Validation** panel) or terminal |
| 7 | `GET /repositories`, `GET /repository/<name>/info` | GUI (**Repository Selection**) |
| 8, 10 | `POST /query` | GUI (SPARQL editor) or terminal |
| 10 | `DELETE /ontology` | GUI (**Clear** button in the **Ontology & Validation** panel) or terminal |

Full reference for every endpoint, including the ones not used in this demo
(`/ontology/status`, `DELETE /ontology`, `/update`, `/repository/<name>/clear`, ...): see
`README.md`.
