/**
 * API接口管理
 * 提供与后端服务的通信功能，包括认证、测试计划管理、文件上传等
 */

class APIClient {
    constructor() {
        this.baseURL = this.getBaseURL();
        this.token = Utils.StorageUtils.get('auth_token');
        this.refreshToken = Utils.StorageUtils.get('refresh_token');
        
        // 请求拦截器
        this.setupInterceptors();
    }
    
    /**
     * 获取API基础URL
     * @returns {string} 基础URL
     */
    getBaseURL() {
        // 开发环境和生产环境的URL配置
        const isDev = window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1';
        
        if (isDev) {
            return 'http://localhost:8000/api';
        } else {
            return '/api';
        }
    }
    
    /**
     * 设置请求拦截器
     */
    setupInterceptors() {
        // 这里可以添加全局请求拦截逻辑
        console.log('API Client initialized with base URL:', this.baseURL);
    }
    
    /**
     * 通用HTTP请求方法
     * @param {string} endpoint - 接口端点
     * @param {Object} options - 请求选项
     * @returns {Promise<Object>} 响应数据
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultHeaders = {
            'Content-Type': 'application/json',
        };
        
        // 添加认证头
        if (this.token) {
            defaultHeaders['Authorization'] = `Bearer ${this.token}`;
        }
        
        const config = {
            method: 'GET',
            headers: defaultHeaders,
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };
        
        try {
            console.log(`API Request: ${config.method} ${url}`, config);
            
            const response = await fetch(url, config);
            
            // 处理认证失败
            if (response.status === 401) {
                await this.handleAuthError();
                throw new Error('认证失败，请重新登录');
            }
            
            // 处理其他HTTP错误
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log(`API Response: ${config.method} ${url}`, data);
            
            return data;
            
        } catch (error) {
            console.error(`API Error: ${config.method} ${url}`, error);
            throw error;
        }
    }
    
    /**
     * 处理认证错误
     */
    async handleAuthError() {
        // 尝试刷新token
        if (this.refreshToken) {
            try {
                await this.refreshAccessToken();
                return;
            } catch (error) {
                console.error('Token refresh failed:', error);
            }
        }
        
        // 清除认证信息并跳转到登录页
        this.clearAuth();
        if (window.app && window.app.navigation) {
            window.app.navigation.showLogin();
        }
    }
    
