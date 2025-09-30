# Docker Development Setup

This setup provides a complete development environment with GraphDB and your Flask application running in containers with hot reloading capabilities.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

### Starting the Environment

```powershell
# Start all services
docker-compose up -d

# Or use the PowerShell helper script
.\docker-dev.ps1 up
```

### Accessing Services

- **Flask Application**: http://localhost:5000
- **GraphDB Workbench**: http://localhost:7200
- **Health Check**: http://localhost:5000/health

## 🔧 Development Features

### Hot Reloading
- Code changes are automatically reflected without rebuilding containers
- The entire project directory is mounted as a volume
- Flask runs in debug mode for instant updates

### Data Persistence
- GraphDB data is persisted in Docker volumes
- Uploads directory is mounted for file persistence
- Data survives container restarts

## 📋 Management Commands

### Using PowerShell Script
```powershell
# Start services
.\docker-dev.ps1 up

# Stop services
.\docker-dev.ps1 down

# Rebuild app container
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

## 🏗️ Architecture

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

## 🔍 Troubleshooting

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

## 🧹 Cleanup

### Remove Containers Only
```bash
docker-compose down
```

### Remove Containers and Volumes (⚠️ Data Loss)
```bash
docker-compose down -v
```

### Remove Everything Including Images
```bash
docker-compose down -v --rmi all
```

## 📝 Configuration

### Environment Variables
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `GRAPHDB_BASE_URL=http://graphdb:7200`

### GraphDB Configuration
- Heap size: 2GB
- Java options: `-Xmx2g -Xms1g`
- Health check interval: 30s

## 🔒 Security Notes

- Services are isolated in a custom network
- Only necessary ports are exposed
- GraphDB data is persisted in named volumes
- No sensitive data in environment variables
