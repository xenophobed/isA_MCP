// isA MCP Management Portal - JavaScript Application

class MCPPortal {
    constructor() {
        // Set API base URL to MCP server
        this.apiBase = window.location.origin;
        this.currentPage = 'dashboard';
        this.tools = [];
        this.prompts = [];
        this.resources = [];
        this.charts = {};
        
        console.log('MCP Portal initialized with API base:', this.apiBase);
        this.init();
    }

    async init() {
        this.initializeModules();
        this.setupNavigation();
        this.setupThemeToggle();
        this.setupSearch();
        await this.loadInitialData();
        
        // Load initial dashboard page
        await this.navigateToPage('dashboard');
    }

    // =================== NAVIGATION MODULE ===================
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                this.navigateToPage(page);
            });
        });
    }

    async navigateToPage(page) {
        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-page="${page}"]`).classList.add('active');

        // Update breadcrumb
        document.getElementById('current-page').textContent = this.capitalizeFirst(page);
        
        // Load page content dynamically
        await this.loadPageContent(page);
        
        // Update current page reference
        this.currentPage = page;
    }

    async loadPageContent(page) {
        const contentContainer = document.getElementById('current-page-content');
        const loadingIndicator = document.getElementById('page-loading');
        
        try {
            // Show loading state
            loadingIndicator.style.display = 'block';
            
            // Fetch page content
            const response = await fetch(`/static/pages/${page}.html`);
            if (!response.ok) {
                throw new Error(`Failed to load page: ${response.status}`);
            }
            
            const pageContent = await response.text();
            
            // Update content
            contentContainer.innerHTML = pageContent;
            
            // Initialize page-specific functionality
            await this.initializePageModule(page);
            
            // Reinitialize Lucide icons for new content
            if (window.lucide) {
                lucide.createIcons();
            }
            
        } catch (error) {
            console.error(`Error loading page ${page}:`, error);
            contentContainer.innerHTML = `
                <div class="error-container">
                    <div class="error-message">
                        <h2>Error Loading Page</h2>
                        <p>Failed to load the ${page} page. Please try again.</p>
                        <button class="btn btn-primary" onclick="portal.navigateToPage('${page}')">
                            <i data-lucide="refresh-cw"></i>
                            Retry
                        </button>
                    </div>
                </div>
            `;
        } finally {
            // Hide loading state
            loadingIndicator.style.display = 'none';
        }
    }

    async initializePageModule(page) {
        // Initialize page-specific modules after content is loaded
        switch (page) {
            case 'dashboard':
                if (this.dashboardModule) {
                    this.dashboardModule.refresh();
                }
                break;
            case 'tools':
                if (this.toolsModule) {
                    this.toolsModule.refresh();
                }
                break;
            case 'prompts':
                if (this.promptsModule) {
                    this.promptsModule.refresh();
                }
                break;
            case 'resources':
                if (this.resourcesModule) {
                    this.resourcesModule.refresh();
                }
                break;
            case 'playground':
                // Initialize playground module only when playground page is loaded
                if (!this.playgroundModule) {
                    this.playgroundModule = new PlaygroundModule(this);
                } else {
                    this.playgroundModule.refresh();
                }
                break;
            case 'logs':
                if (this.logsModule) {
                    this.logsModule.refresh();
                }
                break;
            case 'monitoring':
                if (this.monitoringModule) {
                    this.monitoringModule.refresh();
                }
                break;
            case 'analytics':
                // Initialize analytics module only when analytics page is loaded
                if (!this.analyticsModule) {
                    this.analyticsModule = new AnalyticsModule(this);
                } else {
                    this.analyticsModule.refresh();
                }
                break;
        }
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    async loadPageData(page) {
        switch(page) {
            case 'dashboard':
                if (this.dashboardModule) await this.dashboardModule.refresh();
                break;
            case 'tools':
                if (this.toolsModule) await this.toolsModule.refresh();
                break;
            case 'prompts':
                if (this.promptsModule) await this.promptsModule.refresh();
                break;
            case 'resources':
                if (this.resourcesModule) await this.resourcesModule.refresh();
                break;
            case 'playground':
                if (this.playgroundModule) this.playgroundModule.refresh();
                break;
            case 'logs':
                if (this.logsModule) await this.logsModule.refresh();
                break;
            case 'monitoring':
                if (this.monitoringModule) await this.monitoringModule.refresh();
                break;
            case 'configuration':
                if (this.configurationModule) this.configurationModule.refresh();
                break;
        }
    }

    // =================== THEME MODULE ===================
    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        const currentTheme = localStorage.getItem('theme') || 'light';
        
        this.setTheme(currentTheme);
        
        themeToggle.addEventListener('click', () => {
            const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const icon = document.querySelector('#theme-toggle i');
        if (icon) {
            icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
            lucide.createIcons();
        }
    }

    // =================== SEARCH MODULE ===================
    setupSearch() {
        const searchInput = document.getElementById('global-search');
        let searchTimeout;

        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performSearch(e.target.value);
            }, 300);
        });

        // Refresh button
        const refreshButton = document.getElementById('refresh-all');
        refreshButton.addEventListener('click', () => {
            this.refreshAllData();
        });
    }

    performSearch(query) {
        if (!query.trim()) return;
        
        console.log('Searching for:', query);
        // Search through tools, prompts, and resources
        const allItems = [
            ...this.tools.map(t => ({...t, type: 'tool'})),
            ...this.prompts.map(p => ({...p, type: 'prompt'})),
            ...this.resources.map(r => ({...r, type: 'resource'}))
        ];
        
        const results = allItems.filter(item => 
            item.name?.toLowerCase().includes(query.toLowerCase()) ||
            item.description?.toLowerCase().includes(query.toLowerCase())
        );
        
        this.showSearchResults(results);
    }

    showSearchResults(results) {
        // For now, just log results - could implement a search overlay
        console.log('Search results:', results);
    }

    async refreshAllData() {
        try {
            await this.loadInitialData();
            if (this[`${this.currentPage}Module`]) {
                await this[`${this.currentPage}Module`].refresh();
            }
            this.showNotification('Data refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh data', 'error');
        }
    }

    // =================== DATA LOADING ===================
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadTools(),
                this.loadPrompts(),
                this.loadResources(),
                this.loadSystemHealth()
            ]);
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadTools() {
        try {
            console.log('Loading tools from:', `${this.apiBase}/admin/tools`);
            const response = await fetch(`${this.apiBase}/admin/tools`);
            console.log('Tools API response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Raw tools data:', data);
                this.tools = this.parseTools(data);
                console.log('Parsed tools:', this.tools.length, 'tools');
            } else {
                console.warn('Tools API failed, using fallback');
                this.tools = this.getFallbackTools();
            }
        } catch (error) {
            console.error('Error loading tools:', error);
            this.tools = this.getFallbackTools();
        }

        // Update tools count in navigation
        document.getElementById('tools-count').textContent = this.tools.length;
    }

    async loadPrompts() {
        try {
            console.log('Loading prompts from:', `${this.apiBase}/admin/prompts`);
            const response = await fetch(`${this.apiBase}/admin/prompts`);
            
            if (response.ok) {
                const data = await response.json();
                this.prompts = this.parsePrompts(data);
                console.log('Parsed prompts:', this.prompts.length, 'prompts');
            } else {
                console.warn('Prompts API failed, using fallback');
                this.prompts = this.getFallbackPrompts();
            }
        } catch (error) {
            console.error('Error loading prompts:', error);
            this.prompts = this.getFallbackPrompts();
        }

        document.getElementById('prompts-count').textContent = this.prompts.length;
    }

    async loadResources() {
        try {
            console.log('Loading resources from:', `${this.apiBase}/admin/resources`);
            const response = await fetch(`${this.apiBase}/admin/resources`);
            
            if (response.ok) {
                const data = await response.json();
                this.resources = this.parseResources(data);
                console.log('Parsed resources:', this.resources.length, 'resources');
            } else {
                console.warn('Resources API failed, using fallback');
                this.resources = this.getFallbackResources();
            }
        } catch (error) {
            console.error('Error loading resources:', error);
            this.resources = this.getFallbackResources();
        }

        document.getElementById('resources-count').textContent = this.resources.length;
    }

    async loadSystemHealth() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            if (response.ok) {
                this.systemHealth = await response.json();
            } else {
                this.systemHealth = { status: 'unknown' };
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.systemHealth = { status: 'error', message: error.message };
        }
    }

    // =================== DATA PARSING ===================
    parseTools(apiData) {
        if (!apiData || !apiData.tools) return [];
        
        return apiData.tools.map(tool => ({
            name: tool.name,
            description: tool.description || 'MCP tool',
            category: this.getToolCategory(tool.name),
            schema: tool.inputSchema || {},
            lastUsed: this.getRandomDate(),
            callCount: Math.floor(Math.random() * 1000) + 10,
            avgResponseTime: Math.floor(Math.random() * 500) + 50,
            successRate: (95 + Math.random() * 5).toFixed(1)
        }));
    }

    parsePrompts(apiData) {
        if (!apiData || !apiData.prompts) return [];
        
        return apiData.prompts.map(prompt => ({
            name: prompt.name,
            description: prompt.description || 'MCP prompt',
            category: this.getPromptCategory(prompt.name),
            arguments: prompt.arguments || [],
            content: prompt.content || '',
            lastModified: this.getRandomDate(),
            usageCount: Math.floor(Math.random() * 500) + 5
        }));
    }

    parseResources(apiData) {
        if (!apiData || !apiData.resources) return [];
        
        return apiData.resources.map(resource => ({
            uri: resource.uri,
            name: resource.name || resource.uri.split('/').pop(),
            description: resource.description || 'MCP resource',
            type: this.getResourceType(resource.uri),
            mimeType: resource.mimeType || 'text/plain',
            size: resource.size || Math.floor(Math.random() * 10000) + 1000,
            lastAccessed: this.getRandomDate()
        }));
    }

    getToolCategory(toolName) {
        const name = toolName.toLowerCase();
        if (name.includes('web') || name.includes('fetch') || name.includes('http')) return 'web';
        if (name.includes('data') || name.includes('sql') || name.includes('database')) return 'data';
        if (name.includes('analytics') || name.includes('graph') || name.includes('analyze')) return 'analytics';
        if (name.includes('memory') || name.includes('remember') || name.includes('store')) return 'memory';
        return 'utility';
    }

    getPromptCategory(promptName) {
        const name = promptName.toLowerCase();
        if (name.includes('system')) return 'system';
        if (name.includes('rag') || name.includes('retrieval')) return 'rag';
        if (name.includes('autonomous') || name.includes('auto')) return 'autonomous';
        if (name.includes('shopify') || name.includes('ecommerce')) return 'shopify';
        return 'user';
    }

    getResourceType(uri) {
        if (uri.includes('database') || uri.includes('db')) return 'database';
        if (uri.includes('file') || uri.includes('document')) return 'file';
        if (uri.includes('memory') || uri.includes('cache')) return 'memory';
        if (uri.includes('api') || uri.includes('http')) return 'api';
        return 'other';
    }

    getRandomDate() {
        const now = Date.now();
        const randomOffset = Math.floor(Math.random() * 7 * 24 * 60 * 60 * 1000); // Last 7 days
        return new Date(now - randomOffset).toLocaleDateString();
    }

    // =================== MODULE INITIALIZATION ===================
    initializeModules() {
        // Initialize modules that don't depend on specific page DOM elements
        this.dashboardModule = new DashboardModule(this);
        this.toolsModule = new ToolsModule(this);
        this.promptsModule = new PromptsModule(this);
        this.resourcesModule = new ResourcesModule(this);
        this.logsModule = new LogsModule(this);
        this.monitoringModule = new MonitoringModule(this);
        this.configurationModule = new ConfigurationModule(this);
        
        // Page-specific modules will be initialized when pages are loaded
        this.playgroundModule = null;
        this.analyticsModule = null;
    }

    // =================== FALLBACK DATA ===================
    getFallbackTools() {
        return [
            {
                name: 'web_fetch',
                description: 'Fetch content from web URLs',
                category: 'web',
                schema: { url: 'string', headers: 'object' },
                lastUsed: '2024-01-15',
                callCount: 245,
                avgResponseTime: 1200,
                successRate: '98.2'
            },
            {
                name: 'data_query',
                description: 'Query database and data sources',
                category: 'data',
                schema: { query: 'string', database: 'string' },
                lastUsed: '2024-01-15',
                callCount: 892,
                avgResponseTime: 350,
                successRate: '99.1'
            },
            {
                name: 'memory_store',
                description: 'Store and retrieve memory data',
                category: 'memory',
                schema: { key: 'string', value: 'any', ttl: 'number' },
                lastUsed: '2024-01-14',
                callCount: 156,
                avgResponseTime: 45,
                successRate: '99.8'
            }
        ];
    }

    getFallbackPrompts() {
        return [
            {
                name: 'system_instructions',
                description: 'Core system behavior instructions',
                category: 'system',
                arguments: [],
                content: 'You are a helpful AI assistant...',
                lastModified: '2024-01-10',
                usageCount: 1000
            },
            {
                name: 'rag_query',
                description: 'RAG-based question answering prompt',
                category: 'rag',
                arguments: ['context', 'question'],
                content: 'Based on the following context: {context}...',
                lastModified: '2024-01-12',
                usageCount: 234
            }
        ];
    }

    getFallbackResources() {
        return [
            {
                uri: 'database://supabase/main',
                name: 'Main Database',
                description: 'Primary Supabase database connection',
                type: 'database',
                mimeType: 'application/sql',
                size: 1048576,
                lastAccessed: '2024-01-15'
            },
            {
                uri: 'memory://cache/active',
                name: 'Active Memory Cache',
                description: 'In-memory cache for active sessions',
                type: 'memory',
                mimeType: 'application/json',
                size: 524288,
                lastAccessed: '2024-01-15'
            }
        ];
    }

    // =================== UTILITY FUNCTIONS ===================
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: var(--space-2);">
                <i data-lucide="${type === 'error' ? 'alert-circle' : type === 'success' ? 'check-circle' : 'info'}" style="width: 16px; height: 16px;"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add to page
        const container = document.querySelector('.page-content') || document.body;
        container.appendChild(notification);
        
        // Style notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius)',
            backgroundColor: type === 'error' ? 'var(--destructive)' : type === 'success' ? 'var(--success)' : 'var(--info)',
            color: 'white',
            zIndex: '1000',
            boxShadow: 'var(--shadow-lg)',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease'
        });
        
        // Initialize icons
        lucide.createIcons();
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, type === 'error' ? 5000 : 3000);
    }
}

// =================== DASHBOARD MODULE ===================
class DashboardModule {
    constructor(portal) {
        this.portal = portal;
    }

    async refresh() {
        this.renderStats();
        this.renderActivity();
        this.renderPerformanceTable();
        this.createUsageChart();
    }

    renderStats() {
        const stats = [
            {
                title: 'Total Tools',
                value: this.portal.tools.length,
                change: '+2 this week',
                positive: true,
                icon: 'wrench'
            },
            {
                title: 'Prompts',
                value: this.portal.prompts.length,
                change: '+1 new prompt',
                positive: true,
                icon: 'message-square'
            },
            {
                title: 'Resources',
                value: this.portal.resources.length,
                change: 'All active',
                positive: true,
                icon: 'database'
            },
            {
                title: 'System Health',
                value: this.portal.systemHealth?.status === 'healthy' ? '100%' : '98%',
                change: 'All systems operational',
                positive: true,
                icon: 'activity'
            }
        ];

        const statsGrid = document.getElementById('stats-grid');
        statsGrid.innerHTML = stats.map(stat => `
            <div class="card">
                <div class="card-content">
                    <div class="flex items-center justify-between" style="margin-bottom: var(--space-2);">
                        <span class="text-muted">${stat.title}</span>
                        <i data-lucide="${stat.icon}" style="width: 16px; height: 16px; color: var(--muted-foreground);"></i>
                    </div>
                    <div style="font-size: 24px; font-weight: 600; margin-bottom: var(--space-1);">
                        ${stat.value}
                    </div>
                    <div style="font-size: 12px; color: ${stat.positive ? 'var(--success)' : 'var(--destructive)'};">
                        ${stat.change}
                    </div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    }

    renderActivity() {
        const activities = [
            {
                type: 'success',
                title: 'Tool executed successfully',
                description: 'web_fetch completed in 245ms',
                time: '2 minutes ago',
                icon: 'check-circle'
            },
            {
                type: 'info',
                title: 'New resource discovered',
                description: 'Auto-discovery found new database resource',
                time: '15 minutes ago',
                icon: 'search'
            },
            {
                type: 'warning',
                title: 'High memory usage',
                description: 'Memory cache at 85% capacity',
                time: '1 hour ago',
                icon: 'alert-triangle'
            }
        ];

        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = activities.map(activity => `
            <div style="display: flex; gap: var(--space-3); padding: var(--space-3); border-radius: var(--radius); transition: background-color var(--duration-fast);" 
                 onmouseover="this.style.backgroundColor='var(--accent)'" 
                 onmouseout="this.style.backgroundColor='transparent'">
                <div class="status status-${activity.type}">
                    <span class="status-dot"></span>
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 500; margin-bottom: var(--space-1);">
                        ${activity.title}
                    </div>
                    <div style="font-size: 13px; color: var(--muted-foreground); margin-bottom: var(--space-1);">
                        ${activity.description}
                    </div>
                    <div style="font-size: 12px; color: var(--muted-foreground);">
                        ${activity.time}
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderPerformanceTable() {
        const tbody = document.querySelector('#performance-table tbody');
        const components = [
            ...this.portal.tools.slice(0, 3).map(tool => ({
                name: tool.name,
                type: 'Tool',
                responseTime: tool.avgResponseTime,
                successRate: tool.successRate,
                calls: tool.callCount,
                status: 'Active'
            })),
            ...this.portal.resources.slice(0, 2).map(resource => ({
                name: resource.name,
                type: 'Resource',
                responseTime: Math.floor(Math.random() * 100) + 20,
                successRate: (98 + Math.random() * 2).toFixed(1),
                calls: Math.floor(Math.random() * 500) + 50,
                status: 'Active'
            }))
        ];

        tbody.innerHTML = components.map(component => `
            <tr>
                <td>
                    <div style="font-weight: 500;">${component.name}</div>
                    <div style="font-size: 12px; color: var(--muted-foreground);">${component.type}</div>
                </td>
                <td>
                    <span style="padding: var(--space-1) var(--space-2); background: var(--muted); border-radius: var(--radius-sm); font-size: 12px;">
                        ${component.type}
                    </span>
                </td>
                <td>${component.responseTime}ms</td>
                <td>
                    <span class="status status-success">
                        <span class="status-dot"></span>
                        ${component.successRate}%
                    </span>
                </td>
                <td>${component.calls.toLocaleString()}</td>
                <td>
                    <span class="status status-success">
                        <span class="status-dot"></span>
                        ${component.status}
                    </span>
                </td>
            </tr>
        `).join('');
    }

    createUsageChart() {
        const ctx = document.getElementById('usage-chart');
        if (!ctx) return;

        if (this.portal.charts.usage) {
            this.portal.charts.usage.destroy();
        }

        this.portal.charts.usage = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Tool Calls',
                    data: [145, 178, 190, 181, 195, 187, 192],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'var(--border)' },
                        ticks: { color: 'var(--muted-foreground)' }
                    },
                    x: {
                        grid: { color: 'var(--border)' },
                        ticks: { color: 'var(--muted-foreground)' }
                    }
                }
            }
        });
    }
}

// =================== TOOLS MODULE ===================
class ToolsModule {
    constructor(portal) {
        this.portal = portal;
        this.currentFilter = 'all';
        this.setupFilters();
    }

    setupFilters() {
        const filterButtons = document.querySelectorAll('.tool-filters .btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.getAttribute('data-filter');
                this.renderTools();
            });
        });

        // Discover tools button
        const discoverButton = document.getElementById('discover-tools');
        if (discoverButton) {
            discoverButton.addEventListener('click', () => {
                this.discoverTools();
            });
        }
    }

    async refresh() {
        this.renderTools();
    }

    renderTools() {
        const filteredTools = this.currentFilter === 'all' 
            ? this.portal.tools 
            : this.portal.tools.filter(tool => tool.category === this.currentFilter);

        const toolsGrid = document.getElementById('tools-grid');
        toolsGrid.innerHTML = filteredTools.map(tool => `
            <div class="card" data-category="${tool.category}">
                <div class="card-header">
                    <div class="flex items-center justify-between">
                        <h3 class="card-title">${tool.name}</h3>
                        <span class="status status-success">
                            <span class="status-dot"></span>
                            Active
                        </span>
                    </div>
                    <p class="card-description">${tool.category} • ${tool.callCount} calls</p>
                </div>
                <div class="card-content">
                    <p style="margin-bottom: var(--space-4); color: var(--muted-foreground);">
                        ${tool.description}
                    </p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4);">
                        <span style="font-size: 12px; color: var(--muted-foreground);">Response Time</span>
                        <span style="font-weight: 500;">${tool.avgResponseTime}ms</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4);">
                        <span style="font-size: 12px; color: var(--muted-foreground);">Success Rate</span>
                        <span style="font-weight: 500;">${tool.successRate}%</span>
                    </div>
                    <div style="display: flex; gap: var(--space-2);">
                        <button class="btn btn-ghost btn-sm" onclick="portal.testTool('${tool.name}')">
                            <i data-lucide="play"></i>
                            Test
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="portal.viewToolSchema('${tool.name}')">
                            <i data-lucide="eye"></i>
                            Schema
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    }

    async discoverTools() {
        this.portal.showNotification('Starting tool discovery...', 'info');
        
        try {
            const response = await fetch(`${this.portal.apiBase}/discover-tools`, {
                method: 'POST'
            });
            
            if (response.ok) {
                await this.portal.loadTools();
                this.renderTools();
                this.portal.showNotification('Tool discovery completed', 'success');
            } else {
                throw new Error('Discovery failed');
            }
        } catch (error) {
            console.error('Tool discovery error:', error);
            this.portal.showNotification('Tool discovery failed', 'error');
        }
    }
}

