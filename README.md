# inGraph

## Overview
inGraph is a tool designed to build and maintain a Knowledge Graph (KG) tailored to the INTED use cases. It ensures seamless access to KG data for other tools and supports dynamic updates based on evolving requirements.

## Features
- **Knowledge Graph Construction**: Builds a structured Knowledge Graph customized to different applications.
- **Data Retrieval**: Allows efficient access to specific data within the KG.
- **Interoperability**: Ensures that other tools can interact with the KG effortlessly.
- **Dynamic Maintenance**: Adapts and updates the KG to meet changing use case requirements.
- **REST API Support**: Provides RESTful APIs to interact with the Knowledge Graph programmatically.

## Usage
inGraph serves as the backbone for knowledge-driven applications, providing structured and queryable data to enhance decision-making, automation, and analytics.

## Tools Interaction

### **Tools with Which inGraph Interacts**
   - **inGraph** interacts with any tools that require access to the Knowledge Graph. It has a focus on the WP4 tools, but it can be also by the other INTED tools,

### **How inGraph Interacts with Other Tools**
   - **Direct API Invocation**: Other tools can interact with **inGraph** via its **REST API**. This enables fetching or updating data within the Knowledge Graph.

### **Exposed API for Access**
   **inGraph** exposes **REST APIs** that allow other tools to interact with the Knowledge Graph.

   **API Endpoints**:
   - Under development

### **Message Bus Usage**
   - **inGraph** does not currently plan to use a message bus.

### **Data Shared Between Tools**
   - **Inputs**: Data for creating or updating nodes/relationships.
   - **Outputs**: Query results for retrieving nodes or relationships.

### Authentication and Security
  **inGraph** exposes a REST API, and the APIs will use a key to identify the Knowledge Graph for individual use cases, ensuring secure access.

### 9. Hardware and Software Requirements

#### Hardware:
- A server with sufficient resources to handle the Knowledge Graph and its operations.

#### Software:
- **Graph Database**: A graph database like **Neo4j**.
- **Web Server**: A framework to expose the REST API, e.g., **Flask** or similar.
- **Containerization (Optional)**: Tools like **Docker** for deployment.




