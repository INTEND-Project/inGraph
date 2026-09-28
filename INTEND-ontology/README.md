# INTEND Ontology


## Struttura del progetto

```
ontology/
  intend.ttl                       entry point: importa tutti i moduli
  modules/
    intend-intent.ttl              Intent, IntentManager, IntentReport, Capability
    intend-user.ttl                User, Person, Organization, Role, Permission
    intend-resource.ttl            Resource, BusinessResource/CustomerResource, ...
    intend-application.ttl         Application, Latency/Bandwidth/PacketLossRate
    intend-workflow.ttl            Workflow, Chatbot, Adapter, Explainer, BusinessKnowledge
  external/
    tio-reference.ttl              stub locale dei termini TM Forum TIO citati (leggi la nota nel file)
extensions/
  intend-fill-extension.ttl        Machine, MachineType, Service, ProductComponent, Container (Fig. 5 del paper + KG reale)
  intend-telenor-extension.ttl     EdgeCluster, NetworkLink (rete edge Telenor Nordic, da KG reale)
  intend-gate-extension.ttl        Microservice, KafkaTopic, Parameter (pipeline LiDAR/traffico GATE Institute, da KG reale)
shapes/                            vincoli SHACL, un file per modulo (stesso partizionamento sopra)
examples/
  fill-catalog-data.ttl            catalogo FILL reale (5 MachineType, 12 Service, 13 Component, 42 Container) — migrato da un KG JSON-LD fornito dall'utente
  fill-instance-data.ttl           utenti, macchine possedute, workflow, 10 intent d'esempio (container attesi ricalcolati sul catalogo reale)
  telenor-network-data.ttl         40 edge cluster (Danimarca/Finlandia/Svezia/Norvegia) + 780 collegamenti di rete misurati — da KG JSON-LD reale, non collegato a FILL
  gate-microservices-data.ttl      16 microservizi Kubernetes/Helm, 18 topic Kafka, 219 parametri di configurazione — pipeline LiDAR/traffico reale (Sofia), non collegata a FILL/Telenor
queries/
  NN-*.rq                          14 competency question eseguibili (11 dalla Sez. 3 del paper + 3 specifiche di dominio per verificare le anomalie dei KG reali), una per file
scripts/
  validate.py                      validazione automatica (parsing + SHACL + query)
  generate_jsonld.py               rigenera jsonld/ da tutti i file .ttl del progetto
  requirements.txt
catalog-v001.xml                   catalogo Protégé per risoluzione offline degli import
everything.ttl                     bundle di comodo per Protégé: importa ontologia + tutte e tre le estensioni + tutti e tre i dataset d'esempio in un colpo solo
jsonld/                            clone JSON-LD generato (stessa struttura di ontology/, extensions/, shapes/, examples/, con estensione .jsonld) — vedi sotto
```

Namespace dell'ontologia: `https://w3id.org/intend/ontology#` (prefisso `intend:`) — è un
placeholder in stile w3id, facilmente sostituibile con un dominio reale (basta un
find&replace su tutti i file `.ttl`) quando/se il progetto verrà pubblicato.

## Come aprire il progetto (Protégé)

