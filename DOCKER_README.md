# 🐳 Docker Setup per Knowledge Graph Visualizer

Questo progetto utilizza Docker e Docker Compose per eseguire l'interfaccia web di visualizzazione del Knowledge Graph con GraphDB.

## 📋 Prerequisiti

- Docker Desktop installato e in esecuzione
- Almeno 4GB di RAM disponibile per GraphDB
- PowerShell (per Windows) o Bash (per Linux/Mac)

## 🚀 Avvio Rapido

### Usando lo Script di Sviluppo (Raccomandato)

```powershell
# Avvia tutti i servizi in modalità sviluppo
.\docker-dev.ps1 start

# Visualizza i log dell'interfaccia web
.\docker-dev.ps1 logs-app

# Controlla lo stato dei servizi
.\docker-dev.ps1 status

# Verifica la salute dei servizi
.\docker-dev.ps1 health
```

### Comandi Docker Manuali

```bash
# Avvia tutti i servizi
docker-compose up -d

# Controlla lo stato
docker-compose ps

# Visualizza i log
docker-compose logs -f kg-visualizer
```

## 🌐 Servizi Disponibili

### 🔬 Knowledge Graph Visualizer (Interfaccia Web)
- **Porta:** 5000
- **URL:** http://localhost:5000
- **Funzionalità:**
  - Selezione repository GraphDB
  - Editor SPARQL con syntax highlighting
  - Visualizzazione interattiva del grafo con D3.js
  - Tabella risultati con export CSV
  - Layout multipli (force, circular, hierarchical)

### 📊 GraphDB
- **Porta:** 7200
- **Workbench:** http://localhost:7200
- **Persistenza dati:** Volumi Docker (`graphdb_data`, `graphdb_work`)
- **Memoria:** 2GB heap size (dev) / 4GB (prod)
.\docker-dev.ps1 build

# View logs
.\docker-dev.ps1 logs

# Restart services
.\docker-dev.ps1 restart

# Check status
.\docker-dev.ps1 status
```

### Using Docker Compose Directly
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild specific service
docker-compose build app

# Restart specific service
docker-compose restart app
```

## Architecture

### Services
1. **GraphDB Container**
   - Image: `ontotext/graphdb:10.6.2`
   - Port: 7200
   - Persistent volumes for data storage
   - Health checks for dependency management

2. **Flask App Container**
   - Built from local Dockerfile
   - Port: 5000
   - Hot reloading enabled
   - Environment variables configured

### Networking
- Custom bridge network for service communication
- Services communicate using container names (e.g., `graphdb:7200`)

### Volumes
- **Source Code**: `.:/app` (for hot reloading)
- **Uploads**: `./uploads:/app/uploads` (file persistence)
- **GraphDB Data**: Named volumes for database persistence

## Troubleshooting

### Container Issues
```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs graphdb
docker-compose logs app

# Restart specific service
docker-compose restart app
```

### GraphDB Connection Issues
```bash
# Check GraphDB health
curl http://localhost:7200/rest/repositories

# Check app health
curl http://localhost:5000/health
```

### Hot Reloading Not Working
1. Ensure Flask debug mode is enabled
2. Check volume mounts in docker-compose.yml
3. Verify file permissions

## Cleanup

### Remove Containers Only
```bash
docker-compose down
```

### Remove Containers and Volumes (Data Loss)
```bash
docker-compose down -v
```

### Remove Everything Including Images
```bash
docker-compose down -v --rmi all
```

## Configuration

### Environment Variables
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `GRAPHDB_BASE_URL=http://graphdb:7200`

### GraphDB Configuration
- Heap size: 2GB
- Java options: `-Xmx2g -Xms1g`
- Health check interval: 30s

## Security Notes

- Services are isolated in a custom network
- Only necessary ports are exposed
- GraphDB data is persisted in named volumes
- No sensitive data in environment variables