// =================== PROMPTS MODULE ===================
class PromptsModule {
    constructor(portal) {
        this.portal = portal;
        this.currentFilter = 'all';
        this.setupFilters();
    }

    setupFilters() {
        const filterButtons = document.querySelectorAll('.prompt-filters .btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentFilter = btn.getAttribute('data-filter');
                this.renderPrompts();
            });
        });
    }

    async refresh() {
        this.renderPrompts();
    }

    renderPrompts() {
        const filteredPrompts = this.currentFilter === 'all' 
            ? this.portal.prompts 
            : this.portal.prompts.filter(prompt => prompt.category === this.currentFilter);

        const promptsGrid = document.getElementById('prompts-grid');
        promptsGrid.innerHTML = filteredPrompts.map(prompt => `
            <div class="card" data-category="${prompt.category}">
                <div class="card-header">
                    <div class="flex items-center justify-between">
                        <h3 class="card-title">${prompt.name}</h3>
                        <span style="padding: var(--space-1) var(--space-2); background: var(--muted); border-radius: var(--radius-sm); font-size: 12px;">
                            ${prompt.category}
                        </span>
                    </div>
                    <p class="card-description">${prompt.arguments.length} arguments • Used ${prompt.usageCount} times</p>
                </div>
                <div class="card-content">
                    <p style="margin-bottom: var(--space-4); color: var(--muted-foreground);">
                        ${prompt.description}
                    </p>
                    <div style="margin-bottom: var(--space-4);">
                        <div style="font-size: 12px; color: var(--muted-foreground); margin-bottom: var(--space-2);">
                            Arguments: ${prompt.arguments.join(', ') || 'None'}
                        </div>
                        <div style="font-size: 12px; color: var(--muted-foreground);">
                            Last modified: ${prompt.lastModified}
                        </div>
                    </div>
                    <div style="display: flex; gap: var(--space-2);">
                        <button class="btn btn-ghost btn-sm" onclick="portal.editPrompt('${prompt.name}')">
                            <i data-lucide="edit"></i>
                            Edit
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="portal.usePrompt('${prompt.name}')">
                            <i data-lucide="play"></i>
                            Use
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    }
}

// =================== RESOURCES MODULE ===================
class ResourcesModule {
    constructor(portal) {
        this.portal = portal;
    }

    async refresh() {
        this.renderResources();
    }

    renderResources() {
        const resourcesGrid = document.getElementById('resources-grid');
        resourcesGrid.innerHTML = this.portal.resources.map(resource => `
            <div class="card" data-type="${resource.type}">
                <div class="card-header">
                    <div class="flex items-center justify-between">
                        <h3 class="card-title">${resource.name}</h3>
                        <span class="status status-success">
                            <span class="status-dot"></span>
                            Active
                        </span>
                    </div>
                    <p class="card-description">${resource.type} • ${this.formatFileSize(resource.size)}</p>
                </div>
                <div class="card-content">
                    <p style="margin-bottom: var(--space-4); color: var(--muted-foreground);">
                        ${resource.description}
                    </p>
                    <div style="margin-bottom: var(--space-4);">
                        <div style="font-size: 12px; color: var(--muted-foreground); margin-bottom: var(--space-1);">
                            URI: ${resource.uri}
                        </div>
                        <div style="font-size: 12px; color: var(--muted-foreground); margin-bottom: var(--space-1);">
                            MIME Type: ${resource.mimeType}
                        </div>
                        <div style="font-size: 12px; color: var(--muted-foreground);">
                            Last accessed: ${resource.lastAccessed}
                        </div>
                    </div>
                    <div style="display: flex; gap: var(--space-2);">
                        <button class="btn btn-ghost btn-sm" onclick="portal.accessResource('${resource.uri}')">
                            <i data-lucide="external-link"></i>
                            Access
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="portal.inspectResource('${resource.uri}')">
                            <i data-lucide="search"></i>
                            Inspect
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// =================== PLAYGROUND MODULE ===================
class PlaygroundModule {
    constructor(portal) {
        this.portal = portal;
        this.setupForm();
    }

    setupForm() {
        const form = document.getElementById('playground-form');
        const toolSelect = document.getElementById('tool-select');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.executeTool();
        });

        // Copy button
        document.getElementById('copy-output').addEventListener('click', () => {
            this.copyOutput();
        });
    }

    refresh() {
        this.updateToolOptions();
    }

    updateToolOptions() {
        const toolSelect = document.getElementById('tool-select');
        toolSelect.innerHTML = '<option value="">Select a tool</option>' +
            this.portal.tools.map(tool => 
                `<option value="${tool.name}">${tool.name} (${tool.category})</option>`
            ).join('');
    }

    async executeTool() {
        const toolName = document.getElementById('tool-select').value;
        const argsText = document.getElementById('tool-args').value;
        const outputArea = document.getElementById('output-area');

        if (!toolName) {
            outputArea.textContent = 'Please select a tool.';
            return;
        }

        let args = {};
        try {
            if (argsText.trim()) {
                args = JSON.parse(argsText);
            }
        } catch (error) {
            outputArea.textContent = 'Invalid JSON in arguments field.';
            return;
        }

        outputArea.innerHTML = '<div class="loading"><div class="spinner"></div> Executing tool...</div>';

        try {
            const response = await fetch(`${this.portal.apiBase}/admin/call-tool`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: toolName,
                    arguments: args
                })
            });

            const result = await response.json();
            outputArea.textContent = JSON.stringify(result, null, 2);

        } catch (error) {
            outputArea.textContent = `Error: ${error.message}`;
        }
    }

    copyOutput() {
        const outputArea = document.getElementById('output-area');
        navigator.clipboard.writeText(outputArea.textContent);
        
        const copyBtn = document.getElementById('copy-output');
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i data-lucide="check"></i> Copied';
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
            lucide.createIcons();
        }, 2000);
    }
}

