// Knowledge Graph Visualizer Application
class KnowledgeGraphApp {
    constructor() {
        this.currentRepository = null;
        this.queryEditor = null;
        this.graphData = { nodes: [], links: [] };
        this.simulation = null;
        this.svg = null;
        this.currentResults = null;
        this.isFullscreen = false;
        this.selectedElement = null;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        
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
        document.getElementById('repositorySelect').addEventListener('change', (e) => {
            this.selectRepository(e.target.value);
        });

        document.getElementById('refreshRepos').addEventListener('click', () => {
            this.loadRepositories();
        });

        document.getElementById('executeQuery').addEventListener('click', () => {
            this.executeQuery();
        });

        document.getElementById('clearQuery').addEventListener('click', () => {
            this.clearQuery();
        });

        document.getElementById('loadExample').addEventListener('click', () => {
            this.loadExampleQuery();
        });

        document.getElementById('resetZoom').addEventListener('click', () => {
            this.resetZoom();
        });

        document.getElementById('centerGraph').addEventListener('click', () => {
            this.centerGraph();
        });

        document.getElementById('layoutSelect').addEventListener('change', (e) => {
            this.changeLayout(e.target.value);
        });

        document.getElementById('fullscreenBtn').addEventListener('click', () => {
            this.toggleFullscreen();
        });

        document.getElementById('closeProperties').addEventListener('click', () => {
            this.closePropertiesPanel();
        });

        document.getElementById('exportResults').addEventListener('click', () => {
            this.exportResults();
        });

        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hideModal();
            });
        });

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
            const data = await response.json();
            
            if (response.ok) {
                this.populateRepositorySelect(data.repositories);
                this.updateStatus('Repositories loaded successfully', 'success');
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
            this.showError('Please select a repository first');
            return;
        }

        const query = this.queryEditor.getValue().trim();
        if (!query) {
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

            const response = await fetch('/query', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                let actualResults = data.results;
                
                if (actualResults && actualResults.results && actualResults.results.bindings) {
                    actualResults = actualResults.results;
                } else if (actualResults && actualResults.bindings) {
                    // Direct structure
                } else {
                    console.warn('Unexpected results structure:', actualResults);
                }
                
                this.currentResults = actualResults;
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
        
        let variables = [];
        if (results.head && results.head.vars) {
            variables = results.head.vars;
        } else if (bindings.length > 0) {
            variables = Object.keys(bindings[0]);
        }

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
        if (!results || !results.bindings || results.bindings.length === 0) {
            this.clearGraph();
            return;
        }

        this.lastQueryResults = results;

        const graphData = this.convertResultsToGraph(results);
        this.updateGraph(graphData);
    }

    convertResultsToGraph(results) {
        const nodes = new Map();
        const links = [];
        const triples = [];

        results.bindings.forEach(binding => {
            const vars = Object.keys(binding);
            
            if (vars.includes('subject') && vars.includes('predicate') && vars.includes('object')) {
                const subject = binding.subject;
                const predicate = binding.predicate;
                const object = binding.object;

                if (subject && predicate && object) {
                    triples.push({
                        subject: subject.value,
                        subjectLabel: this.shortenUri(subject.value),
                        predicate: predicate.value,
                        predicateLabel: this.shortenUri(predicate.value),
                        object: object.value,
                        objectLabel: object.type === 'literal' ? object.value : this.shortenUri(object.value),
                        objectType: object.type
                    });
                }

                if (subject && !nodes.has(subject.value)) {
                    nodes.set(subject.value, {
                        id: subject.value,
                        label: this.shortenUri(subject.value),
                        type: subject.type,
                        fullUri: subject.value,
                        triples: []
                    });
                }

                if (object && !nodes.has(object.value)) {
                    nodes.set(object.value, {
                        id: object.value,
                        label: object.type === 'literal' ? object.value : this.shortenUri(object.value),
                        type: object.type,
                        fullUri: object.value,
                        triples: []
                    });
                }

                if (subject && object && predicate) {
                    links.push({
                        source: subject.value,
                        target: object.value,
                        label: this.shortenUri(predicate.value),
                        predicate: predicate.value,
                        predicateLabel: this.shortenUri(predicate.value)
                    });
                }
            } else {
                vars.forEach(variable => {
                    const value = binding[variable];
                    if (value && !nodes.has(value.value)) {
                        nodes.set(value.value, {
                            id: value.value,
                            label: value.type === 'literal' ? value.value : this.shortenUri(value.value),
                            type: value.type,
                            fullUri: value.value,
                            variable: variable,
                            triples: []
                        });
                    }
                });
            }
        });

        triples.forEach(triple => {
            if (nodes.has(triple.subject)) {
                nodes.get(triple.subject).triples.push({
                    role: 'subject',
                    predicate: triple.predicateLabel,
                    predicateFull: triple.predicate,
                    value: triple.objectLabel,
                    valueFull: triple.object,
                    valueType: triple.objectType
                });
            }
            if (nodes.has(triple.object)) {
                nodes.get(triple.object).triples.push({
                    role: 'object',
                    subject: triple.subjectLabel,
                    subjectFull: triple.subject,
                    predicate: triple.predicateLabel,
                    predicateFull: triple.predicate
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

        // FIX: SVG uses 100% width/height so it always fills its container.
        // The viewBox defines a fixed coordinate system that D3 works in.
        // preserveAspectRatio ensures the graph scales uniformly.
        this.svg = d3.select('#graphContainer')
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet')
            .style('display', 'block');
        
        // Store the viewBox dimensions — these never change
        this.viewBoxWidth = width;
        this.viewBoxHeight = height;

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
        
        // Always use the fixed viewBox coordinate system
        const width = this.viewBoxWidth;
        const height = this.viewBoxHeight;

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
            .attr('class', 'link')
            .on('click', (event, d) => {
                if (this.isFullscreen && !this.isDragging) {
                    event.stopPropagation();
                    this.showEdgeProperties(d, event.currentTarget);
                }
            });

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
            .on('click', (event, d) => {
                if (this.isFullscreen && !this.isDragging) {
                    event.stopPropagation();
                    this.showNodeProperties(d, event.currentTarget);
                }
            })
            .on('dblclick', (event, d) => {
                d.fx = null;
                d.fy = null;
                d3.select(event.currentTarget).classed('pinned', false);
                if (!this.simulation.alpha() > 0.3) {
                    this.simulation.alpha(0.3).restart();
                }
            })
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
            .text(d => `${d.type}: ${d.fullUri || d.id}\n\n💡 Drag to reposition\n💡 Double-click to unlock`);

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
        this.isDragging = false;
        this.dragStartX = event.x;
        this.dragStartY = event.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
        const dx = event.x - this.dragStartX;
        const dy = event.y - this.dragStartY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            this.isDragging = true;
        }
    }

    dragended(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        
        if (this.isDragging) {
            d3.select(event.sourceEvent.target).classed('pinned', true);
        }
        
        this.isDragging = false;
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
            const width = this.viewBoxWidth;
            const height = this.viewBoxHeight;

            // Release all fixed nodes
            this.graphData.nodes.forEach(node => {
                node.fx = null;
                node.fy = null;
            });
            if (this.svg) {
                this.svg.selectAll('.node').classed('pinned', false);
            }

            this.simulation
                .force('center', d3.forceCenter(width / 2, height / 2))
                .alpha(0.5)
                .restart();
            
            this.resetZoom();
        }
    }

    fitGraphToViewBox() {
        if (!this.svg || !this.zoomBehavior) return;
        try {
            const g = this.svg.select('.graph-group');
            if (g.empty()) return;
            const bounds = g.node().getBBox();
            const vbWidth = this.viewBoxWidth;
            const vbHeight = this.viewBoxHeight;

            if (!bounds || !isFinite(bounds.width) || !isFinite(bounds.height) || bounds.width === 0 || bounds.height === 0) {
                this.resetZoom();
                return;
            }

            const scale = Math.min(4, 0.85 / Math.max(bounds.width / vbWidth, bounds.height / vbHeight));
            const translateX = vbWidth / 2 - scale * (bounds.x + bounds.width / 2);
            const translateY = vbHeight / 2 - scale * (bounds.y + bounds.height / 2);

            this.svg.transition().duration(400).call(
                this.zoomBehavior.transform,
                d3.zoomIdentity.translate(translateX, translateY).scale(scale)
            );
        } catch (e) {
            console.error('fitGraphToViewBox error:', e);
        }
    }

    changeLayout(layoutType) {
        if (!this.simulation || this.graphData.nodes.length === 0) return;

        const width = this.viewBoxWidth;
        const height = this.viewBoxHeight;

        switch (layoutType) {
            case 'force':
                this.graphData.nodes.forEach(node => { node.fx = null; node.fy = null; });
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
                this.graphData.nodes.forEach(node => { node.fx = null; node.fy = null; });
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
        console.log(`${type}: ${message}`);
    }

    exportResults() {
        if (!this.currentResults || !this.currentResults.bindings) {
            this.showError('No results to export');
            return;
        }

        const bindings = this.currentResults.bindings;
        
        let variables = [];
        if (this.currentResults.head && this.currentResults.head.vars) {
            variables = this.currentResults.head.vars;
        } else if (bindings.length > 0) {
            variables = Object.keys(bindings[0]);
        }

        let csvContent = variables.join(',') + '\n';
        bindings.forEach(binding => {
            const row = variables.map(variable => {
                const value = binding[variable];
                return value ? `"${value.value.replace(/"/g, '""')}"` : '';
            });
            csvContent += row.join(',') + '\n';
        });

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

    // =============================================
    // FULLSCREEN — fixed version
    // =============================================
    toggleFullscreen() {
        const panel = document.querySelector('.visualization-panel');
        const btn = document.getElementById('fullscreenBtn');
        
        this.isFullscreen = !this.isFullscreen;
        
        if (this.isFullscreen) {
            // --- ENTER fullscreen ---
            panel.classList.add('fullscreen');
            btn.innerHTML = '<i class="fas fa-compress"></i> Exit Fullscreen';
            
            if (this.svg) {
                this.svg.selectAll('.node').style('cursor', 'pointer');
                this.svg.selectAll('.link').style('cursor', 'pointer');
            }
            
            // After CSS transition completes, fit graph into the new large viewport
            setTimeout(() => {
                this.fitGraphToViewBox();
            }, 350);
            
        } else {
            // --- EXIT fullscreen ---
            panel.classList.remove('fullscreen');
            btn.innerHTML = '<i class="fas fa-expand"></i> Fullscreen';
            this.closePropertiesPanel();
            
            if (this.svg) {
                this.svg.selectAll('.node').style('cursor', 'default');
                this.svg.selectAll('.link').style('cursor', 'default');
            }
            
            // After CSS transition completes, reset zoom so graph fits the small container
            setTimeout(() => {
                this.resetZoom();
            }, 350);
        }
    }

    // Properties panel methods
    showNodeProperties(nodeData, element) {
        this.clearSelection();
        
        this.selectedElement = element;
        d3.select(element).classed('selected', true);
        
        const panel = document.getElementById('propertiesPanel');
        const content = document.getElementById('propertiesContent');
        const title = document.getElementById('propertiesTitle');
        
        if (!panel) {
            console.error('Properties panel not found in DOM!');
            return;
        }
        
        title.innerHTML = '<i class="fas fa-circle"></i> Node Properties';
        
        let html = '';
        
        html += `
            <div class="property-item">
                <div class="property-label">ID</div>
                <div class="property-value">${this.escapeHtml(nodeData.id)}</div>
            </div>
        `;
        
        html += `
            <div class="property-item">
                <div class="property-label">Label</div>
                <div class="property-value">${this.escapeHtml(nodeData.label)}</div>
            </div>
        `;
        
        html += `
            <div class="property-item">
                <div class="property-label">Type</div>
                <div class="property-value">${this.escapeHtml(nodeData.type)}</div>
            </div>
        `;
        
        if (nodeData.fullUri && nodeData.fullUri !== nodeData.id) {
            html += `
                <div class="property-item">
                    <div class="property-label">Full URI</div>
                    <div class="property-value">
                        <a href="${nodeData.fullUri}" target="_blank">${this.escapeHtml(nodeData.fullUri)}</a>
                    </div>
                </div>
            `;
        }
        
        if (nodeData.variable) {
            html += `
                <div class="property-item">
                    <div class="property-label">Variable</div>
                    <div class="property-value">${this.escapeHtml(nodeData.variable)}</div>
                </div>
            `;
        }
        
        if (nodeData.triples && nodeData.triples.length > 0) {
            html += `
                <div class="property-item">
                    <div class="property-label">Triples (${nodeData.triples.length})</div>
                    <div class="property-value">
            `;
            
            nodeData.triples.forEach((triple, index) => {
                if (triple.role === 'subject') {
                    html += `
                        <div style="margin-bottom: 10px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #667eea;">
                            <strong style="color: #667eea;">→</strong> 
                            <span style="color: #667eea;">${this.escapeHtml(triple.predicate)}</span> → 
                            <span style="color: #2c3e50;">${this.escapeHtml(triple.value)}</span>
                        </div>
                    `;
                } else {
                    html += `
                        <div style="margin-bottom: 10px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #764ba2;">
                            <span style="color: #2c3e50;">${this.escapeHtml(triple.subject)}</span> → 
                            <span style="color: #764ba2;">${this.escapeHtml(triple.predicate)}</span> 
                            <strong style="color: #764ba2;">→</strong>
                        </div>
                    `;
                }
            });
            
            html += `
                    </div>
                </div>
            `;
        }
        
        const excludeKeys = ['id', 'label', 'type', 'fullUri', 'variable', 'triples', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'index'];
        Object.keys(nodeData).forEach(key => {
            if (!excludeKeys.includes(key)) {
                html += `
                    <div class="property-item">
                        <div class="property-label">${this.escapeHtml(key)}</div>
                        <div class="property-value">${this.escapeHtml(String(nodeData[key]))}</div>
                    </div>
                `;
            }
        });
        
        content.innerHTML = html;
        panel.classList.add('active');
    }

    showEdgeProperties(edgeData, element) {
        this.clearSelection();
        
        this.selectedElement = element;
        d3.select(element).classed('selected', true);
        
        const panel = document.getElementById('propertiesPanel');
        const content = document.getElementById('propertiesContent');
        const title = document.getElementById('propertiesTitle');
        
        title.innerHTML = '<i class="fas fa-arrow-right"></i> Edge Properties';
        
        let html = '';
        
        const sourceNode = edgeData.source;
        const targetNode = edgeData.target;
        const sourceLabel = sourceNode.label || this.shortenUri(sourceNode.id || sourceNode);
        const targetLabel = targetNode.label || this.shortenUri(targetNode.id || targetNode);
        
        html += `
            <div class="property-item">
                <div class="property-label">Triple</div>
                <div class="property-value">
                    <div style="padding: 12px; background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%); border-radius: 8px; border-left: 4px solid #667eea;">
                        <div style="margin-bottom: 8px;">
                            <strong style="color: #667eea;">Subject:</strong><br>
                            <span style="color: #2c3e50; margin-left: 10px;">${this.escapeHtml(sourceLabel)}</span>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <strong style="color: #f39c12;">Predicate:</strong><br>
                            <span style="color: #2c3e50; margin-left: 10px;">${this.escapeHtml(edgeData.label)}</span>
                        </div>
                        <div>
                            <strong style="color: #764ba2;">Object:</strong><br>
                            <span style="color: #2c3e50; margin-left: 10px;">${this.escapeHtml(targetLabel)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        html += `
            <div class="property-item">
                <div class="property-label">Source Node</div>
                <div class="property-value">
                    <strong>Label:</strong> ${this.escapeHtml(sourceLabel)}<br>
                    <strong>URI:</strong> <a href="${sourceNode.id || sourceNode}" target="_blank" style="word-break: break-all;">${this.escapeHtml(sourceNode.id || sourceNode)}</a><br>
                    ${sourceNode.type ? `<strong>Type:</strong> ${this.escapeHtml(sourceNode.type)}` : ''}
                </div>
            </div>
        `;
        
        html += `
            <div class="property-item">
                <div class="property-label">Target Node</div>
                <div class="property-value">
                    <strong>Label:</strong> ${this.escapeHtml(targetLabel)}<br>
                    <strong>URI:</strong> <a href="${targetNode.id || targetNode}" target="_blank" style="word-break: break-all;">${this.escapeHtml(targetNode.id || targetNode)}</a><br>
                    ${targetNode.type ? `<strong>Type:</strong> ${this.escapeHtml(targetNode.type)}` : ''}
                </div>
            </div>
        `;
        
        html += `
            <div class="property-item">
                <div class="property-label">Predicate URI</div>
                <div class="property-value">
                    <a href="${edgeData.predicate}" target="_blank" style="word-break: break-all;">${this.escapeHtml(edgeData.predicate)}</a>
                </div>
            </div>
        `;
        
        const excludeKeys = ['source', 'target', 'predicate', 'predicateLabel', 'label', 'index'];
        Object.keys(edgeData).forEach(key => {
            if (!excludeKeys.includes(key) && typeof edgeData[key] !== 'object') {
                html += `
                    <div class="property-item">
                        <div class="property-label">${this.escapeHtml(key)}</div>
                        <div class="property-value">${this.escapeHtml(String(edgeData[key]))}</div>
                    </div>
                `;
            }
        });
        
        content.innerHTML = html;
        panel.classList.add('active');
    }

    closePropertiesPanel() {
        const panel = document.getElementById('propertiesPanel');
        const content = document.getElementById('propertiesContent');
        
        panel.classList.remove('active');
        content.innerHTML = '<p class="no-selection">Click on a node or edge to view properties</p>';
        
        this.clearSelection();
    }

    clearSelection() {
        if (this.selectedElement) {
            d3.select(this.selectedElement).classed('selected', false);
            this.selectedElement = null;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new KnowledgeGraphApp();
});