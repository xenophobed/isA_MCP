// Unified Management Platform - JavaScript Application
// Integrates Agent (8080), MCP (8081), and Model (8082) services

class UnifiedPlatform {
    constructor() {
        this.services = {
            agent: { 
                port: 8080, 
                baseUrl: 'http://localhost:8080',
                status: 'checking',
                pages: ['agents', 'workflows', 'tracing', 'agent-playground']
            },
            mcp: { 
                port: 8081, 
                baseUrl: 'http://localhost:8081',
                status: 'checking',
                pages: ['tools', 'prompts', 'resources', 'playground']
            },
            model: { 
                port: 8082, 
                baseUrl: 'http://localhost:8082',
                status: 'checking',
                pages: ['models', 'training', 'deployments', 'evaluation', 'model-playground']
            }
        };
        
        this.currentPage = 'dashboard';
        this.currentService = null;
        this.data = {
            tools: [],
            prompts: [],
            resources: [],
            agents: [],
            models: [],
            deployments: []
        };
        this.charts = {};
        
        // Service check configuration
        this.serviceCheckInterval = 10000; // 10 seconds
        this.serviceCheckTimer = null;
        
        console.log('Unified Platform initialized');
        this.init();
    }

    async init() {
        this.showLoadingProgress('Initializing platform...', 10);
        
        // Initialize modules
        this.initializeModules();
        this.showLoadingProgress('Modules initialized', 20);
        
        // Check all services
        await this.checkAllServices();
        this.showLoadingProgress('Services checked', 40);
        
        // Setup navigation and UI
        this.setupNavigation();
        this.setupThemeToggle();
        this.setupSearch();
        this.showLoadingProgress('UI components ready', 60);
        
        // Load initial data for available services
        await this.loadInitialData();
        this.showLoadingProgress('Data loaded', 80);
        
        // Start periodic service checking
        this.startServiceChecking();
        this.showLoadingProgress('Service monitoring started', 90);
        
        // Load initial dashboard page
        await this.navigateToPage('dashboard');
        this.showLoadingProgress('Dashboard loaded', 100);
        
        // Hide loading screen
        setTimeout(() => {
            document.getElementById('page-loading').style.display = 'none';
        }, 500);
    }

    // =================== SERVICE MANAGEMENT ===================
    async checkAllServices() {
        const checkPromises = Object.keys(this.services).map(service => 
            this.checkServiceHealth(service)
        );
        
        await Promise.allSettled(checkPromises);
        this.updateServiceUI();
    }

    async checkServiceHealth(serviceName) {
        const service = this.services[serviceName];
        const indicator = document.getElementById(`${serviceName}-indicator`);
        const navIndicator = document.getElementById(`${serviceName}-nav-indicator`);
        
        try {
            // Try to fetch from service health endpoint
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            
            const response = await fetch(`${service.baseUrl}/health`, {
                method: 'GET',
                signal: controller.signal,
                mode: 'cors'
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                service.status = 'online';
                indicator.className = 'status-indicator online';
                if (navIndicator) navIndicator.className = 'service-indicator online';
                console.log(`${serviceName} service is online`);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            service.status = 'offline';
            indicator.className = 'status-indicator offline';
            if (navIndicator) navIndicator.className = 'service-indicator offline';
            console.warn(`${serviceName} service is offline:`, error.message);
        }
        
        this.updateNavigationVisibility(serviceName);
    }

    updateNavigationVisibility(serviceName) {
        const section = document.getElementById(`${serviceName}-section`);
        const service = this.services[serviceName];
        
        if (section) {
            if (service.status === 'online') {
                section.style.display = 'block';
                section.classList.remove('service-offline');
            } else {
                section.style.opacity = '0.5';
                section.classList.add('service-offline');
                // Don't hide, just dim it
            }
        }
    }

    updateServiceUI() {
        // Update service status in the status bar
        Object.keys(this.services).forEach(serviceName => {
            const statusElement = document.getElementById(`${serviceName}-status`);
            const service = this.services[serviceName];
            
            if (statusElement) {
                statusElement.classList.remove('online', 'offline', 'checking');
                statusElement.classList.add(service.status);
                statusElement.title = `${serviceName.toUpperCase()} Service: ${service.status}`;
            }
        });
    }

    startServiceChecking() {
        if (this.serviceCheckTimer) {
            clearInterval(this.serviceCheckTimer);
        }
        
        this.serviceCheckTimer = setInterval(() => {
            this.checkAllServices();
        }, this.serviceCheckInterval);
    }

    // =================== API METHODS ===================
    async makeServiceRequest(serviceName, endpoint, options = {}) {
        const service = this.services[serviceName];
        
        if (!service || service.status !== 'online') {
            throw new Error(`${serviceName} service is not available`);
        }
        
        const url = `${service.baseUrl}${endpoint}`;
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };
        
        try {
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`Error making request to ${serviceName}:`, error);
            throw error;
        }
    }