1. Installa [Protégé](https://protege.stanford.edu/) (desktop).
2. `File > Open...` → seleziona `ontology/intend.ttl`. Protégé trova automaticamente
   `catalog-v001.xml` nella cartella del progetto e risolve offline tutti gli
   `owl:imports` verso i moduli `intend:` e verso `tio-reference.ttl`. FOAF, PROV-O,
   ORG e SOSA vengono invece scaricati dai loro namespace ufficiali (serve
   connessione a Internet la prima volta; sono cache-abili in Protégé).
3. Per esplorare in un colpo solo ontologia + tutte e tre le estensioni (FILL,
   Telenor, GATE) + tutti e tre i dataset d'esempio, apri invece `everything.ttl`
   (bundle di comodo, non fa parte dell'ontologia modulare — vedi il commento in
   testa al file). I tre domini sono indipendenti e non condividono individui.

## Come validare (SHACL + parsing)

```bash
cd INTEND-ontology
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r scripts/requirements.txt

python scripts/validate.py           # parsing di tutti i .ttl + validazione SHACL
python scripts/validate.py --queries # come sopra, più l'esecuzione delle 14 competency question
```

Lo script (`scripts/validate.py`) fa tre cose, in ordine:
1. Parsa **ogni** file `.ttl` singolarmente (così un errore di sintassi indica
   subito il file responsabile, invece di un errore generico sul grafo unito).
2. Carica ontologia + tutte e tre le estensioni + tutti e tre i dataset d'esempio
   in un unico grafo (~11.500 triple) e lo valida con `pyshacl` contro tutte le
   shape in `shapes/`.
3. Con `--queries`, esegue ognuna delle query in `queries/` e stampa i risultati.

## Clone JSON-LD

```bash
python scripts/generate_jsonld.py    # rigenera jsonld/ da zero a partire dai .ttl
```

`jsonld/` è un clone completo del progetto (ontologia, le tre estensioni, tutte
le shape SHACL, tutti e quattro i dataset d'esempio, `everything.ttl`) nella
stessa sintassi JSON-LD in cui sono arrivati i tre KG originali — stessa
struttura di cartelle di `ontology/`/`extensions/`/`shapes/`/`examples/`, un
`.jsonld` per ogni `.ttl`. Il Turtle resta la fonte canonica: `jsonld/` è
generato, non va editato a mano, e va rigenerato con lo script sopra ogni
volta che cambi un file `.ttl`.

Ogni `.jsonld` usa come `@context` esattamente gli stessi prefissi dichiarati
nel file `.ttl` sorgente (estratti automaticamente), non l'elenco di default
di rdflib — l'output è quindi compatto e leggibile (`fill:Machine`,
`telenor:hasNeighbor`, ...) invece che la forma espansa con URI completi che
si otterrebbe altrimenti. Lo script verifica anche, per ogni file, che il
grafo RDF ottenuto ri-parsando il `.jsonld` generato sia isomorfo al grafo
del `.ttl` originale (non solo che il JSON-LD sia sintatticamente valido) —
confermato per tutti e 23 i file, e confermato separatamente eseguendo
l'intera validazione SHACL usando **solo** i file in `jsonld/` (stesso
conteggio di triple, stesso esito `CONFORMS`) come prova di equivalenza
funzionale, non solo sintattica, col Turtle.

## Come interrogare i dati (SPARQL)

Ogni file in `queries/` è una query SPARQL 1.1 completa e autonoma (prefissi
inclusi), eseguibile con qualunque motore — `scripts/validate.py --queries`,
`rdflib`, Apache Jena/Fuseki, GraphDB, ecc. Le query 1-9 girano sui dati FILL; le
query 10-11 sono le Resource CQ su GPU/CPU ed energia rinnovabile (Sez. 3 del
paper) — originariamente template vuoti perché FILL non porta questo tipo di
dato, ora popolate dai 40 edge cluster Telenor; la query 12 è specifica di
Telenor (collegamenti senza dati di banda/errore misurati); le query 13-14 sono
specifiche di GATE (topic Kafka senza produttore/consumatore; confronto tra
`intend:dependsOn` esplicito e la dipendenza implicita dal flusso dei topic).

## Decisioni di modellazione — dove leggerle

Ogni scelta non ovvia è documentata **nel file stesso**, come commento accanto
all'assioma rilevante (non in un documento separato, per restare sempre
sincronizzata col codice). I punti principali:

- **`ontology/external/tio-reference.ttl`**: perché esiste uno stub locale di TIO
  invece di un `owl:imports` reale verso TM Forum (che richiede membership), e come
  sostituirlo se ottieni i file ufficiali.
- **`ontology/modules/intend-resource.ttl` e `intend-application.ttl`**: come si
  risolve l'incoerenza del paper su `executesOn` (definito con domain/range opposti
  in Sez. 5.1.3 e 5.1.4) tramite una coppia `owl:inverseOf` (`executesOn`/`hosts`).
- **`ontology/modules/intend-intent.ttl`**: perché `hasTarget`/`hasCondition` non
  hanno un `rdfs:domain` fisso (per supportare sia la lettura "piatta" del testo
  che quella annidata sotto `Expectation` della Fig. 3), e come la cardinalità
  canonica viva invece in `shapes/intend-shapes-intent.ttl`.
- **`shapes/intend-shapes-resource.ttl`**: perché la cardinalità `consistsIn` di
  Fig. 2 (1..* business, 0..* customer) NON è un vincolo per-istanza su ogni
  `Resource`, ma si applica solo a un eventuale individuo-aggregato di primo
  livello (vedi `data:FillContinuum` in `examples/fill-instance-data.ttl` per
  l'esempio d'uso).
- **`extensions/intend-fill-extension.ttl`**: perché esiste `fill:MachineType`
  distinta da `fill:Machine` — la prima è un modello/catalogo (con il proprio
  profilo di servizi/container), la seconda un'unità specifica di proprietà di
  un cliente (es. MA-01). `fill:hasAvailableContainer` (MachineType → Container)
  non è ridondante rispetto alle altre quattro proprietà (offersService/
  requires/calls/compatibleWithMachineType): verificato empiricamente che il KG
  reale include container aggiuntivi non derivabili da quella catena.
