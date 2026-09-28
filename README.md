# inGraph

```bash
cd INTEND-ontology
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/validate.py
```

Interfaccia web + GraphDB:

```bash
cd gui/inGraph
docker compose up
# then open http://localhost:5000
```