    // =================== DATA LOADING ===================
    async loadInitialData() {
        const loadPromises = [];
        
        // Load MCP data if service is online
        if (this.services.mcp.status === 'online') {
            loadPromises.push(this.loadMCPData());
        }
        
        // Load Agent data if service is online
        if (this.services.agent.status === 'online') {
            loadPromises.push(this.loadAgentData());
        }
        
        // Load Model data if service is online
        if (this.services.model.status === 'online') {
            loadPromises.push(this.loadModelData());
        }
        
        await Promise.allSettled(loadPromises);
        this.updateNavigationCounts();
    }

    async loadMCPData() {
        try {
            const [tools, prompts, resources] = await Promise.allSettled([
                this.makeServiceRequest('mcp', '/api/tools'),
                this.makeServiceRequest('mcp', '/api/prompts'),
                this.makeServiceRequest('mcp', '/api/resources')
            ]);
            
            if (tools.status === 'fulfilled') this.data.tools = tools.value;
            if (prompts.status === 'fulfilled') this.data.prompts = prompts.value;
            if (resources.status === 'fulfilled') this.data.resources = resources.value;
            
            console.log('MCP data loaded successfully');
        } catch (error) {
            console.error('Failed to load MCP data:', error);
        }
    }

    async loadAgentData() {
        try {
            const agents = await this.makeServiceRequest('agent', '/api/agents');
            this.data.agents = agents;
            console.log('Agent data loaded successfully');
        } catch (error) {
            console.error('Failed to load Agent data:', error);
        }
    }

    async loadModelData() {
        try {
            const [models, deployments] = await Promise.allSettled([
                this.makeServiceRequest('model', '/api/models'),
                this.makeServiceRequest('model', '/api/deployments')
            ]);
            
            if (models.status === 'fulfilled') this.data.models = models.value;
            if (deployments.status === 'fulfilled') this.data.deployments = deployments.value;
            
            console.log('Model data loaded successfully');
        } catch (error) {
            console.error('Failed to load Model data:', error);
        }
    }