- **`examples/fill-catalog-data.ttl`** (intestazione del file): catalogo migrato
  da un KG JSON-LD reale fornito dall'utente (non più ricostruito dall'OCR del
  paper) — elenca le anomalie trovate nella fonte (un Component7 mancante, un
  riferimento circolare su Container30, due Service senza componenti, ecc.) e
  come sono state gestite (senza inventare dati mancanti).
- **`examples/fill-instance-data.ttl`** (intestazione del file): quali dati sono
  affidabilmente estratti dal paper (Fig. 6 per utenti/macchine) e quali sono
  dichiaratamente illustrativi (i ruoli/permessi specifici di Pablo/Mary/Amira;
  la riassegnazione di MA-02/MA-04 a tipi macchina reali, dato che il KG non
  copriva "Machine6"/"Machine7" del paper). I container attesi dei 10 intent
  d'esempio sono ricalcolati e verificati contro il catalogo reale, non più
  copiati dalla Tabella 5 del paper.
- **`extensions/intend-telenor-extension.ttl`**: perché `telenor:EdgeCluster` è
  dichiarata sottoclasse SIA di `intend:EdgeDevice` SIA di `intend:BusinessResource`
  (nessun conflitto: solo `BusinessResource`/`CustomerResource` sono
  `owl:disjointWith`, non `EdgeDevice`) — cattura sia la posizione nel continuum
  sia la proprietà lato-provider, e rende `telenor:EdgeCluster` immediatamente
  compatibile con le query 10/11 che filtrano su `intend:BusinessResource`.
  `telenor:NetworkLink` invece NON è una sottoclasse di `intend:Resource`: la
  semantica di `sosa:Platform` ("ospita altre entità") non si adatta a un
  collegamento, e `intend:consistsIn` (l'unica relazione Resource→Resource
  esistente) è compositiva/gerarchica, non di adiacenza di rete — un caso reale
  in cui NON forzare un fit esistente è stata la scelta più onesta.
- **`extensions/intend-telenor-extension.ttl`** (commento sopra le datatype
  properties): perché `telenor:hasLatency`/`telenor:bandwidthTbps` ecc. sono
  proprietà nuove e indipendenti invece di riusare/sottoproprietà di
  `intend:hasLatency`/`intend:requiresBandwidth` (già con `rdfs:domain
  intend:Application` in `intend-application.ttl`): un `rdfs:domain` già fissato
  su una proprietà si applica cumulativamente a ogni suo riuso nel grafo caricato
  — riusarla per `telenor:NetworkLink` avrebbe fatto inferire (erroneamente) che
  ogni NetworkLink è anche un'Application. Non è un problema teorico: è la stessa
  ragione per cui `fill:ipAddress` (estensione FILL) è una proprietà indipendente
  invece di una sotto-proprietà di qualcosa con dominio incompatibile.
- **`examples/telenor-network-data.ttl`** (intestazione del file): 40 collegamenti
  senza banda misurata e 34 senza tasso di errore pacchetti nella fonte reale
  ("nan Tbit/s"/"nan packets/s") — omessi (non asserito il dato, non fabbricato
  uno zero), non gli stessi 40≠34 collegamenti (verificato via script); vedi
  `queries/12-telenor-links-missing-data.rq` per renderlo interrogabile invece di
  solo documentato in un commento.
- **`extensions/intend-gate-extension.ttl`**: perché `gate:Microservice` NON
  introduce una propria proprietà di dipendenza — usa direttamente
  `intend:dependsOn` (Application→Application) invece di dichiarare una
  sotto-proprietà come `fill:requires`/`fill:calls`. A differenza di FILL
  (dominio/range più stretti di quelli generici) e di Telenor (`hasLatency`
  ecc. avevano bisogno di proprietà indipendenti per evitare inquinamento del
  dominio), qui il dominio/range di `intend:dependsOn` combacia esattamente una
  volta che `gate:Microservice` è sottoclasse di `intend:Application` — nessuna
  proprietà nuova serve. `gate:KafkaTopic` è promossa a individuo di prima classe
  invece di restare una stringa (come nella fonte), per rendere interrogabile il
  grafo produttore/consumatore (query 13-14).
- **`examples/gate-microservices-data.ttl`** (intestazione del file): diversi
  `gate:Parameter` hanno più di un valore `gate:description` (fino a 6) — lo
  stesso nome di parametro ricorre in più microservizi e la fonte sembra fondere
  la descrizione di ogni occorrenza in ogni altra occorrenza dello stesso nome;
  tutte le descrizioni sono state preservate, nessuna scartata o scelta come
  "quella giusta". Due apparenti disallineamenti singolare/plurale nei nomi dei
  topic (`object_in_zone_detection` vs `...detections`, `traffic_jam_detector`
  vs `...detections`) sono stati mantenuti come topic distinti, non uniti — sono
  esattamente la causa dell'unico caso in cui `intend:dependsOn` esplicito e il
  grafo di flusso implicito via topic Kafka non coincidono (verificato via
  `queries/14-gate-dependson-vs-topic-flow.rq`).

