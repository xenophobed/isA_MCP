/**
 * 认证管理模块
 * 处理用户登录、登出、权限验证等功能
 */

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.token = null;
        this.refreshToken = null;
        this.tokenRefreshTimer = null;
        
        this.init();
    }
    
    /**
     * 初始化认证管理器
     */
    init() {
        // 从存储中恢复认证状态
        this.restoreAuthState();
        
        // 设置token自动刷新
        this.setupTokenRefresh();
        
        // 监听存储变化（多标签页同步）
        this.setupStorageListener();
    }
    
    /**
     * 从本地存储恢复认证状态
     */
    restoreAuthState() {
        this.token = Utils.StorageUtils.get('auth_token');
        this.refreshToken = Utils.StorageUtils.get('refresh_token');
        this.currentUser = Utils.StorageUtils.get('current_user');
        
        if (this.token && this.currentUser) {
            console.log('Auth state restored:', this.currentUser);
            this.updateUI();
        }
    }
    
    /**
     * 设置token自动刷新
     */
    setupTokenRefresh() {
        if (this.refreshToken) {
            // 每30分钟检查一次token是否需要刷新
            this.tokenRefreshTimer = setInterval(() => {
                this.checkAndRefreshToken();
            }, 30 * 60 * 1000);
        }
    }
    
    /**
     * 设置存储监听器（多标签页同步）
     */
    setupStorageListener() {
        window.addEventListener('storage', (e) => {
            if (e.key === 'auth_token' || e.key === 'current_user') {
                this.restoreAuthState();
            }
        });
    }
    
    /**
     * 用户登录
     * @param {string} username - 用户名
     * @param {string} password - 密码
     * @returns {Promise<Object>} 登录结果
     */
    async login(username, password) {
        try {
        // Validate input
        if (!username || !password) {
            throw new Error('Please enter username and password');
        }
            
            // 显示登录加载状态
            const loginBtn = Utils.DOMUtils.$('.login-btn');
            if (loginBtn) {
                window.app.ui.setButtonLoading(loginBtn, true);
            }
            
            // 调用API登录
            const result = await window.api.login(username.trim(), password);
            
            // 保存认证信息
            this.setAuthData(result);
            
            // 更新UI
            this.updateUI();
            
            // Show success message
            window.app.ui.showToast('Login successful!', 'success');
            
            // Navigate to Dashboard
            setTimeout(() => {
                window.app.navigation.showDashboard();
            }, 500);
            
            return result;
            
        } catch (error) {
            console.error('Login error:', error);
            window.app.ui.showToast(error.message || 'Login failed, please try again', 'error');
            throw error;
        } finally {
            // 隐藏登录加载状态
            const loginBtn = Utils.DOMUtils.$('.login-btn');
            if (loginBtn) {
                window.app.ui.setButtonLoading(loginBtn, false);
            }
        }
    }
    
    /**
     * 演示登录
     */
    async demoLogin() {
        try {
            await this.login('demo', 'demo123');
        } catch (error) {
            console.error('Demo login error:', error);
        }
    }
    
    /**
     * 用户登出
     */
    async logout() {
        try {
            // Confirm logout
            const confirmed = await window.app.ui.showConfirm(
                'Are you sure you want to sign out?',
                'Confirm Sign Out'
            );
            
            if (!confirmed) return;
            
            // 调用API登出
            if (this.token) {
                try {
                    await window.api.logout();
                } catch (error) {
                    console.error('Logout API error:', error);
                    // 即使API调用失败，也要清除本地认证状态
                }
            }
            
            // 清除认证状态
            this.clearAuthData();
            
            // 更新UI
            this.updateUI();
            
            // Show logout message
            window.app.ui.showToast('Successfully signed out', 'info');
            
            // 跳转到登录页
            setTimeout(() => {
                window.app.navigation.showLogin();
            }, 500);
            
        } catch (error) {
            console.error('Logout error:', error);
            window.app.ui.showToast('退出登录失败', 'error');
        }
    }
    
    /**
     * 设置认证数据
     * @param {Object} authData - 认证数据
     */
    setAuthData(authData) {
        this.token = authData.access_token;
        this.refreshToken = authData.refresh_token;
        this.currentUser = authData.user;
        
        // 保存到本地存储
        Utils.StorageUtils.set('auth_token', this.token);
        if (this.refreshToken) {
            Utils.StorageUtils.set('refresh_token', this.refreshToken);
        }
        Utils.StorageUtils.set('current_user', this.currentUser);
        
        // 更新API客户端的认证信息
        if (window.api) {
            window.api.setAuth(this.token, this.refreshToken);
        }
        
        // 设置token自动刷新
        this.setupTokenRefresh();
        
        console.log('Auth data set:', this.currentUser);
    }
    
    /**
     * 清除认证数据
     */
    clearAuthData() {
        this.token = null;
        this.refreshToken = null;
        this.currentUser = null;
        
        // 清除本地存储
        Utils.StorageUtils.remove('auth_token');
        Utils.StorageUtils.remove('refresh_token');
        Utils.StorageUtils.remove('current_user');
        
        // 清除API客户端的认证信息
        if (window.api) {
            window.api.clearAuth();
        }
        
        // 清除token刷新定时器
        if (this.tokenRefreshTimer) {
            clearInterval(this.tokenRefreshTimer);
            this.tokenRefreshTimer = null;
        }
        
        console.log('Auth data cleared');
    }
    
    /**
     * 检查并刷新token
     */
    async checkAndRefreshToken() {
        if (!this.refreshToken) return;
        
        try {
            // 这里可以添加token过期检查逻辑
            // 如果token即将过期，则调用刷新接口
            
            // 示例：检查token是否在1小时内过期
            const tokenPayload = this.parseJWT(this.token);
            if (tokenPayload && tokenPayload.exp) {
                const expirationTime = tokenPayload.exp * 1000;
                const currentTime = Date.now();
                const timeUntilExpiration = expirationTime - currentTime;
                
                // 如果token在1小时内过期，则刷新
                if (timeUntilExpiration < 60 * 60 * 1000) {
                    await this.refreshAccessToken();
                }
            }
            
        } catch (error) {
            console.error('Token refresh check error:', error);
        }
    }
    
    /**
     * 刷新访问token
     */
    async refreshAccessToken() {
        try {
            const result = await window.api.refreshAccessToken();
            this.setAuthData({
                access_token: result.access_token,
                refresh_token: result.refresh_token || this.refreshToken,
                user: this.currentUser
            });
            
            console.log('Token refreshed successfully');
            
        } catch (error) {
            console.error('Token refresh failed:', error);
            
            // 刷新失败，清除认证状态并跳转到登录页
            this.clearAuthData();
            window.app.ui.showToast('登录已过期，请重新登录', 'warning');
            window.app.navigation.showLogin();
        }
    }
    
    /**
     * 解析JWT token
     * @param {string} token - JWT token
     * @returns {Object|null} 解析后的payload
     */
    parseJWT(token) {
        if (!token) return null;
        
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64).split('').map(c => {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join('')
            );
            
            return JSON.parse(jsonPayload);
        } catch (error) {
            console.error('JWT parse error:', error);
            return null;
        }
    }
    
    /**
     * 检查用户是否已登录
     * @returns {boolean} 是否已登录
     */
    isAuthenticated() {
        return !!(this.token && this.currentUser);
    }
    
    /**
     * 检查用户权限
     * @param {string} permission - 权限名称
     * @returns {boolean} 是否有权限
     */
    hasPermission(permission) {
        if (!this.currentUser) return false;
        
        // 管理员拥有所有权限
        if (this.currentUser.role === 'admin') return true;
        
        // 这里可以根据实际需求扩展权限检查逻辑
        const userPermissions = this.currentUser.permissions || [];
        return userPermissions.includes(permission);
    }
    
    /**
     * 检查用户角色
     * @param {string} role - 角色名称
     * @returns {boolean} 是否具有该角色
     */
    hasRole(role) {
        if (!this.currentUser) return false;
        return this.currentUser.role === role;
    }
    
    /**
     * 获取当前用户信息
     * @returns {Object|null} 用户信息
     */
    getCurrentUser() {
        return this.currentUser;
    }
    
    /**
     * 获取用户显示名称
     * @returns {string} 显示名称
     */
    getUserDisplayName() {
        if (!this.currentUser) return '未登录';
        return this.currentUser.name || this.currentUser.username || '用户';
    }
    
    /**
     * 更新UI显示
     */
    updateUI() {
        const userDisplayName = this.getUserDisplayName();
        
        // 更新用户名显示
        const userNameElements = Utils.DOMUtils.$$('#currentUserName, #currentUserName2');
        userNameElements.forEach(element => {
            if (element) {
                element.textContent = userDisplayName;
            }
        });
        
        // 根据登录状态显示/隐藏页面元素
        if (this.isAuthenticated()) {
            // 已登录状态的UI更新
            this.updateAuthenticatedUI();
        } else {
            // 未登录状态的UI更新
            this.updateUnauthenticatedUI();
        }
    }
    
    /**
     * 更新已登录状态的UI
     */
    updateAuthenticatedUI() {
        // 这里可以添加已登录状态下的UI更新逻辑
        console.log('UI updated for authenticated user:', this.getUserDisplayName());
    }
    
    /**
     * 更新未登录状态的UI
     */
    updateUnauthenticatedUI() {
        // 这里可以添加未登录状态下的UI更新逻辑
        console.log('UI updated for unauthenticated state');
    }
    
    /**
     * 处理登录表单提交
     * @param {Event} event - 表单提交事件
     */
    async handleLoginSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const username = formData.get('username');
        const password = formData.get('password');
        
        try {
            await this.login(username, password);
        } catch (error) {
            // 错误已在login方法中处理
        }
    }
    
    /**
     * 验证密码强度
     * @param {string} password - 密码
     * @returns {Object} 验证结果
     */
    validatePasswordStrength(password) {
        return Utils.ValidationUtils.validatePassword(password);
    }
    
    /**
     * 生成安全的随机密码
     * @param {number} length - 密码长度
     * @returns {string} 随机密码
     */
    generateSecurePassword(length = 12) {
        const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()';
        let password = '';
        
        for (let i = 0; i < length; i++) {
            password += charset.charAt(Math.floor(Math.random() * charset.length));
        }
        
        return password;
    }
    
    /**
     * 处理认证错误
     * @param {Error} error - 错误对象
     */
    handleAuthError(error) {
        console.error('Auth error:', error);
        
        if (error.message.includes('401') || error.message.includes('认证失败')) {
            // 认证失败，清除认证状态
            this.clearAuthData();
            window.app.ui.showToast('认证失败，请重新登录', 'error');
            window.app.navigation.showLogin();
        } else {
            // 其他错误
            window.app.ui.showToast(error.message || '认证过程中发生错误', 'error');
        }
    }
    
    /**
     * 清理资源
     */
    cleanup() {
        if (this.tokenRefreshTimer) {
            clearInterval(this.tokenRefreshTimer);
            this.tokenRefreshTimer = null;
        }
    }
}

// 创建全局认证管理器实例
window.AuthManager = AuthManager;