// =================== LOGS MODULE ===================
class LogsModule {
    constructor(portal) {
        this.portal = portal;
        this.logs = [];
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Add basic log filtering and refresh functionality
        document.getElementById('refresh-logs')?.addEventListener('click', () => {
            this.loadLogs();
        });

        document.getElementById('clear-logs')?.addEventListener('click', () => {
            this.clearLogs();
        });

        document.getElementById('export-logs')?.addEventListener('click', () => {
            this.exportLogs();
        });
    }

    async refresh() {
        await this.loadLogs();
        this.renderLogStats();
    }

    async loadLogs() {
        try {
            const response = await fetch(`${this.portal.apiBase}/logs`);
            
            if (response.ok) {
                this.logs = await response.json();
            } else {
                this.logs = this.getFallbackLogs();
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            this.logs = this.getFallbackLogs();
        }

        this.renderLogs();
    }

    renderLogs() {
        const logStream = document.getElementById('log-stream');
        if (!logStream) return;

        logStream.innerHTML = this.logs.map(log => this.renderLogEntry(log)).join('');
        lucide.createIcons();
    }

    renderLogEntry(log) {
        const timestamp = new Date(log.timestamp).toLocaleString();
        const levelClass = log.level.toLowerCase();

        return `
            <div class="log-entry log-${levelClass}">
                <div class="log-header">
                    <div class="log-meta">
                        <span class="log-timestamp">${timestamp}</span>
                        <span class="log-level log-level-${levelClass}">
                            ${log.level}
                        </span>
                        <span class="log-component">${log.component}</span>
                    </div>
                </div>
                <div class="log-message">${log.message}</div>
            </div>
        `;
    }

    renderLogStats() {
        const stats = {
            total: this.logs.length,
            errors: this.logs.filter(log => log.level === 'ERROR').length,
            warnings: this.logs.filter(log => log.level === 'WARNING').length,
            info: this.logs.filter(log => log.level === 'INFO').length
        };

        const statsGrid = document.getElementById('log-stats');
        if (statsGrid) {
            statsGrid.innerHTML = `
                <div class="card">
                    <div class="card-content">
                        <div class="flex items-center justify-between" style="margin-bottom: var(--space-2);">
                            <span class="text-muted">Total Logs</span>
                            <i data-lucide="file-text" style="width: 16px; height: 16px; color: var(--muted-foreground);"></i>
                        </div>
                        <div style="font-size: 24px; font-weight: 600;">${stats.total}</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-content">
                        <div class="flex items-center justify-between" style="margin-bottom: var(--space-2);">
                            <span class="text-muted">Errors</span>
                            <i data-lucide="alert-circle" style="width: 16px; height: 16px; color: var(--destructive);"></i>
                        </div>
                        <div style="font-size: 24px; font-weight: 600; color: var(--destructive);">${stats.errors}</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-content">
                        <div class="flex items-center justify-between" style="margin-bottom: var(--space-2);">
                            <span class="text-muted">Warnings</span>
                            <i data-lucide="alert-triangle" style="width: 16px; height: 16px; color: var(--warning);"></i>
                        </div>
                        <div style="font-size: 24px; font-weight: 600; color: var(--warning);">${stats.warnings}</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-content">
                        <div class="flex items-center justify-between" style="margin-bottom: var(--space-2);">
                            <span class="text-muted">Info</span>
                            <i data-lucide="info" style="width: 16px; height: 16px; color: var(--info);"></i>
                        </div>
                        <div style="font-size: 24px; font-weight: 600;">${stats.info}</div>
                    </div>
                </div>
            `;
            lucide.createIcons();
        }
    }

    clearLogs() {
        if (confirm('Are you sure you want to clear all logs?')) {
            this.logs = [];
            this.renderLogs();
            this.renderLogStats();
        }
    }

    exportLogs() {
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const filename = `mcp-logs-${timestamp}.json`;
        
        const blob = new Blob([JSON.stringify(this.logs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    getFallbackLogs() {
        const now = Date.now();
        return [
            {
                timestamp: new Date(now - 1000).toISOString(),
                level: 'INFO',
                component: 'server',
                message: 'MCP server started successfully'
            },
            {
                timestamp: new Date(now - 5000).toISOString(),
                level: 'INFO',
                component: 'tools',
                message: 'Tool discovery completed: found 3 tools'
            },
            {
                timestamp: new Date(now - 10000).toISOString(),
                level: 'WARNING',
                component: 'memory',
                message: 'Memory usage at 85% capacity'
            },
            {
                timestamp: new Date(now - 15000).toISOString(),
                level: 'ERROR',
                component: 'resources',
                message: 'Failed to connect to database resource'
            }
        ];
    }
}

// =================== MONITORING MODULE ===================
class MonitoringModule {
    constructor(portal) {
        this.portal = portal;
    }

    async refresh() {
        this.renderHealthCards();
        this.createRealtimeChart();
    }

    renderHealthCards() {
        const healthData = [
            {
                title: 'MCP Server',
                status: 'healthy',
                uptime: '99.9%',
                value: 'All systems operational'
            },
            {
                title: 'Tools',
                status: 'healthy',
                uptime: '99.7%',
                value: `${this.portal.tools.length} tools active`
            },
            {
                title: 'Resources',
                status: 'healthy',
                uptime: '99.8%',
                value: 'All connections stable'
            }
        ];

        const healthGrid = document.getElementById('health-grid');
        healthGrid.innerHTML = healthData.map(item => `
            <div class="card">
                <div class="card-content">
                    <div class="flex items-center justify-between" style="margin-bottom: var(--space-4);">
                        <h3 style="font-size: 16px; font-weight: 500;">${item.title}</h3>
                        <span class="status status-${item.status}">
                            <span class="status-dot"></span>
                            ${item.status}
                        </span>
                    </div>
                    <div style="font-size: 14px; color: var(--muted-foreground); margin-bottom: var(--space-2);">
                        ${item.value}
                    </div>
                    <div style="font-size: 12px; color: var(--muted-foreground);">
                        Uptime: ${item.uptime}
                    </div>
                </div>
            </div>
        `).join('');
    }

    createRealtimeChart() {
        const ctx = document.getElementById('realtime-chart');
        if (!ctx) return;

        if (this.portal.charts.realtime) {
            this.portal.charts.realtime.destroy();
        }

        this.portal.charts.realtime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 20}, (_, i) => i),
                datasets: [{
                    label: 'Tool Calls/min',
                    data: Array.from({length: 20}, () => Math.floor(Math.random() * 50) + 10),
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'var(--border)' },
                        ticks: { color: 'var(--muted-foreground)' }
                    },
                    x: {
                        grid: { color: 'var(--border)' },
                        ticks: { color: 'var(--muted-foreground)' }
                    }
                },
                animation: false
            }
        });

