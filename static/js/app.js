// Knowledge Graph Visualizer Application
class KnowledgeGraphApp {
    constructor() {
        this.currentRepository = null;
        this.queryEditor = null;
        this.graphData = { nodes: [], links: [] };
        this.simulation = null;
        this.svg = null;
        this.currentResults = null;
        
        this.init();
    }

    init() {
        console.log('Initializing Knowledge Graph App...');
        try {
            this.setupEventListeners();
            this.initializeQueryEditor();
            this.loadRepositories();
            this.setupGraphVisualization();
            console.log('Knowledge Graph App initialized successfully');
        } catch (error) {
            console.error('Error initializing app:', error);
        }
    }

    setupEventListeners() {
        // Repository selection
        document.getElementById('repositorySelect').addEventListener('change', (e) => {
            this.selectRepository(e.target.value);
        });

        document.getElementById('refreshRepos').addEventListener('click', () => {
            this.loadRepositories();
        });

        // Query controls
        document.getElementById('executeQuery').addEventListener('click', () => {
            this.executeQuery();
        });

        document.getElementById('clearQuery').addEventListener('click', () => {
            this.clearQuery();
        });

        document.getElementById('loadExample').addEventListener('click', () => {
            this.loadExampleQuery();
        });

        // Visualization controls
        document.getElementById('resetZoom').addEventListener('click', () => {
            this.resetZoom();
        });

        document.getElementById('centerGraph').addEventListener('click', () => {
            this.centerGraph();
        });

        document.getElementById('layoutSelect').addEventListener('change', (e) => {
            this.changeLayout(e.target.value);
        });

        // Results controls
        document.getElementById('exportResults').addEventListener('click', () => {
            this.exportResults();
        });

        // Modal controls
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideModal();
            });
        });

        // Click outside modal to close
        document.getElementById('errorModal').addEventListener('click', (e) => {
            if (e.target.id === 'errorModal') {
                this.hideModal();
            }
        });
    }

    initializeQueryEditor() {
        console.log('Initializing query editor...');
        const textarea = document.getElementById('queryEditor');
        if (!textarea) {
            console.error('Query editor textarea not found!');
            return;
        }

        try {
            this.queryEditor = CodeMirror.fromTextArea(textarea, {
                mode: 'application/sparql-query',
                theme: 'monokai',
                lineNumbers: true,
                autoCloseBrackets: true,
                matchBrackets: true,
                indentWithTabs: false,
                indentUnit: 2,
                lineWrapping: true
            });

            this.queryEditor.on('change', () => {
                this.updateQueryStatus();
            });
            
            console.log('Query editor initialized successfully');
        } catch (error) {
            console.error('Error initializing query editor:', error);
        }
    }

    async loadRepositories() {
        console.log('Loading repositories...');
        this.showLoading();
        try {
            const response = await fetch('/repositories');
            console.log('Repository response status:', response.status);
            const data = await response.json();
            console.log('Repository data:', data);
            
            if (response.ok) {
                this.populateRepositorySelect(data.repositories);
                this.updateStatus('Repositories loaded successfully', 'success');
                console.log('Repositories loaded successfully:', data.repositories);
            } else {
                throw new Error(data.error || 'Error loading repositories');
            }
        } catch (error) {
            console.error('Error loading repositories:', error);
            this.showError('Error loading repositories: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    populateRepositorySelect(repositories) {
        const select = document.getElementById('repositorySelect');
        select.innerHTML = '<option value="">Select a repository...</option>';
        
        repositories.forEach(repo => {
            const option = document.createElement('option');
            option.value = repo;
            option.textContent = repo;
            select.appendChild(option);
        });
    }

    async selectRepository(repositoryId) {
        if (!repositoryId) {
            this.currentRepository = null;
            this.updateRepositoryInfo('No repository selected');
            document.getElementById('executeQuery').disabled = true;
            return;
        }

        this.currentRepository = repositoryId;
        document.getElementById('executeQuery').disabled = false;
        
        try {
            const response = await fetch(`/repository/${repositoryId}/info`);
            const data = await response.json();
            
            if (response.ok) {
                const info = data.info;
                const infoText = `Repository: ${repositoryId} | Triples: ${info.triple_count || 'N/A'} | Status: ${info.state || 'N/A'}`;
                this.updateRepositoryInfo(infoText);
            } else {
                this.updateRepositoryInfo(`Repository: ${repositoryId} (Information not available)`);
            }
        } catch (error) {
            this.updateRepositoryInfo(`Repository: ${repositoryId} (Error loading info)`);
        }
    }

    async executeQuery() {
        console.log('Executing query...');
        if (!this.currentRepository) {
            console.error('No repository selected');
            this.showError('Please select a repository first');
            return;
        }

        const query = this.queryEditor.getValue().trim();
        console.log('Query:', query);
        if (!query) {
            console.error('No query provided');
            this.showError('Please enter a SPARQL query');
            return;
        }

        this.showLoading();
        this.updateQueryStatus('Executing query...', 'warning');

        try {
            const formData = new FormData();
            formData.append('repository', this.currentRepository);
            formData.append('query', query);
            formData.append('format', 'json');

            console.log('Sending query to repository:', this.currentRepository);
            const response = await fetch('/query', {
                method: 'POST',
                body: formData
            });

            console.log('Query response status:', response.status);
            const data = await response.json();
            console.log('Query response data:', data);

            if (response.ok) {
                // Handle the nested structure from GraphDB
                let actualResults = data.results;
                console.log('Raw API results:', actualResults);
                
                if (actualResults && actualResults.results && actualResults.results.bindings) {
                    // GraphDB returns nested structure: results.results.bindings
                    actualResults = actualResults.results;
                    console.log('Extracted nested results:', actualResults);
                } else if (actualResults && actualResults.bindings) {
                    // Direct structure: results.bindings
                    console.log('Using direct results structure');
                } else {
                    console.warn('Unexpected results structure:', actualResults);
                }
                
                this.currentResults = actualResults;
                console.log('Final results for processing:', actualResults);
                this.displayResults(actualResults);
                this.visualizeGraph(actualResults);
                this.updateQueryStatus('Query executed successfully', 'success');
            } else {
                throw new Error(data.error || 'Error executing query');
            }
        } catch (error) {
            console.error('Error executing query:', error);
            this.showError('Error executing query: ' + error.message);
            this.updateQueryStatus('Error executing query', 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayResults(results) {
        console.log('Displaying results:', results);
        const container = document.getElementById('resultsTable');
        const countElement = document.getElementById('resultsCount');
        const exportBtn = document.getElementById('exportResults');

        if (!results || !results.bindings || results.bindings.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>No results found</p>
                </div>
            `;
            countElement.textContent = '0 results';
            exportBtn.disabled = true;
            return;
        }

        const bindings = results.bindings;
        
        // Get variables from head.vars or extract from first binding
        let variables = [];
        if (results.head && results.head.vars) {
            variables = results.head.vars;
        } else if (bindings.length > 0) {
            // Extract variable names from first binding
            variables = Object.keys(bindings[0]);
        }
        
        console.log('Variables found:', variables);

        // Create table
        let tableHTML = '<table><thead><tr>';
        variables.forEach(variable => {
            tableHTML += `<th>${variable}</th>`;
        });
        tableHTML += '</tr></thead><tbody>';

        bindings.forEach(binding => {
            tableHTML += '<tr>';
            variables.forEach(variable => {
                const value = binding[variable];
                let cellContent = '';
                if (value) {
                    if (value.type === 'uri') {
                        cellContent = `<a href="${value.value}" target="_blank" title="${value.value}">${this.shortenUri(value.value)}</a>`;
                    } else {
                        cellContent = value.value;
                    }
                }
                tableHTML += `<td>${cellContent}</td>`;
            });
            tableHTML += '</tr>';
        });

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
        countElement.textContent = `${bindings.length} results`;
        exportBtn.disabled = false;
    }

    visualizeGraph(results) {
        console.log('Visualizing graph with results:', results);
        if (!results || !results.bindings || results.bindings.length === 0) {
            console.log('No results to visualize, clearing graph');
            this.clearGraph();
            return;
        }

        console.log('Converting results to graph data...');
        const graphData = this.convertResultsToGraph(results);
        console.log('Graph data:', graphData);
        this.updateGraph(graphData);
    }

    convertResultsToGraph(results) {
        const nodes = new Map();
        const links = [];

        results.bindings.forEach(binding => {
            // Try to identify subject, predicate, object pattern
            const vars = Object.keys(binding);
            
            if (vars.includes('subject') && vars.includes('predicate') && vars.includes('object')) {
                // Standard SPO pattern
                const subject = binding.subject;
                const predicate = binding.predicate;
                const object = binding.object;

                // Add subject node
                if (subject && !nodes.has(subject.value)) {
                    nodes.set(subject.value, {
                        id: subject.value,
                        label: this.shortenUri(subject.value),
                        type: subject.type,
                        fullUri: subject.value
                    });
                }

                // Add object node
                if (object && !nodes.has(object.value)) {
                    nodes.set(object.value, {
                        id: object.value,
                        label: object.type === 'literal' ? object.value : this.shortenUri(object.value),
                        type: object.type,
                        fullUri: object.value
                    });
                }

                // Add link
                if (subject && object && predicate) {
                    links.push({
                        source: subject.value,
                        target: object.value,
                        label: this.shortenUri(predicate.value),
                        predicate: predicate.value
                    });
                }
            } else {
                // Generic pattern - create nodes for all variables
                vars.forEach(variable => {
                    const value = binding[variable];
                    if (value && !nodes.has(value.value)) {
                        nodes.set(value.value, {
                            id: value.value,
                            label: value.type === 'literal' ? value.value : this.shortenUri(value.value),
                            type: value.type,
                            fullUri: value.value,
                            variable: variable
                        });
                    }
                });
            }
        });

        return {
            nodes: Array.from(nodes.values()),
            links: links
        };
    }

    setupGraphVisualization() {
        const container = document.getElementById('graphContainer');
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Clear existing content
        container.innerHTML = '';

        // Create SVG
        this.svg = d3.select('#graphContainer')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Add arrow marker
        this.svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 15)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#95a5a6');

        // Create zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.svg.select('.graph-group').attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Create main group for graph elements
        this.svg.append('g').attr('class', 'graph-group');

        // Store zoom behavior for later use
        this.zoomBehavior = zoom;
    }

    updateGraph(graphData) {
        if (!graphData || graphData.nodes.length === 0) {
            this.clearGraph();
            return;
        }

        this.graphData = graphData;
        const container = document.getElementById('graphContainer');
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Update simulation
        this.simulation = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        const g = this.svg.select('.graph-group');
        g.selectAll('*').remove();

        // Create links
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(graphData.links)
            .enter().append('line')
            .attr('class', 'link');

        // Create link labels
        const linkLabel = g.append('g')
            .attr('class', 'link-labels')
            .selectAll('text')
            .data(graphData.links)
            .enter().append('text')
            .attr('class', 'link-label')
            .text(d => d.label);

        // Create nodes
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(graphData.nodes)
            .enter().append('circle')
            .attr('class', d => `node ${d.type}`)
            .attr('r', d => d.type === 'literal' ? 8 : 12)
            .call(d3.drag()
                .on('start', (event, d) => this.dragstarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragended(event, d)));

        // Create node labels
        const nodeLabel = g.append('g')
            .attr('class', 'node-labels')
            .selectAll('text')
            .data(graphData.nodes)
            .enter().append('text')
            .attr('class', 'node-label')
            .attr('dy', -15)
            .text(d => d.label.length > 20 ? d.label.substring(0, 20) + '...' : d.label);

        // Add tooltips
        node.append('title')
            .text(d => `${d.type}: ${d.fullUri || d.id}`);

        // Update positions on simulation tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);

            nodeLabel
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });

        this.updateGraphStats();
    }

    clearGraph() {
        const container = document.getElementById('graphContainer');
        container.innerHTML = `
            <div class="graph-placeholder">
                <i class="fas fa-project-diagram"></i>
                <p>Select a repository and execute a query to visualize the graph</p>
            </div>
        `;
        this.updateGraphStats(0, 0);
    }

    updateGraphStats(nodes = null, links = null) {
        const statsElement = document.getElementById('graphStats');
        if (nodes === null) nodes = this.graphData.nodes.length;
        if (links === null) links = this.graphData.links.length;
        statsElement.textContent = `Nodes: ${nodes}, Links: ${links}`;
    }

    // Graph interaction methods
    dragstarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    resetZoom() {
        if (this.svg && this.zoomBehavior) {
            this.svg.transition().duration(750).call(
                this.zoomBehavior.transform,
                d3.zoomIdentity
            );
        }
    }

    centerGraph() {
        if (this.simulation && this.graphData.nodes.length > 0) {
            const container = document.getElementById('graphContainer');
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            this.simulation
                .force('center', d3.forceCenter(width / 2, height / 2))
                .alpha(0.3)
                .restart();
        }
    }

    changeLayout(layoutType) {
        if (!this.simulation || this.graphData.nodes.length === 0) return;

        const container = document.getElementById('graphContainer');
        const width = container.clientWidth;
        const height = container.clientHeight;

        switch (layoutType) {
            case 'force':
                this.simulation
                    .force('link', d3.forceLink(this.graphData.links).id(d => d.id).distance(100))
                    .force('charge', d3.forceManyBody().strength(-300))
                    .force('center', d3.forceCenter(width / 2, height / 2));
                break;
            case 'circular':
                this.simulation
                    .force('link', null)
                    .force('charge', null)
                    .force('center', d3.forceCenter(width / 2, height / 2));
                
                const radius = Math.min(width, height) / 3;
                this.graphData.nodes.forEach((node, i) => {
                    const angle = (i / this.graphData.nodes.length) * 2 * Math.PI;
                    node.fx = width / 2 + radius * Math.cos(angle);
                    node.fy = height / 2 + radius * Math.sin(angle);
                });
                break;
            case 'hierarchical':
                this.simulation
                    .force('link', d3.forceLink(this.graphData.links).id(d => d.id).distance(80))
                    .force('charge', d3.forceManyBody().strength(-200))
                    .force('center', d3.forceCenter(width / 2, height / 2))
                    .force('y', d3.forceY().strength(0.1));
                break;
        }

        this.simulation.alpha(0.3).restart();
    }

    // Utility methods
    clearQuery() {
        this.queryEditor.setValue('');
        this.updateQueryStatus();
    }

    loadExampleQuery() {
        const exampleQuery = `# Example query to visualize the graph
SELECT ?subject ?predicate ?object
WHERE {
    ?subject ?predicate ?object .
}
LIMIT 20`;
        
        this.queryEditor.setValue(exampleQuery);
        this.updateQueryStatus();
        console.log('Example query loaded');
    }

    updateQueryStatus(message = null, type = null) {
        const statusElement = document.getElementById('queryStatus');
        if (message) {
            statusElement.textContent = message;
            statusElement.className = `status-text ${type || ''}`;
        } else {
            const query = this.queryEditor.getValue().trim();
            if (query) {
                statusElement.textContent = 'Query ready for execution';
                statusElement.className = 'status-text';
            } else {
                statusElement.textContent = 'Enter a SPARQL query';
                statusElement.className = 'status-text';
            }
        }
    }

    updateRepositoryInfo(info) {
        document.getElementById('repoInfo').textContent = info;
    }

    updateStatus(message, type) {
        // Could be used for general status updates
        console.log(`${type}: ${message}`);
    }

    exportResults() {
        if (!this.currentResults || !this.currentResults.bindings) {
            this.showError('No results to export');
            return;
        }

        const bindings = this.currentResults.bindings;
        
        // Get variables from head.vars or extract from first binding
        let variables = [];
        if (this.currentResults.head && this.currentResults.head.vars) {
            variables = this.currentResults.head.vars;
        } else if (bindings.length > 0) {
            variables = Object.keys(bindings[0]);
        }

        // Create CSV content
        let csvContent = variables.join(',') + '\n';
        bindings.forEach(binding => {
            const row = variables.map(variable => {
                const value = binding[variable];
                return value ? `"${value.value.replace(/"/g, '""')}"` : '';
            });
            csvContent += row.join(',') + '\n';
        });

        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sparql_results_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    shortenUri(uri) {
        if (!uri || typeof uri !== 'string') return uri;
        
        // Common prefixes
        const prefixes = {
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf:',
            'http://www.w3.org/2000/01/rdf-schema#': 'rdfs:',
            'http://www.w3.org/2001/XMLSchema#': 'xsd:',
            'http://www.w3.org/2002/07/owl#': 'owl:',
            'https://intendproject.eu/schema/': 'intend:',
            'https://intendproject.eu/gate/': 'gate:',
            'https://schema.org/': 'schema:'
        };

        for (const [fullPrefix, shortPrefix] of Object.entries(prefixes)) {
            if (uri.startsWith(fullPrefix)) {
                return shortPrefix + uri.substring(fullPrefix.length);
            }
        }

        // If no prefix match, show last part of URI
        const lastSlash = uri.lastIndexOf('/');
        const lastHash = uri.lastIndexOf('#');
        const lastSeparator = Math.max(lastSlash, lastHash);
        
        if (lastSeparator > 0 && lastSeparator < uri.length - 1) {
            return uri.substring(lastSeparator + 1);
        }

        return uri;
    }

    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorModal').style.display = 'flex';
    }

    hideModal() {
        document.getElementById('errorModal').style.display = 'none';
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new KnowledgeGraphApp();
});
