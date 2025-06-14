# inGraph

## Overview

inGraph is a tool designed to build and maintain a Knowledge Graph (KG) tailored to the INTED use cases. It ensures seamless access to KG data for other tools and supports dynamic updates based on evolving requirements.

## Features

- **Knowledge Graph Construction**: Builds a structured Knowledge Graph customized to different applications.
- **Data Retrieval**: Allows efficient access to specific data within the KG.
- **Interoperability**: Ensures that other tools can interact with the KG effortlessly.
- **Dynamic Maintenance**: Adapts and updates the KG to meet changing use case requirements.
- **REST API Support**: Provides RESTful APIs to interact with the Knowledge Graph programmatically.

---

## Project Structure

- **`KG/` folder**: Contains the Knowledge Graphs built from the analysis of the Telenor, FILL, and GATE use cases, starting from raw data.
- **`query/` folder**: Includes simple SPARQL query test examples.
- **`InGraphInChatComunication.py`**: A specific script used to interface this infrastructure with the inChat component for data exchange.
- **`InGraphApp.py`**: Backbone of the inGraph application.

---

## Requirements

Before running the application, make sure you have:

1.**Python 3.7+** installed.

2.**GraphDB** installed and running locally on `http://localhost:7200`.

You can download GraphDB from the official site:

https://www.ontotext.com/products/graphdb/

### Install Python dependencies

```bash

pipinstall-rrequirements.txt

```

---

## ▶️ Running the Application

After installing dependencies and starting GraphDB:

```bash

pythoninGraphApp.py

```

The API will be available at:

`http://0.0.0.0:5000`

---

## 🚀 Available Endpoints

| Method | Endpoint                 | Description                                  |

| ------ | ------------------------ | -------------------------------------------- |

| GET    | `/health`              | Check if the service and GraphDB are healthy |

| GET    | `/repositories`        | List all available repositories              |

| POST   | `/repositories/create` | Create a new repository                      |

| POST   | `/upload`              | Upload a JSON-LD or JSON file                |

| POST   | `/query`               | Execute a SPARQL query                       |

| POST   | `/update`              | Execute SPARQL INSERT/DELETE/UPDATE          |

---

## 🧪 Example Usage

### Upload JSON-LD

```bash

curl-XPOSThttp://0.0.0.0:5000/upload\

  -F "repository=second-graph" \

  -F"file=@FILL__KG.jsonld"

```

### SPARQL Query

```bash

curl-XPOSThttp://0.0.0.0:5000/query\

  -F "repository=second-graph" \

  -F"file=@machine5-query.sparql"\

  -F "format=json"

```

### SPARQL Update/Delete

```bash

curl-XPOSThttp://0.0.0.0:5000/update\

  -F "repository=second-graph" \

  -F"file=@query_delete.sparql"

```



---
## Deployment

The infrastructure is currently deployed in test mode at:

🔗 [http://notae-system.diag.uniroma1.it:5000/](http://notae-system.diag.uniroma1.it:5000/)
---

## License

This project is provided under the MIT License.