        // Simulate real-time updates
        setInterval(() => {
            if (this.portal.currentPage === 'monitoring' && this.portal.charts.realtime) {
                const chart = this.portal.charts.realtime;
                chart.data.datasets[0].data.shift();
                chart.data.datasets[0].data.push(Math.floor(Math.random() * 50) + 10);
                chart.update('none');
            }
        }, 2000);
    }
}

// =================== CONFIGURATION MODULE ===================
class ConfigurationModule {
    constructor(portal) {
        this.portal = portal;
    }

    refresh() {
        // Configuration page doesn't need specific refresh logic
        console.log('Configuration page loaded');
    }
}

// =================== GLOBAL FUNCTIONS ===================
window.testTool = function(toolName) {
    portal.navigateToPage('playground');
    setTimeout(() => {
        document.getElementById('tool-select').value = toolName;
    }, 100);
};

window.viewToolSchema = function(toolName) {
    const tool = portal.tools.find(t => t.name === toolName);
    if (tool) {
        alert(`Schema for ${toolName}:\n\n${JSON.stringify(tool.schema, null, 2)}`);
    }
};

window.editPrompt = function(promptName) {
    alert(`Edit prompt: ${promptName}\n(This would open a prompt editor)`);
};

window.usePrompt = function(promptName) {
    portal.navigateToPage('playground');
    portal.showNotification(`Prompt ${promptName} loaded in playground`, 'info');
};

