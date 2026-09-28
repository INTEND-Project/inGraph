# Demo: pipeline d'uso di inGraph (interfaccia grafica)

Percorso guidato, pensato per essere seguito passo-passo davanti a un pubblico: avvio
dello stack, caricamento dell'ontologia, validazione, upload di un Knowledge Graph reale,
esplorazione e query dall'interfaccia web. Ogni comando è stato eseguito realmente contro
GraphDB per scrivere questa guida — i numeri riportati (triple, violazioni, righe di
risultato) sono quelli osservati davvero, non stime.

Tutti i comandi da terminale assumono che la shell sia posizionata in `gui/inGraph/`
(questa cartella). I percorsi verso l'ontologia (`../../INTEND-ontology/...`) presumono
che `INTEND-ontology/` sia una cartella sorella di `gui/`, cioè `INTEND/INTEND-ontology/`
mentre questa app è in `INTEND/gui/inGraph/`.

## Risposta rapida: prima l'ontologia o prima il KG?

**Prima l'ontologia, poi il KG.** `/upload` allega automaticamente un report SHACL solo
se un'ontologia è *già* caricata nel momento in cui il file arriva — se carichi il KG
prima, quell'upload non avrà nessuna validazione allegata (dovresti richiamare `/validate`
a parte sullo stesso file per ottenerla). Caricando l'ontologia per prima, invece, un solo
upload ti restituisce **sia l'inserimento in GraphDB sia il verdetto di conformità**, che è
anche il momento più efficace di una demo: un'unica chiamata, due risultati.

## Prerequisiti

- Docker e Docker Compose funzionanti.
- Questa demo usa i file d'esempio già presenti in `INTEND-ontology/` (nessun file da
  preparare a parte).

## Pipeline passo-passo

### 1. Avvio dello stack

```bash
docker compose up -d --build
```

Aspetta che entrambi i container risultino attivi (GraphDB impiega circa 30-60s per
diventare "healthy"). Verifica:

```bash
curl http://localhost:5050/health
# {"status": "healthy", "graphdb": "connected"}
```

> Nota sulla porta: 5050 sull'host, non 5000 — su macOS la 5000 è occupata di default
> dall'AirPlay Receiver di sistema. Dentro al container l'app ascolta comunque sulla 5000.

**Da dire:** "Un solo comando fa partire sia GraphDB sia l'interfaccia web — nessuna
installazione locale di Python o di GraphDB."

### 2. Apri l'interfaccia

Apri **http://localhost:5050** nel browser. A questo punto dovresti vedere:

- **Repository Selection**: dropdown vuoto (nessun repository ancora).
- **Ontology & Validation**: "No ontology loaded. Load one below to enable KG validation."
- Editor SPARQL, pannello del grafo e tabella risultati, tutti vuoti.

**Da dire:** "Partiamo da zero: niente repository, nessuna ontologia caricata."

### 3. Crea il repository di destinazione

La creazione di un repository non ha ancora un form nell'interfaccia grafica — si fa da
terminale (o con `createRepoScript.py`):

```bash
curl -X POST http://localhost:5050/repositories/create \
  -F "id=telenor" \
  -F "ruleset=rdfsplus-optimized"
```

`rdfsplus-optimized` è il ruleset di default: abilita il reasoning RDFS reale lato
GraphDB (utile più avanti se si caricano anche le triple dell'ontologia nello stesso
repository, non solo nello store di validazione — vedi README.md, sezione Architecture).

**Da dire:** "Un repository GraphDB è come un database a sé — dobbiamo crearne uno prima
di poterci caricare qualcosa."

### 4. Carica l'ontologia completa

**Dall'interfaccia** (pannello **Ontology & Validation** → card **Load Ontology**):
seleziona tutti i file dell'ontologia (TBox) nel primo campo, tutte le shape SHACL nel
secondo, poi clicca **Load Ontology**.

**Da terminale**, lo stesso risultato:

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

Risposta attesa (osservata realmente):

```json
{
  "message": "Ontology loaded successfully (replaced any previously loaded ontology)",
  "ontology_triples": 863,
  "shapes_triples": 756,
  "status": "success"
}
```

Nell'interfaccia, la riga di stato in cima al pannello **Ontology & Validation** passa da
"No ontology loaded" a qualcosa come *"Ontology loaded: 10 ontology file(s), 8 shapes
file(s) — 863 ontology triples, 756 shapes triples"*.

**Da dire:** "Carichiamo l'intera ontologia — i cinque moduli core più tutte e tre le
estensioni di dominio (FILL, Telenor, GATE) — in un colpo solo. `/ontology/load`
**sostituisce** sempre tutto lo store, non lo somma: è un'azione deliberata, non un
accumulo."