    updateNavigationCounts() {
        // Update navigation badges with counts
        const countElements = {
            'tools-count': this.data.tools.length,
            'prompts-count': this.data.prompts.length,
            'resources-count': this.data.resources.length,
            'agents-count': this.data.agents.length,
            'models-count': this.data.models.length,
            'deployments-count': this.data.deployments ? this.data.deployments.length : 0
        };
        
        Object.entries(countElements).forEach(([id, count]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = count;
                element.style.display = count > 0 ? 'inline' : 'none';
            }
        });
    }

    // =================== NAVIGATION ===================
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                const service = link.getAttribute('data-service');
                this.navigateToPage(page, service);
            });
        });
    }

    async navigateToPage(page, service = null) {
        // Check if service is required and available
        if (service && this.services[service].status !== 'online') {
            this.showServiceUnavailableMessage(service, page);
            return;
        }
        
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        const targetLink = service 
            ? document.querySelector(`[data-page="${page}"][data-service="${service}"]`)
            : document.querySelector(`[data-page="${page}"]:not([data-service])`);
            
        if (targetLink) {
            targetLink.classList.add('active');
        }

        // Update breadcrumb and service tag
        document.getElementById('current-page').textContent = this.capitalizeFirst(page);
        const serviceTag = document.getElementById('current-service-tag');
        
        if (service) {
            serviceTag.textContent = service.toUpperCase();
            serviceTag.style.display = 'inline';
            serviceTag.className = `service-tag ${service}`;
        } else {
            serviceTag.style.display = 'none';
        }

        // Store current context
        this.currentPage = page;
        this.currentService = service;

        // Load page content
        await this.loadPageContent(page, service);
    }

    async loadPageContent(page, service) {
        const contentContainer = document.getElementById('current-page-content');
        
        try {
            let content = '';
            
            switch (page) {
                case 'dashboard':
                    content = await this.generateDashboardContent();
                    break;
                case 'tools':
                    content = await this.generateToolsContent();
                    break;
                case 'prompts':
                    content = await this.generatePromptsContent();
                    break;
                case 'resources':
                    content = await this.generateResourcesContent();
                    break;
                case 'agents':
                    content = await this.generateAgentsContent();
                    break;
                case 'models':
                    content = await this.generateModelsContent();
                    break;
                case 'deployments':
                    content = await this.generateDeploymentsContent();
                    break;
                case 'monitoring':
                    content = await this.generateMonitoringContent();
                    break;
                case 'logs':
                    content = await this.generateLogsContent();
                    break;
                case 'analytics':
                    content = await this.generateAnalyticsContent();
                    break;
                default:
                    content = this.generatePlaceholderContent(page, service);
            }
            
            contentContainer.innerHTML = content;
            
            // Re-initialize icons for new content
            if (window.lucide) {
                lucide.createIcons();
            }
            
            // Initialize any charts if needed
            this.initializePageCharts(page);
            
        } catch (error) {
            console.error(`Failed to load ${page} content:`, error);
            contentContainer.innerHTML = this.generateErrorContent(page, error.message);
        }
    }

    // =================== CONTENT GENERATORS ===================
    async generateDashboardContent() {
        const onlineServices = Object.entries(this.services)
            .filter(([_, service]) => service.status === 'online')
            .map(([name, _]) => name);
            
        return `
            <div class="dashboard-container">
                <div class="dashboard-header">
                    <h1>Unified Platform Dashboard</h1>
                    <p>Managing ${onlineServices.length} of ${Object.keys(this.services).length} services</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="server"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${onlineServices.length}</div>
                            <div class="stat-label">Services Online</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="wrench"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.data.tools.length}</div>
                            <div class="stat-label">MCP Tools</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="bot"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.data.agents.length}</div>
                            <div class="stat-label">Active Agents</div>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i data-lucide="brain"></i>
                        </div>
                        <div class="stat-content">
                            <div class="stat-number">${this.data.models.length}</div>
                            <div class="stat-label">AI Models</div>
                        </div>
                    </div>
                </div>
                
                <div class="dashboard-grid">
                    <div class="dashboard-section">
                        <h2>Service Status</h2>
                        <div class="service-cards">
                            ${Object.entries(this.services).map(([name, service]) => `
                                <div class="service-card ${service.status}">
                                    <div class="service-card-header">
                                        <h3>${name.toUpperCase()}</h3>
                                        <div class="status-indicator ${service.status}">
                                            <span class="status-dot"></span>
                                            <span>${service.status}</span>
                                        </div>
                                    </div>
                                    <div class="service-card-content">
                                        <p>Port: ${service.port}</p>
                                        <p>URL: ${service.baseUrl}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="dashboard-section">
                        <h2>Quick Actions</h2>
                        <div class="quick-actions">
                            <button class="btn btn-primary" onclick="platform.refreshAllData()">
                                <i data-lucide="refresh-cw"></i>
                                Refresh All Data
                            </button>
                            <button class="btn btn-secondary" onclick="platform.checkAllServices()">
                                <i data-lucide="activity"></i>
                                Check Services
                            </button>
                            <button class="btn btn-secondary" onclick="platform.navigateToPage('analytics')">
                                <i data-lucide="trending-up"></i>
                                View Analytics
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    generateToolsContent() {
        if (this.services.mcp.status !== 'online') {
            return this.generateServiceUnavailableContent('mcp', 'Tools');
        }
        
        return `
            <div class="tools-container">
                <div class="page-header">
                    <h1>MCP Tools</h1>
                    <p>Available tools from MCP service</p>
                    <div class="page-actions">
                        <button class="btn btn-primary" onclick="platform.refreshMCPData()">
                            <i data-lucide="refresh-cw"></i>
                            Refresh Tools
                        </button>
                    </div>
                </div>
                
                <div class="tools-grid">
                    ${this.data.tools.map(tool => `
                        <div class="tool-card">
                            <div class="tool-header">
                                <h3>${tool.name}</h3>
                                <span class="tool-type">${tool.type || 'Function'}</span>
                            </div>
                            <div class="tool-content">
                                <p>${tool.description || 'No description available'}</p>
                                ${tool.parameters ? `
                                    <div class="tool-parameters">
                                        <strong>Parameters:</strong>
                                        <ul>
                                            ${Object.keys(tool.parameters).map(param => 
                                                `<li>${param}</li>`
                                            ).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    generateServiceUnavailableContent(service, pageName) {
        return `
            <div class="service-unavailable">
                <div class="unavailable-icon">
                    <i data-lucide="wifi-off"></i>
                </div>
                <h2>${pageName} Unavailable</h2>
                <p>The ${service.toUpperCase()} service is currently offline.</p>
                <div class="unavailable-actions">
                    <button class="btn btn-primary" onclick="platform.checkServiceHealth('${service}')">
                        <i data-lucide="refresh-cw"></i>
                        Check Service
                    </button>
                    <button class="btn btn-secondary" onclick="platform.navigateToPage('dashboard')">
                        <i data-lucide="home"></i>
                        Back to Dashboard
                    </button>
                </div>
            </div>
        `;
    }

    generatePlaceholderContent(page, service) {
        return `
            <div class="placeholder-content">
                <div class="placeholder-icon">
                    <i data-lucide="construction"></i>
                </div>
                <h2>${this.capitalizeFirst(page)} ${service ? `(${service.toUpperCase()})` : ''}</h2>
                <p>This page is under construction. Content will be loaded from the ${service || 'unified'} service.</p>
                <div class="placeholder-actions">
                    <button class="btn btn-primary" onclick="platform.navigateToPage('dashboard')">
                        <i data-lucide="home"></i>
                        Back to Dashboard  
                    </button>
                </div>
            </div>
        `;
    }

    // =================== UTILITY METHODS ===================
    showLoadingProgress(text, percentage) {
        const progressFill = document.getElementById('loading-progress');
        const progressText = document.getElementById('loading-progress-text');
        
        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
        
        if (progressText) {
            progressText.textContent = text;
        }
    }

    showServiceUnavailableMessage(service, page) {
        const contentContainer = document.getElementById('current-page-content');
        contentContainer.innerHTML = this.generateServiceUnavailableContent(service, page);
        
        if (window.lucide) {
            lucide.createIcons();
        }
        
        // Auto-hide after a few seconds and return to dashboard
        setTimeout(() => {
            this.navigateToPage('dashboard');
        }, 3000);
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    initializeModules() {
        // Setup theme toggle
        this.setupThemeToggle();
        
        // Setup refresh button
        const refreshButton = document.getElementById('refresh-all');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                this.refreshAllData();
            });
        }
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                document.body.classList.toggle('dark-theme');
                const icon = themeToggle.querySelector('i');
                if (document.body.classList.contains('dark-theme')) {
                    icon.setAttribute('data-lucide', 'moon');
                } else {
                    icon.setAttribute('data-lucide', 'sun');
                }
                lucide.createIcons();
            });
        }
    }

    setupSearch() {
        const searchInput = document.getElementById('global-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.performGlobalSearch(e.target.value);
            });
        }
    }

    performGlobalSearch(query) {
        if (!query.trim()) return;
        
        console.log('Global search:', query);
        // Implement cross-service search logic here
    }

    async refreshAllData() {
        const refreshButton = document.getElementById('refresh-all');
        if (refreshButton) {
            refreshButton.disabled = true;
            refreshButton.innerHTML = '<i data-lucide="loader-2"></i> Refreshing...';
        }
        
        try {
            await this.checkAllServices();
            await this.loadInitialData();
            
            // Reload current page if it has data dependencies
            if (this.currentPage !== 'dashboard') {
                await this.loadPageContent(this.currentPage, this.currentService);
            } else {
                await this.loadPageContent('dashboard');
            }
            
            console.log('All data refreshed successfully');
        } catch (error) {
            console.error('Failed to refresh data:', error);
        } finally {
            if (refreshButton) {
                refreshButton.disabled = false;
                refreshButton.innerHTML = '<i data-lucide="refresh-cw"></i> Refresh All';
            }
            
            if (window.lucide) {
                lucide.createIcons();
            }
        }
    }

    initializePageCharts(page) {
        // Initialize charts based on page type
        // This would be expanded based on specific chart needs
    }

    generateErrorContent(page, error) {
        return `
            <div class="error-container">
                <div class="error-icon">
                    <i data-lucide="alert-triangle"></i>
                </div>
                <h2>Error Loading ${this.capitalizeFirst(page)}</h2>
                <p>Failed to load page content: ${error}</p>
                <div class="error-actions">
                    <button class="btn btn-primary" onclick="platform.loadPageContent('${page}', ${this.currentService ? `'${this.currentService}'` : 'null'})">
                        <i data-lucide="refresh-cw"></i>
                        Retry
                    </button>
                    <button class="btn btn-secondary" onclick="platform.navigateToPage('dashboard')">
                        <i data-lucide="home"></i>
                        Back to Dashboard
                    </button>
                </div>
            </div>
        `;
    }

    // Cleanup method
    destroy() {
        if (this.serviceCheckTimer) {
            clearInterval(this.serviceCheckTimer);
        }
    }
}

// Initialize the platform when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.platform = new UnifiedPlatform();
});

// Handle page unload cleanup
window.addEventListener('beforeunload', () => {
    if (window.platform) {
        window.platform.destroy();
    }
});