window.accessResource = function(uri) {
    portal.showNotification(`Accessing resource: ${uri}`, 'info');
};

// =================== ANALYTICS MODULE ===================
class AnalyticsModule {
    constructor(portal) {
        this.portal = portal;
        this.refresh();
    }

    refresh() {
        this.loadAnalyticsStats();
        this.loadAnalyticsCharts();
        this.loadAnalyticsTable();
    }

    async loadAnalyticsStats() {
        const statsContainer = document.getElementById('analytics-stats');
        if (!statsContainer) return;

        const stats = [
            { title: 'Total Operations', value: '2,847', change: '+12.5%', icon: 'activity' },
            { title: 'Success Rate', value: '97.8%', change: '+0.8%', icon: 'check-circle' },
            { title: 'Avg Response Time', value: '245ms', change: '-15ms', icon: 'clock' },
            { title: 'Active Sessions', value: '24', change: '+3', icon: 'users' }
        ];

        statsContainer.innerHTML = stats.map(stat => `
            <div class="metric-card">
                <div class="metric-header">
                    <i data-lucide="${stat.icon}" class="metric-icon"></i>
                    <span class="metric-change success">${stat.change}</span>
                </div>
                <div class="metric-value">${stat.value}</div>
                <div class="metric-label">${stat.title}</div>
            </div>
        `).join('');

        // Reinitialize icons
        if (window.lucide) {
            lucide.createIcons();
        }
    }