### 5. Valida il KG a secco, prima di caricarlo

Usiamo i dati Telenor (rete edge in Scandinavia) come KG di esempio.

**Dall'interfaccia**: card **Validate a KG** → seleziona
`INTEND-ontology/jsonld/examples/telenor-network-data.jsonld` → **Validate**.

**Da terminale:**

```bash
curl -X POST http://localhost:5050/validate \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Risultato osservato: **`conforms: false`, 1 violazione**, sul nodo
`fill-data#FillContinuum`, non su nulla di Telenor.

**Da dire (questo è il momento didattico della demo):** "Non è un bug nei dati Telenor —
abbiamo caricato anche le shape di FILL, e una di quelle controlla un nodo specifico
(`data:FillContinuum`) indipendentemente dal fatto che il file che stiamo validando lo
definisca o meno. Stiamo validando solo Telenor, quindi quel nodo semplicemente non c'è:
la violazione segnala l'assenza, non un errore di modellazione. Lo risolviamo al passo
9 restringendo l'ontologia caricata al solo dominio che ci interessa."

### 6. Carica il KG nel repository

**Dall'interfaccia**: nella stessa card **Validate & Upload a KG** usata al passo 5 —
seleziona lo stesso file (se non è già selezionato) e clicca **Upload to Repository**.
Va nel repository che risulta selezionato in **Repository Selection** (passo 3), quindi
assicurati che `telenor` sia scelto lì prima di cliccare. Il pannello mostra sia la
conferma dell'upload (repository, triple totali) sia lo stesso report di validazione
appena visto al passo 5 — è la stessa identica chiamata, non serve rivalidare a parte.

**Da terminale**, lo stesso risultato:

```bash
curl -X POST http://localhost:5050/upload \
  -F "repository=telenor" \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Risposta attesa (osservata realmente):

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

**Da dire:**
- "Il file caricato ha 7711 triple, ma il repository ne segnala 7829 — la differenza
  (118) sono gli assiomi RDF/RDFS/OWL che GraphDB pre-carica in ogni repository con
  ruleset `rdfsplus-optimized`, ancora prima che carichiamo qualsiasi dato. Non è un
  errore di conteggio."
- "E soprattutto: **l'upload è andato a buon fine comunque**, nonostante la violazione
  vista al passo precedente. La validazione qui è *soft*: segnala, non blocca. L'idea è
  poter vedere cosa non è conforme in un KG reale senza restare bloccati fuori da
  GraphDB — se in futuro serve un vero cancello (rifiuto netto dei dati non conformi),
  la logica per farlo è già tutta nel backend, basta invertire l'ordine delle due
  operazioni (vedi README.md)."

### 7. Esplora il repository dall'interfaccia

Torna al browser:

1. Pannello **Repository Selection** → **Refresh** → seleziona `telenor` dal menu.
2. La riga sotto il menu mostra triple totali e stato del repository.

### 8. Interroga con SPARQL e guarda il grafo

L'interfaccia disegna archi nel grafo **solo quando la query restituisce colonne chiamate
esattamente `?subject ?predicate ?object`** (`convertResultsToGraph` in `static/js/app.js`
riconosce solo quello schema). Con nomi di colonna qualsiasi, i valori diventano comunque
nodi, ma senza nessun arco tra loro, perché il codice non ha modo di sapere quale valore è
il soggetto e quale il predicato. Vale la pena mostrare entrambi i casi.

#### 8a. Query "a domanda" (tabella — competency question)

Nell'**Editor SPARQL**, sostituisci la query di esempio con una vera competency question
sui dati appena caricati — quali cluster edge hanno più capacità di calcolo:

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

Clicca **Execute Query**. Risultato osservato: **40 righe**, in testa cluster come
Copenhagen, Stoccolma, Göteborg, Malmö, Luleå (tutti con gpu:64, cpu:128) — inclusi
correttamente i nomi con caratteri accentati, prova diretta che l'upload dei dati non
ASCII ha funzionato senza corruzione. Guarda la **tabella risultati** in basso.

Se ora passi al pannello **Graph Visualization**, vedrai **84 nodi e 0 archi** — non è un
errore: sono 40 valori distinti di `?resource` + 40 di `?name` + 2 di `?gpuCount` (16, 64)
+ 2 di `?cpuCount` (32, 128) = 84 nodi isolati, uno per ogni valore distinto in ogni
colonna, esattamente per il motivo spiegato sopra.

**Da dire:** "Questa query risponde a una domanda precisa ed è perfetta per la tabella —
ma guardate cosa succede nel grafo: nodi isolati, zero archi. Non è rotto, è solo che
`resource`/`name`/`gpuCount`/`cpuCount` non sono `subject`/`predicate`/`object`, quindi il
visualizzatore non sa disegnare nessuna relazione."

#### 8b. La stessa domanda, riscritta a triple (grafo mirato)

La query di 8a **si può riscrivere** in forma soggetto/predicato/oggetto, mantenendo lo
stesso identico significato ("i cluster con più GPU/CPU") — il trucco è che il ranking
(`ORDER BY` + `LIMIT`) deve avvenire in una subquery, perché la query esterna può
selezionare solo `subject`/`predicate`/`object` e non può più ordinare per `?gpuCount`,
che a quel punto non è più una colonna ma un valore fra tanti nella colonna `?object`:

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

La subquery interna fa esattamente il lavoro di 8a (filtra gli `EdgeCluster`, li ordina
per GPU/CPU decrescenti, tiene solo i primi 10); la query esterna riprende quei 10
soggetti e per ciascuno recupera solo le tre proprietà che ci interessano (`rdfs:label`,
`gpuCount`, `cpuCount` — il `FILTER... IN (...)` evita di trascinarsi dentro anche
`location`, `memoryTB`, ecc., a differenza della query di 8c qui sotto).

Risultato osservato: **30 righe** (10 cluster × 3 proprietà), **22 nodi distinti, 30
archi**. Tutti e 10 i cluster in cima alla classifica condividono lo stesso valore di
`gpuCount` (64) e `cpuCount` (128), quindi nel grafo si vede chiaramente una struttura "a
stella": 10 nodi-cluster (più i loro 10 nodi-nome) che convergono sugli stessi due nodi
condivisi "64" e "128".

**Da dire:** "Stessa domanda di prima, stessa risposta — ma ora la vediamo come grafo:
dieci cluster diversi che finiscono tutti sullo stesso nodo '64 GPU' e sullo stesso nodo
'128 CPU'. È lo stesso meccanismo che in 8a produceva nodi isolati, usato di proposito:
qui la subquery fa il ranking, la query esterna spacchetta il risultato in triple."

#### 8c. Query a triple generica (grafo con archi reali, senza filtri)

Se invece l'obiettivo è esplorare tutto quello che si sa su un cluster, non solo GPU/CPU,
basta una query a triple senza `FILTER`:

```sparql
PREFIX telenor: <https://w3id.org/intend/extensions/telenor#>

