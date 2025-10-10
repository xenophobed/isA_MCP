/**
 * 主应用程序
 * 统一管理所有模块，提供应用程序的入口点和全局状态管理
 */

class Application {
    constructor() {
        this.currentPage = 'login';
        this.isInitialized = false;
        this.modules = {};
        
        // 绑定this到全局作用域
        window.app = this;
        
        this.init();
    }
    
    /**
     * 初始化应用程序
     */
    init() {
        console.log('🚀 Initializing 3GPP Test System...');
        
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeApp();
            });
        } else {
            this.initializeApp();
        }
    }
    
    /**
     * 初始化应用程序核心
     */
    async initializeApp() {
        try {
            // 初始化模块
            await this.initializeModules();
            
            // 设置全局事件监听器
            this.setupGlobalEventListeners();
            
            // 初始化路由
            this.initializeRouting();
            
            // 检查认证状态并显示相应页面
            this.checkAuthAndShowPage();
            
            this.isInitialized = true;
            console.log('✅ 3GPP Test System initialized successfully');
            
        } catch (error) {
            console.error('❌ Application initialization failed:', error);
            this.showInitializationError(error);
        }
    }
    
    /**
     * 初始化所有模块
     */
    async initializeModules() {
        console.log('📦 Initializing modules...');
        
        // 初始化UI组件
        this.ui = new UIComponents();
        this.modules.ui = this.ui;
        
        // 初始化认证管理器
        this.auth = new AuthManager();
        this.modules.auth = this.auth;
        
        // 初始化导航管理器
        this.navigation = new NavigationManager();
        this.modules.navigation = this.navigation;
        
        // 初始化Dashboard管理器
        this.dashboard = new DashboardManager();
        this.modules.dashboard = this.dashboard;
        
        // 初始化测试计划管理器
        this.testPlan = new TestPlanManager();
        this.modules.testPlan = this.testPlan;
        
        console.log('✅ All modules initialized');
    }
    
    /**
     * 设置全局事件监听器
     */
    setupGlobalEventListeners() {
        // 登录表单提交事件
        const loginForm = Utils.DOMUtils.$('#loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                this.auth.handleLoginSubmit(e);
            });
        }
        
        // 窗口大小变化事件
        window.addEventListener('resize', Utils.DataUtils.throttle(() => {
            this.handleWindowResize();
        }, 250));
        
        // 页面可见性变化事件
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });
        
        // 在线/离线状态变化事件
        window.addEventListener('online', () => {
            this.handleOnlineStatusChange(true);
        });
        
        window.addEventListener('offline', () => {
            this.handleOnlineStatusChange(false);
        });
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            this.handleGlobalKeydown(e);
        });
        
        console.log('📡 Global event listeners set up');
    }
    
    /**
     * 初始化路由
     */
    initializeRouting() {
        // 监听浏览器前进/后退事件
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) {
                this.showPage(e.state.page, false);
            }
        });
        
        // 检查URL参数
        const urlParams = new URLSearchParams(window.location.search);
        const page = urlParams.get('page');
        if (page) {
            this.currentPage = page;
        }
        
        console.log('🛣️ Routing initialized');
    }
    
    /**
     * 检查认证状态并显示相应页面
     */
    checkAuthAndShowPage() {
        if (this.auth.isAuthenticated()) {
            // 已登录，根据当前页面显示
            if (this.currentPage === 'login') {
                this.navigation.showDashboard();
            } else {
                this.showPage(this.currentPage);
            }
        } else {
            // 未登录，显示登录页面
            this.navigation.showLogin();
        }
    }
    
    /**
     * 显示页面
     * @param {string} pageId - 页面ID
     * @param {boolean} updateHistory - 是否更新浏览器历史
     */
    showPage(pageId, updateHistory = true) {
        // 隐藏所有页面
        const pages = Utils.DOMUtils.$$('.page');
        pages.forEach(page => {
            page.classList.remove('active');
        });
        
        // 显示目标页面
        const targetPage = Utils.DOMUtils.$(`#${pageId}`);
        if (targetPage) {
            targetPage.classList.add('active');
            this.currentPage = pageId.replace('Page', '');
            
            // 更新浏览器历史
            if (updateHistory) {
                const url = new URL(window.location);
                url.searchParams.set('page', this.currentPage);
                window.history.pushState(
                    { page: this.currentPage }, 
                    '', 
                    url.toString()
                );
            }
            
            // 页面切换后的处理
            this.handlePageSwitch(this.currentPage);
            
            console.log(`📄 Switched to page: ${this.currentPage}`);
        } else {
            console.error(`❌ Page not found: ${pageId}`);
        }
    }
    
    /**
     * 处理页面切换后的逻辑
     * @param {string} page - 页面名称
     */
    handlePageSwitch(page) {
        switch (page) {
            case 'dashboard':
                // 加载Dashboard数据
                if (this.dashboard) {
                    this.dashboard.loadDashboard();
                }
                break;
                
            case 'testDetail':
                // 加载测试计划数据
                if (this.testPlan) {
                    this.testPlan.loadTestPlans();
                }
                break;
                
            case 'login':
                // 清理其他页面的数据
                if (this.dashboard) {
                    this.dashboard.stopAutoRefresh();
                }
                break;
        }
        
        // 更新用户界面
        if (this.auth) {
            this.auth.updateUI();
        }
    }
    
    /**
     * 处理窗口大小变化
     */
    handleWindowResize() {
        // 这里可以添加响应式处理逻辑
        const width = window.innerWidth;
        const isMobile = width <= 768;
        
        document.body.classList.toggle('mobile', isMobile);
        document.body.classList.toggle('desktop', !isMobile);
    }
    
    /**
     * 处理页面可见性变化
     */
    handleVisibilityChange() {
        if (document.hidden) {
            // 页面隐藏时暂停自动刷新
            if (this.dashboard) {
                this.dashboard.stopAutoRefresh();
            }
        } else {
            // 页面显示时恢复自动刷新
            if (this.dashboard && this.currentPage === 'dashboard') {
                this.dashboard.setupAutoRefresh();
            }
        }
    }
    
    /**
     * 处理在线/离线状态变化
     * @param {boolean} isOnline - 是否在线
     */
    handleOnlineStatusChange(isOnline) {
        if (isOnline) {
            this.ui.showToast('网络连接已恢复', 'success', 3000);
            
            // 重新加载当前页面数据
            if (this.currentPage === 'dashboard') {
                this.dashboard.refresh();
            } else if (this.currentPage === 'testDetail') {
                this.testPlan.refreshPlans();
            }
        } else {
            this.ui.showToast('网络连接已断开，部分功能可能无法使用', 'warning', 5000);
        }
    }
    
    /**
     * 处理全局键盘事件
     * @param {KeyboardEvent} e - 键盘事件
     */
    handleGlobalKeydown(e) {
        // Ctrl/Cmd + K: 全局搜索
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            this.showGlobalSearch();
        }
        
        // Ctrl/Cmd + R: 刷新当前页面数据
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            this.refreshCurrentPage();
        }
        
        // Escape: 关闭模态框
        if (e.key === 'Escape') {
            this.ui.closeModal();
            this.ui.closeAllDropdowns();
        }
        
        // F1: 显示帮助
        if (e.key === 'F1') {
            e.preventDefault();
            this.showHelp();
        }
    }
    
    /**
     * 显示全局搜索
     */
    showGlobalSearch() {
        // 根据当前页面显示不同的搜索功能
        if (this.currentPage === 'testDetail') {
            const searchInput = Utils.DOMUtils.$('#planSearch');
            if (searchInput) {
                searchInput.focus();
            }
        }
    }
    
    /**
     * 刷新当前页面
     */
    refreshCurrentPage() {
        switch (this.currentPage) {
            case 'dashboard':
                if (this.dashboard) {
                    this.dashboard.refresh();
                }
                break;
                
            case 'testDetail':
                if (this.testPlan) {
                    this.testPlan.refreshPlans();
                }
                break;
        }
    }
    
    /**
     * 显示帮助信息
     */
    showHelp() {
        const helpContent = `
            <div class="help-content">
                <h4>快捷键</h4>
                <div class="shortcut-list">
                    <div class="shortcut-item">
                        <kbd>Ctrl/Cmd + K</kbd>
                        <span>全局搜索</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Ctrl/Cmd + R</kbd>
                        <span>刷新页面数据</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Esc</kbd>
                        <span>关闭模态框</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>F1</kbd>
                        <span>显示帮助</span>
                    </div>
                </div>
                
                <h4>功能说明</h4>
                <ul>
                    <li><strong>Dashboard:</strong> 查看测试执行状态和统计信息</li>
                    <li><strong>测试详情:</strong> 管理测试计划和测试用例</li>
                    <li><strong>文件上传:</strong> 支持拖拽上传XLSX文件</li>
                    <li><strong>导出功能:</strong> 支持导出为XLSX、CSV、PDF格式</li>
                </ul>
                
                <h4>联系支持</h4>
                <p>如有问题，请联系系统管理员。</p>
            </div>
        `;
        
        this.ui.showModal('帮助信息', helpContent);
    }
    
    /**
     * 显示初始化错误
     * @param {Error} error - 错误对象
     */
    showInitializationError(error) {
        document.body.innerHTML = `
            <div class="error-container">
                <div class="error-content">
                    <h1>🚫 系统初始化失败</h1>
                    <p>应用程序无法正常启动，请刷新页面重试。</p>
                    <details>
                        <summary>错误详情</summary>
                        <pre>${error.message}\n${error.stack}</pre>
                    </details>
                    <button onclick="location.reload()" class="retry-btn">
                        🔄 刷新页面
                    </button>
                </div>
            </div>
        `;
    }
    
    /**
     * 获取应用程序状态
     * @returns {Object} 应用程序状态
     */
    getAppState() {
        return {
            isInitialized: this.isInitialized,
            currentPage: this.currentPage,
            isAuthenticated: this.auth?.isAuthenticated() || false,
            currentUser: this.auth?.getCurrentUser() || null,
            modules: Object.keys(this.modules),
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * 显示应用程序信息
     */
    showAppInfo() {
        const state = this.getAppState();
        const content = `
            <div class="app-info">
                <h4>应用程序信息</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <label>版本:</label>
                        <span>v1.0.0</span>
                    </div>
                    <div class="info-item">
                        <label>当前页面:</label>
                        <span>${state.currentPage}</span>
                    </div>
                    <div class="info-item">
                        <label>认证状态:</label>
                        <span>${state.isAuthenticated ? '已登录' : '未登录'}</span>
                    </div>
                    <div class="info-item">
                        <label>当前用户:</label>
                        <span>${state.currentUser?.name || '无'}</span>
                    </div>
                    <div class="info-item">
                        <label>加载模块:</label>
                        <span>${state.modules.join(', ')}</span>
                    </div>
                    <div class="info-item">
                        <label>初始化时间:</label>
                        <span>${state.timestamp}</span>
                    </div>
                </div>
            </div>
        `;
        
        this.ui.showModal('应用程序信息', content);
    }
    
    /**
     * 清理应用程序资源
     */
    cleanup() {
        console.log('🧹 Cleaning up application resources...');
        
        // 清理模块资源
        Object.values(this.modules).forEach(module => {
            if (module && typeof module.cleanup === 'function') {
                module.cleanup();
            }
        });
        
        // 清理事件监听器
        // (大部分事件监听器会在页面卸载时自动清理)
        
        console.log('✅ Application cleanup completed');
    }
}

/**
 * 导航管理器
 * 处理页面间的导航逻辑
 */
class NavigationManager {
    constructor() {
        this.history = [];
        this.maxHistoryLength = 10;
    }
    
    /**
     * 显示登录页面
     */
    showLogin() {
        this.navigateTo('loginPage', 'login');
    }
    
    /**
     * 显示Dashboard页面
     */
    showDashboard() {
        this.navigateTo('dashboardPage', 'dashboard');
    }
    
    /**
     * 显示测试详情页面
     */
    showTestDetail() {
        this.navigateTo('testDetailPage', 'testDetail');
    }
    
    /**
     * 导航到指定页面
     * @param {string} pageId - 页面ID
     * @param {string} pageName - 页面名称
     */
    navigateTo(pageId, pageName) {
        // 记录导航历史
        this.addToHistory({
            pageId,
            pageName,
            timestamp: new Date(),
            from: window.app.currentPage
        });
        
        // 执行页面切换
        window.app.showPage(pageId);
    }
    
    /**
     * 添加到导航历史
     * @param {Object} entry - 历史记录条目
     */
    addToHistory(entry) {
        this.history.push(entry);
        
        // 限制历史记录长度
        if (this.history.length > this.maxHistoryLength) {
            this.history.shift();
        }
    }
    
    /**
     * 获取导航历史
     * @returns {Array} 导航历史
     */
    getHistory() {
        return [...this.history];
    }
    
    /**
     * 返回上一页
     */
    goBack() {
        if (this.history.length > 1) {
            // 移除当前页面
            this.history.pop();
            
            // 获取上一页面
            const previousPage = this.history[this.history.length - 1];
            if (previousPage) {
                window.app.showPage(previousPage.pageId, false);
            }
        } else {
            // 默认返回Dashboard
            this.showDashboard();
        }
    }
}

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.cleanup();
    }
});

// 创建应用程序实例
console.log('🎯 Starting 3GPP Test System Application...');
new Application();