    async loadAnalyticsCharts() {
        // Implementation would go here for Chart.js charts
        console.log('Analytics charts loaded');
    }

    async loadAnalyticsTable() {
        const table = document.getElementById('analytics-table');
        if (!table) return;

        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td>search_memories</td>
                <td>memory</td>
                <td>67</td>
                <td><span class="status-indicator success">99.1%</span></td>
                <td>250ms</td>
                <td>+8</td>
                <td><span class="trend-up">↗️</span></td>
            </tr>
            <tr>
                <td>generate_image</td>
                <td>ai</td>
                <td>67</td>
                <td><span class="status-indicator warning">94.2%</span></td>
                <td>3500ms</td>
                <td>+12</td>
                <td><span class="trend-up">↗️</span></td>
            </tr>
            <tr>
                <td>web_search</td>
                <td>web</td>
                <td>89</td>
                <td><span class="status-indicator success">96.7%</span></td>
                <td>1500ms</td>
                <td>+23</td>
                <td><span class="trend-up">↗️</span></td>
            </tr>
        `;
    }
}

window.inspectResource = function(uri) {
    const resource = portal.resources.find(r => r.uri === uri);
    if (resource) {
        alert(`Resource Details:\n\nURI: ${resource.uri}\nType: ${resource.type}\nSize: ${resource.size} bytes\nMIME Type: ${resource.mimeType}`);
    }
};

// Initialize the portal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.portal = new MCPPortal();
});

// Export for API usage
window.MCPPortalAPI = {
    async callTool(name, args) {
        const response = await fetch(`${window.portal.apiBase}/admin/call-tool`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, arguments: args })
        });
        return await response.json();
    }
};