    /**
     * 刷新访问token
     */
    async refreshAccessToken() {
        const response = await fetch(`${this.baseURL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh_token: this.refreshToken
            })
        });
        
        if (!response.ok) {
            throw new Error('Token refresh failed');
        }
        
        const data = await response.json();
        this.setAuth(data.access_token, data.refresh_token);
    }
    
    /**
     * 设置认证信息
     * @param {string} token - 访问token
     * @param {string} refreshToken - 刷新token
     */
    setAuth(token, refreshToken = null) {
        this.token = token;
        Utils.StorageUtils.set('auth_token', token);
        
        if (refreshToken) {
            this.refreshToken = refreshToken;
            Utils.StorageUtils.set('refresh_token', refreshToken);
        }
    }
    
    /**
     * 清除认证信息
     */
    clearAuth() {
        this.token = null;
        this.refreshToken = null;
        Utils.StorageUtils.remove('auth_token');
        Utils.StorageUtils.remove('refresh_token');
        Utils.StorageUtils.remove('current_user');
    }
    
    // ===== 认证相关接口 =====
    
    /**
     * 用户登录
     * @param {string} username - 用户名
     * @param {string} password - 密码
     * @returns {Promise<Object>} 登录结果
     */
    async login(username, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password
            })
        });
        
        // 设置认证信息
        this.setAuth(data.access_token, data.refresh_token);
        
        // 保存用户信息
        if (data.user) {
            Utils.StorageUtils.set('current_user', data.user);
        }
        
        return data;
    }
    
    /**
     * 用户登出
     * @returns {Promise<Object>} 登出结果
     */
    async logout() {
        try {
            await this.request('/auth/logout', {
                method: 'POST'
            });
        } finally {
            this.clearAuth();
        }
    }
    
    /**
     * 获取当前用户信息
     * @returns {Promise<Object>} 用户信息
     */
    async getCurrentUser() {
        return await this.request('/auth/me');
    }
    
    // ===== 测试计划相关接口 =====
    
    /**
     * 获取测试计划列表
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 测试计划列表
     */
    async getTestPlans(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? `/testplans?${queryString}` : '/testplans';
        return await this.request(endpoint);
    }
    
    /**
     * 获取单个测试计划详情
     * @param {string} planId - 测试计划ID
     * @returns {Promise<Object>} 测试计划详情
     */
    async getTestPlan(planId) {
        return await this.request(`/testplans/${planId}`);
    }
    
    /**
     * 创建测试计划
     * @param {Object} planData - 测试计划数据
     * @returns {Promise<Object>} 创建结果
     */
    async createTestPlan(planData) {
        return await this.request('/testplans', {
            method: 'POST',
            body: JSON.stringify(planData)
        });
    }
    
    /**
     * 更新测试计划
     * @param {string} planId - 测试计划ID
     * @param {Object} planData - 更新数据
     * @returns {Promise<Object>} 更新结果
     */
    async updateTestPlan(planId, planData) {
        return await this.request(`/testplans/${planId}`, {
            method: 'PUT',
            body: JSON.stringify(planData)
        });
    }
    
    /**
     * 删除测试计划
     * @param {string} planId - 测试计划ID
     * @returns {Promise<Object>} 删除结果
     */
    async deleteTestPlan(planId) {
        return await this.request(`/testplans/${planId}`, {
            method: 'DELETE'
        });
    }
    
    /**
     * 执行测试计划
     * @param {string} planId - 测试计划ID
     * @param {Object} config - 执行配置
     * @returns {Promise<Object>} 执行结果
     */
    async executeTestPlan(planId, config = {}) {
        return await this.request(`/testplans/${planId}/execute`, {
            method: 'POST',
            body: JSON.stringify(config)
        });
    }
    
    // ===== 测试用例相关接口 =====
    
    /**
     * 获取测试用例列表
     * @param {string} planId - 测试计划ID
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 测试用例列表
     */
    async getTestCases(planId, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? 
            `/testplans/${planId}/testcases?${queryString}` : 
            `/testplans/${planId}/testcases`;
        return await this.request(endpoint);
    }
    
    /**
     * 获取测试用例详情
     * @param {string} planId - 测试计划ID
     * @param {string} caseId - 测试用例ID
     * @returns {Promise<Object>} 测试用例详情
     */
    async getTestCase(planId, caseId) {
        return await this.request(`/testplans/${planId}/testcases/${caseId}`);
    }
    
    /**
     * 更新测试用例状态
     * @param {string} planId - 测试计划ID
     * @param {string} caseId - 测试用例ID
     * @param {string} status - 新状态
     * @param {Object} result - 测试结果
     * @returns {Promise<Object>} 更新结果
     */
    async updateTestCaseStatus(planId, caseId, status, result = {}) {
        return await this.request(`/testplans/${planId}/testcases/${caseId}/status`, {
            method: 'PUT',
            body: JSON.stringify({
                status,
                result
            })
        });
    }
    
    // ===== 文件上传相关接口 =====
    
    /**
     * 上传XLSX文件并生成测试计划
     * @param {File} file - XLSX文件
     * @param {Object} options - 上传选项
     * @param {Function} onProgress - 进度回调
     * @returns {Promise<Object>} 上传结果
     */
    async uploadXLSXFile(file, options = {}, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);
        
        // 添加选项参数
        Object.entries(options).forEach(([key, value]) => {
            formData.append(key, JSON.stringify(value));
        });
        
        const xhr = new XMLHttpRequest();
        
        return new Promise((resolve, reject) => {
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('响应解析失败'));
                    }
                } else {
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        reject(new Error(errorResponse.message || `HTTP ${xhr.status}`));
                    } catch (error) {
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('文件上传失败'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('文件上传超时'));
            });
            
            xhr.open('POST', `${this.baseURL}/upload/xlsx`);
            
            // 添加认证头
            if (this.token) {
                xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
            }
            
            // 设置超时时间 (5分钟)
            xhr.timeout = 5 * 60 * 1000;
            
            xhr.send(formData);
        });
    }
    
    /**
     * 下载测试计划模板
     * @param {string} templateType - 模板类型
     * @returns {Promise<Blob>} 文件blob
     */
    async downloadTemplate(templateType = 'standard') {
        const response = await fetch(`${this.baseURL}/templates/${templateType}`, {
            method: 'GET',
            headers: {
                'Authorization': this.token ? `Bearer ${this.token}` : undefined
            }
        });
        
        if (!response.ok) {
            throw new Error(`模板下载失败: ${response.statusText}`);
        }
        
        return await response.blob();
    }
    
    // ===== 导出相关接口 =====
    
    /**
     * 导出测试计划
     * @param {string} planId - 测试计划ID
     * @param {string} format - 导出格式 ('xlsx', 'csv', 'pdf')
     * @param {Object} options - 导出选项
     * @returns {Promise<Blob>} 文件blob
     */
    async exportTestPlan(planId, format = 'xlsx', options = {}) {
        const queryString = new URLSearchParams({
            format,
            ...options
        }).toString();
        
        const response = await fetch(`${this.baseURL}/testplans/${planId}/export?${queryString}`, {
            method: 'GET',
            headers: {
                'Authorization': this.token ? `Bearer ${this.token}` : undefined
            }
        });
        
        if (!response.ok) {
            throw new Error(`导出失败: ${response.statusText}`);
        }
        
        return await response.blob();
    }
    
    // ===== Dashboard统计接口 =====
    
    /**
     * 获取Dashboard统计数据
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 统计数据
     */
    async getDashboardStats(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? `/dashboard/stats?${queryString}` : '/dashboard/stats';
        return await this.request(endpoint);
    }
    
    /**
     * 获取最近测试列表
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>} 测试列表
     */
    async getRecentTests(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? `/dashboard/recent?${queryString}` : '/dashboard/recent';
        return await this.request(endpoint);
    }
    
    // ===== 系统配置接口 =====
    
    /**
     * 获取系统配置
     * @returns {Promise<Object>} 系统配置
     */
    async getSystemConfig() {
        return await this.request('/system/config');
    }
    
    /**
     * 更新系统配置
     * @param {Object} config - 配置数据
     * @returns {Promise<Object>} 更新结果
     */
    async updateSystemConfig(config) {
        return await this.request('/system/config', {
            method: 'PUT',
            body: JSON.stringify(config)
        });
    }
    
    /**
     * 获取系统健康状态
     * @returns {Promise<Object>} 健康状态
     */
    async getSystemHealth() {
        return await this.request('/system/health');
    }
}

// 模拟API响应 (用于开发和演示)
class MockAPIClient extends APIClient {
    constructor() {
        super();
        this.mockData = this.initMockData();
    }
    
    /**
     * 初始化模拟数据
     */
    initMockData() {
        return {
            users: [
                {
                    id: '1',
                    username: 'admin',
                    password: 'admin123',
                    name: 'Administrator',
                    email: 'admin@3gpp-test.com',
                    role: 'admin'
                },
                {
                    id: '2',
                    username: 'demo',
                    password: 'demo123',
                    name: 'Demo User',
                    email: 'demo@3gpp-test.com',
                    role: 'user'
                }
            ],
            testPlans: [
                {
                    id: '1',
                    name: 'LTE Basic Functionality Tests',
                    fileName: 'lte_basic_test.xlsx',
                    createdTime: '2024-01-15 09:30:00',
                    status: 'running',
                    progress: 65,
                    testCases: this.generateMockTestCases(45, 'LTE'),
                    description: 'Comprehensive LTE network basic functionality test plan'
                },
                {
                    id: '2',
                    name: '5G NR Performance Tests',
                    fileName: '5g_performance_test.xlsx',
                    createdTime: '2024-01-14 14:20:00',
                    status: 'completed',
                    progress: 100,
                    testCases: this.generateMockTestCases(32, '5G'),
                    description: '5G New Radio network performance evaluation test plan'
                },
                {
                    id: '3',
                    name: 'VoLTE Interoperability Tests',
                    fileName: 'volte_interop_test.xlsx',
                    createdTime: '2024-01-16 11:15:00',
                    status: 'failed',
                    progress: 23,
                    testCases: this.generateMockTestCases(28, 'VoLTE'),
                    description: 'Voice over LTE interoperability testing plan'
                }
            ]
        };
    }
    
    /**
     * Generate mock test cases
     */
    generateMockTestCases(count, technology) {
        const testCases = [];
        const testTypes = ['Signaling Flow Test', 'Performance Test', 'Protocol Conformance Test', 'Interoperability Test'];
        const priorities = ['High', 'Medium', 'Low'];
        const statuses = ['Pending', 'Running', 'Passed', 'Failed'];
        
        for (let i = 1; i <= count; i++) {
            testCases.push({
                id: `TC_${technology}_${String(i).padStart(3, '0')}`,
                name: `${technology} Test Case ${i}`,
                type: testTypes[Math.floor(Math.random() * testTypes.length)],
                priority: priorities[Math.floor(Math.random() * priorities.length)],
                status: statuses[Math.floor(Math.random() * statuses.length)],
                description: `This is the detailed description for ${technology} test case ${i}`,
                expectedResult: 'Expected result description',
                actualResult: Math.random() > 0.5 ? 'Actual result description' : '',
                duration: `${Math.floor(Math.random() * 60)} minutes`,
                createdTime: Utils.DateUtils.format(new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000))
            });
        }
        return testCases;
    }
    
    /**
     * 模拟网络延迟
     */
    async mockDelay(min = 500, max = 1500) {
        const delay = Math.random() * (max - min) + min;
        return new Promise(resolve => setTimeout(resolve, delay));
    }
    
    /**
     * 模拟登录
     */
    async login(username, password) {
        await this.mockDelay();
        
        const user = this.mockData.users.find(u => 
            u.username === username && u.password === password
        );
        
        if (!user) {
            throw new Error('Invalid username or password');
        }
        
        const accessToken = `mock_token_${Date.now()}`;
        const refreshToken = `mock_refresh_${Date.now()}`;
        
        this.setAuth(accessToken, refreshToken);
        Utils.StorageUtils.set('current_user', user);
        
        return {
            access_token: accessToken,
            refresh_token: refreshToken,
            user: {
                id: user.id,
                username: user.username,
                name: user.name,
                email: user.email,
                role: user.role
            }
        };
    }
    
    /**
     * 模拟获取测试计划列表
     */
    async getTestPlans(params = {}) {
        await this.mockDelay();
        
        let plans = [...this.mockData.testPlans];
        
        // 模拟过滤
        if (params.status) {
            plans = plans.filter(p => p.status === params.status);
        }
        
        if (params.search) {
            plans = plans.filter(p => 
                p.name.toLowerCase().includes(params.search.toLowerCase())
            );
        }
        
        return {
            data: plans,
            total: plans.length,
            page: parseInt(params.page) || 1,
            pageSize: parseInt(params.pageSize) || 10
        };
    }
    
    /**
     * 模拟文件上传
     */
    async uploadXLSXFile(file, options = {}, onProgress = null) {
        // 模拟上传进度
        if (onProgress) {
            for (let progress = 0; progress <= 100; progress += 10) {
                setTimeout(() => onProgress(progress), progress * 50);
            }
        }
        
        await this.mockDelay(2000, 4000);
        
        // 模拟生成新的测试计划
        const newPlan = {
            id: Utils.DataUtils.generateId('plan'),
            name: `测试计划_${file.name.replace('.xlsx', '')}`,
            fileName: file.name,
            createdTime: Utils.DateUtils.format(new Date()),
            status: 'pending',
            progress: 0,
            testCases: this.generateMockTestCases(Math.floor(Math.random() * 50) + 10, '3GPP'),
            description: '从XLSX文件生成的测试计划'
        };
        
        this.mockData.testPlans.push(newPlan);
        
        return {
            success: true,
            data: newPlan,
            message: 'File uploaded and parsed successfully'
        };
    }
    
    /**
     * 模拟获取Dashboard统计
     */
    async getDashboardStats(params = {}) {
        await this.mockDelay();
        
        const plans = this.mockData.testPlans;
        const stats = {
            total: plans.length,
            running: plans.filter(p => p.status === 'running').length,
            completed: plans.filter(p => p.status === 'completed').length,
            failed: plans.filter(p => p.status === 'failed').length,
            pending: plans.filter(p => p.status === 'pending').length
        };
        
        return stats;
    }
    
    /**
     * 模拟获取最近测试
     */
    async getRecentTests(params = {}) {
        await this.mockDelay();
        
        const plans = [...this.mockData.testPlans]
            .sort((a, b) => new Date(b.createdTime) - new Date(a.createdTime))
            .slice(0, parseInt(params.limit) || 10);
        
        return {
            data: plans,
            total: plans.length
        };
    }
}

// 根据环境选择API客户端
const isDevelopment = window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1';

// 创建API客户端实例
window.api = isDevelopment ? new MockAPIClient() : new APIClient();

console.log('API Client initialized:', window.api);