## Come estendere l'ontologia

`extensions/intend-fill-extension.ttl`, `intend-telenor-extension.ttl` e
`intend-gate-extension.ttl` sono tre esempi completi di estensione di dominio,
ciascuno con un problema di modellazione diverso già risolto e documentato nel
file stesso: sotto-proprietà con dominio/range più stretti (FILL), proprietà
nuove e indipendenti per evitare di inquinare il dominio di proprietà core già
vincolate (Telenor), riuso diretto di una proprietà core quando dominio/range
combaciano già (GATE, `intend:dependsOn`). Tutte e tre aggiungono classi e
proprietà definite come sottoclassi/sotto-proprietà (o riusi diretti) di
termini `intend:` core, senza toccare nulla sotto `ontology/modules/`. Per il
tuo dominio:
1. Crea un nuovo file in `extensions/` con `owl:imports <https://w3id.org/intend/ontology>`.
2. Aggiungi le tue classi come `rdfs:subClassOf` della classe INTEND pertinente
   (`intend:Resource`, `intend:Application`, `intend:User`, ...).
3. Aggiungi le tue proprietà come `rdfs:subPropertyOf` della proprietà INTEND
   pertinente quando esiste un parallelo semantico (vedi `fill:runsOn
   rdfs:subPropertyOf intend:executesOn` come modello).
4. Scrivi le shape SHACL corrispondenti in un nuovo file sotto `shapes/`.
5. Rilancia `python scripts/validate.py` per verificare che tutto continui a essere
   sintatticamente corretto e conforme.

## Limiti noti

- Il namespace `tio:` in `ontology/external/tio-reference.ttl` è una ricostruzione
  locale best-effort, non il file ufficiale TM Forum TIO v3.6.0 (non liberamente
  distribuibile). Sostituiscilo se hai accesso alla membership TM Forum.
- Le proprietà osservabili (`Throughput`, `Latency`, `Bandwidth`, ...) sono
  modellate nella TBox ma non popolate nell'esempio FILL, perché la validazione
  del paper (Sez. 6) verte su selezione di servizi/container, non su vincoli di
  performance quantitativi.
- `examples/fill-catalog-data.ttl` contiene un `Container30` senza componente
  padre assegnato (nella fonte il suo `isContainerOf` puntava a se stesso — un
  bug della fonte, non corretto inventando dati) e due Service (Data Xplorer,
  Thermo Stability) senza componenti collegati — così come nella fonte.
- Il catalogo FILL (`fill:requires`/`fill:calls`/`fill:offersService`/
  `fill:compatibleWithMachineType`/`fill:hasAvailableContainer`) è ora popolato
  con dati reali (era il gap principale segnalato nelle revisioni precedenti);
  manca ancora un livello "cliente" reale nel KG fornito (utenti, macchine
  possedute) — quello resta l'esempio illustrativo Pablo/Mary/Amira basato sulla
  Fig. 6 del paper, con i tipi macchina riassegnati a valori realmente esistenti
  nel catalogo (vedi header di `examples/fill-instance-data.ttl`).
- `examples/telenor-network-data.ttl` non ha dati né di utenti/intent né di
  applicazioni deployate — è puro livello Resource (catalogo infrastrutturale),
  a differenza di FILL che copre anche Intent/Workflow. Il costo (`aeros:
  costOfCompute`, migrato come `telenor:costOfCompute`) non specifica valuta o
  unità nella fonte: preservato come numero grezzo, utilizzabile solo per
  confronti relativi tra cluster, non come costo assoluto.
- `examples/gate-microservices-data.ttl`, come Telenor, non ha dati di
  utenti/intent — è puro livello Application (catalogo di microservizi). Nella
  fonte, `gate:chartRepository` è presente solo per 8 dei 16 microservizi
  (esattamente quelli che sono target di almeno un `intend:dependsOn` di un
  altro microservizio — correlazione verificata via script, non imposta come
  regola di validazione). Le richieste/limiti CPU/memoria Kubernetes sono
  identici per tutti e 16 i microservizi in questo snapshot (0.1/1 core,
  512Mi/4Gi) — il modello (`gate:requestsCpuCores`/`gate:limitsCpuCores`/
  `gate:requestsMemoryMiB`/`gate:limitsMemoryMiB`) supporta valori diversi per
  future evoluzioni della pipeline, anche se i dati attuali non li mostrano.
  `gate:dataType` sui parametri è l'annotazione di tipo Python della fonte
  (es. `"Union[int, NoneType]"`), non un tipo XSD.