SELECT ?subject ?predicate ?object WHERE {
    ?subject a telenor:EdgeCluster .
    ?subject ?predicate ?object .
}
LIMIT 100
```

Clicca **Execute Query**. Risultato osservato: **100 righe** (il `LIMIT` taglia a metà
della lista cluster — ogni cluster ha da solo 15-19 proprietà, quindi 100 righe bastano
per pochi cluster completi), **99 nodi distinti, 100 archi** — un grafo più grande e più
denso di 8b, perché qui non stiamo più filtrando per una domanda specifica.

Con una qualsiasi delle query a triple (8b o 8c), nel pannello **Graph Visualization**:
- Prova i layout (Force / Circular / Hierarchical), lo zoom, il trascinamento dei nodi.
- Clicca **Fullscreen**, poi su un nodo o un arco per vedere il pannello delle proprietà
  con la tripla completa.
- **Export CSV** per scaricare i risultati (funziona con qualunque query, anche 8a).

**Da dire:** "Stessa API, tre modi di leggere gli stessi dati: tabella per i dettagli
(8a), grafo mirato su una domanda precisa (8b), grafo esplorativo generico (8c) — la
scelta dipende solo da come si scrive la query."

### 9. (Bonus) Da 1 violazione a conforme: ontologia mirata

Ricarica l'ontologia, questa volta **solo** con i moduli core più l'estensione Telenor
(niente FILL, niente GATE):

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

(`ontology_triples: 655`, `shapes_triples: 561`, osservato — `/ontology/load` **sostituisce**
lo store precedente, quindi le shape di FILL/GATE non sono più in gioco.)

Rivalida lo stesso file:

```bash
curl -X POST http://localhost:5050/validate \
  -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"
