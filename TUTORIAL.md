# 🎯 Tutorial: Knowledge Graph Visualizer

## 🚀 Avvio Rapido

### 1. Avvia l'Applicazione
```powershell
.\docker-dev.ps1 start
```

### 2. Apri l'Interfaccia Web
Vai su: **http://localhost:5000**

## 📊 Come Usare l'Interfaccia

### 🗂️ Selezione Repository

1. **Seleziona Repository**: Usa il dropdown per scegliere un repository GraphDB
   - Repository disponibili: GATE, FILL, TELENOR (con dati)
   - GATE1, GATE_TEST (vuoti)

2. **Informazioni Repository**: Vedrai il numero di triple e lo stato

### 💻 Editor SPARQL

1. **Query di Esempio**: Clicca "Esempio" per caricare una query predefinita
2. **Scrivi Query**: Usa l'editor con syntax highlighting
3. **Esegui Query**: Clicca "Esegui Query" per vedere i risultati

### 📈 Visualizzazione Grafo

1. **Grafo Interattivo**: I risultati appaiono come grafo D3.js
2. **Controlli**:
   - **Zoom**: Rotella del mouse
   - **Pan**: Trascina lo sfondo
   - **Drag**: Trascina i nodi
   - **Reset Zoom**: Pulsante per tornare alla vista originale
   - **Centra**: Centra il grafo nella vista

3. **Layout**:
   - **Force**: Layout a forze (default)
   - **Circular**: Layout circolare
   - **Hierarchical**: Layout gerarchico

### 📋 Risultati

1. **Tabella**: Visualizza tutti i risultati in formato tabella
2. **Export CSV**: Scarica i risultati in formato CSV
3. **Link Cliccabili**: Gli URI sono cliccabili

## 🔍 Query di Esempio

### Query Base
```sparql
SELECT ?subject ?predicate ?object
WHERE {
    ?subject ?predicate ?object .
}
LIMIT 20
```

### Query con Filtri
```sparql
SELECT ?subject ?predicate ?object
WHERE {
    ?subject ?predicate ?object .
    FILTER(isURI(?subject))
}
LIMIT 50
```

### Query per Tipi
```sparql
SELECT ?subject ?type
WHERE {
    ?subject a ?type .
}
LIMIT 30
```

### Query con Prefissi
```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?label
WHERE {
    ?subject rdfs:label ?label .
}
LIMIT 25
```

## 🎨 Interpretazione del Grafo

### Colori dei Nodi
- **Blu**: Subject (soggetti)
- **Viola**: Object (oggetti URI)
- **Arancione**: Literal (valori letterali)

### Collegamenti
- **Frecce**: Indicano la direzione della relazione
- **Etichette**: Mostrano il predicato/proprietà
- **Hover**: Mostra informazioni dettagliate

## 🛠️ Risoluzione Problemi

### Repository Vuoto
Se non vedi risultati:
1. Verifica che il repository abbia dati
2. Usa una query più semplice
3. Controlla la console del browser per errori

### Grafo Non Visualizzato
1. Assicurati che la query restituisca risultati
2. Controlla che D3.js sia caricato (console browser)
3. Prova a cambiare layout

### Performance
Per dataset grandi:
1. Usa `LIMIT` nelle query
2. Filtra i risultati con `FILTER`
3. Usa query più specifiche

## 📚 Repository di Test

### GATE (2539 triple)
Contiene dati del progetto GATE con ontologie e metadati.

### FILL (697 triple)
Dataset più piccolo per test rapidi.

### TELENOR (7580 triple)
Dataset più grande per test di performance.

## 🔧 Comandi Docker Utili

```powershell
# Visualizza log in tempo reale
.\docker-dev.ps1 logs-app

# Controlla stato servizi
.\docker-dev.ps1 status

# Verifica salute servizi
.\docker-dev.ps1 health

# Riavvia servizi
.\docker-dev.ps1 restart

# Modalità produzione
.\docker-dev.ps1 prod
```

## 💡 Suggerimenti

1. **Inizia Semplice**: Usa query con LIMIT basso per esplorare i dati
2. **Esplora Gradualmente**: Aumenta la complessità delle query
3. **Usa i Prefissi**: Rendono le query più leggibili
4. **Salva Query Utili**: Copia le query che funzionano bene
5. **Monitora Performance**: Query complesse possono richiedere tempo

## 🎯 Prossimi Passi

1. Esplora i tuoi dati con query semplici
2. Sperimenta con diversi layout di visualizzazione
3. Usa l'export CSV per analisi esterne
4. Combina più repository per analisi comparative

Buona esplorazione del tuo Knowledge Graph! 🚀