```

Risultato osservato: **`conforms: true`, 0 violazioni.**

**Da dire:** "Stessi dati Telenor di prima, zero modifiche — cambia solo l'ontologia con
cui li confrontiamo. La lezione: `sh:targetNode` controlla un IRI preciso a prescindere
da cosa stiamo validando, quindi conviene caricare solo le shape dei domini che si stanno
davvero verificando insieme, oppure validare un file che li include tutti."

### 10. Da terminale: la stessa query via curl, e pulizia dell'ontologia

Per chiudere: le stesse query di prima si possono lanciare anche senza browser, e uno
sguardo a come si svuota lo store dell'ontologia (utile per ripartire da zero, o prima di
caricarne una diversa — anche se, come visto al passo 9, `/ontology/load` sostituisce
comunque tutto lo store ad ogni chiamata, quindi la DELETE esplicita serve solo per
tornare allo stato "nessuna ontologia caricata", non per sostituirla con un'altra).

**Query SPARQL da terminale**

> Attenzione a **non** usare `-F` per il campo `query` con una query multi-riga come
> questa: verificato che con `-F` (multipart) curl non trasmette in modo affidabile un
> valore su più righe — la richiesta arriva a GraphDB malformata e fallisce con un 400.
> `--data-urlencode` invece funziona correttamente con query multi-riga.

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

Risposta attesa (osservata realmente, troncata alla prima riga di risultati — sono 40 in
tutto, stesso numero del passo 8a):

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

**Pulizia dell'ontologia**

Stessa cosa che fa il bottone **Clear** nel pannello **Ontology & Validation**
dell'interfaccia — da terminale:

```bash
curl -X DELETE http://localhost:5050/ontology
```

Risposta attesa (osservata realmente):

```json
{
  "message": "Ontology cleared",
  "status": "success"
}
```

Da qui in avanti `GET /ontology/status` torna a `"loaded": false`, e sia il pannello
**Ontology & Validation** nell'interfaccia sia una chiamata a `/validate` lo riflettono
subito: il bottone **Validate** torna disabilitato in GUI, `/validate` da terminale
risponderebbe di nuovo `409` come al passo 5 — esattamente lo stato di partenza del
passo 2.

**Da dire:** "Tutto quello che abbiamo fatto dal browser ha un equivalente da riga di
comando — utile per automatizzare la pipeline in uno script, o in CI. E per chiudere il
cerchio: cancellando l'ontologia torniamo esattamente al punto da cui siamo partiti."

## Cheat sheet dei comandi (in ordine)

```bash
# 1. Avvio
docker compose up -d --build

# 2. Verifica
curl http://localhost:5050/health

# 3. Repository
curl -X POST http://localhost:5050/repositories/create -F "id=telenor" -F "ruleset=rdfsplus-optimized"

# 4. Ontologia (completa)
curl -X POST http://localhost:5050/ontology/load -F "ontology_files=@..." -F "shapes_files=@..."

# 5. Validazione a secco
curl -X POST http://localhost:5050/validate -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"

# 6. Upload
curl -X POST http://localhost:5050/upload -F "repository=telenor" -F "file=@../../INTEND-ontology/jsonld/examples/telenor-network-data.jsonld"

# 7-8. Da qui in poi: tutto nel browser, http://localhost:5050
#      (8a: query "a domanda" -> tabella, 84 nodi/0 archi nel grafo
#       8b: stessa domanda a triple -> grafo mirato, 22 nodi/30 archi
#       8c: query a triple generica  -> grafo esplorativo, 99 nodi/100 archi)

# 9. Bonus: ricarica l'ontologia mirata, ripeti il passo 5

# 10. Stessa query da terminale (occhio: --data-urlencode, non -F, per una query multi-riga)
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

# 10. Pulizia dell'ontologia
curl -X DELETE http://localhost:5050/ontology
```

## Endpoint usati in questa demo

| Passo | Endpoint | Dove |
|---|---|---|
| 1-2 | `GET /health` | terminale |
| 3 | `POST /repositories/create` | terminale (nessun form nella GUI) |
| 4, 9 | `POST /ontology/load` | GUI (**Load Ontology**) o terminale |
| 5, 9 | `POST /validate` | GUI (**Validate a KG**) o terminale |
| 6 | `POST /upload` | GUI (**Upload to Repository** nel pannello **Ontology & Validation**) o terminale |
| 7 | `GET /repositories`, `GET /repository/<name>/info` | GUI (**Repository Selection**) |
| 8, 10 | `POST /query` | GUI (Editor SPARQL) o terminale |
| 10 | `DELETE /ontology` | GUI (bottone **Clear** nel pannello **Ontology & Validation**) o terminale |

Riferimento completo di tutti gli endpoint, inclusi quelli non usati in questa demo
(`/ontology/status`, `DELETE /ontology`, `/update`, `/repository/<name>/clear`, ...): vedi
`README.md`.
