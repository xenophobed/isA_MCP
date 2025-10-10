/**
 * Dashboard管理模块
 * 处理Dashboard页面的数据加载、显示和交互功能
 */

class DashboardManager {
    constructor() {
        this.dashboardData = {
            stats: {
                total: 0,
                running: 0,
                completed: 0,
                failed: 0,
                pending: 0
            },
            recentTests: [],
            isLoading: false
        };
        
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.autoRefreshDelay = 30000; // 30秒自动刷新
        
        this.init();
    }
    
    /**
     * 初始化Dashboard管理器
     */
    init() {
        console.log('Dashboard manager initialized');
    }
    
    /**
     * 加载Dashboard数据
     */
    async loadDashboard() {
        if (this.dashboardData.isLoading) return;
        
        try {
            this.dashboardData.isLoading = true;
            this.showLoadingState();
            
            // 并行加载统计数据和最近测试
            const [statsData, recentTestsData] = await Promise.all([
                this.loadStats(),
                this.loadRecentTests()
            ]);
            
            // 更新数据
            this.dashboardData.stats = statsData;
            this.dashboardData.recentTests = recentTestsData.data || [];
            
            // 渲染UI
            this.renderStats();
            this.renderRecentTests();
            
            // 设置自动刷新
            this.setupAutoRefresh();
            
            console.log('Dashboard data loaded:', this.dashboardData);
            
        } catch (error) {
            console.error('Dashboard load error:', error);
            window.app.ui.showToast('加载Dashboard数据失败', 'error');
            this.showErrorState(error.message);
        } finally {
            this.dashboardData.isLoading = false;
            this.hideLoadingState();
        }
    }
    
    /**
     * 加载统计数据
     */
    async loadStats() {
        try {
            const stats = await window.api.getDashboardStats();
            return stats;
        } catch (error) {
            console.error('Load stats error:', error);
            return {
                total: 0,
                running: 0,
                completed: 0,
                failed: 0,
                pending: 0
            };
        }
    }
    
    /**
     * 加载最近测试数据
     */
    async loadRecentTests() {
        try {
            const params = {
                limit: 20,
                sort: 'created_time',
                order: 'desc'
            };
            
            const result = await window.api.getRecentTests(params);
            return result;
        } catch (error) {
            console.error('Load recent tests error:', error);
            return { data: [], total: 0 };
        }
    }
    
    /**
     * 刷新Dashboard数据
     */
    async refresh() {
        const refreshBtn = Utils.DOMUtils.$('.refresh-btn');
        
        try {
            if (refreshBtn) {
                refreshBtn.textContent = '刷新中...';
                refreshBtn.disabled = true;
            }
            
            await this.loadDashboard();
            
            window.app.ui.showToast('数据已刷新', 'success', 2000);
            
        } catch (error) {
            console.error('Dashboard refresh error:', error);
        } finally {
            if (refreshBtn) {
                refreshBtn.textContent = '🔄刷新';
                refreshBtn.disabled = false;
            }
        }
    }
    
    /**
     * 设置自动刷新
     */
    setupAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                this.loadDashboard();
            }, this.autoRefreshDelay);
        }
    }
    
    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    /**
     * 渲染统计卡片
     */
    renderStats() {
        const stats = this.dashboardData.stats;
        
        // 更新统计数字
        this.updateStatCard('runningTests', stats.running || 0);
        this.updateStatCard('completedTests', stats.completed || 0);
        this.updateStatCard('failedTests', stats.failed || 0);
        this.updateStatCard('totalTests', stats.total || 0);
        
        console.log('Stats rendered:', stats);
    }
    
    /**
     * 更新统计卡片
     * @param {string} elementId - 元素ID
     * @param {number} value - 数值
     */
    updateStatCard(elementId, value) {
        const element = Utils.DOMUtils.$(`#${elementId}`);
        if (element) {
            // 数字动画效果
            this.animateNumber(element, parseInt(element.textContent) || 0, value, 1000);
        }
    }
    
    /**
     * 数字动画效果
     * @param {Element} element - 目标元素
     * @param {number} start - 起始值
     * @param {number} end - 结束值
     * @param {number} duration - 动画时长
     */
    animateNumber(element, start, end, duration) {
        if (start === end) return;
        
        const startTime = performance.now();
        const difference = end - start;
        
        const step = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // 使用缓动函数
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.round(start + difference * easeOutQuart);
            
            element.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };
        
        requestAnimationFrame(step);
    }
    
    /**
     * 渲染最近测试列表
     */
    renderRecentTests() {
        const testGrid = Utils.DOMUtils.$('#testGrid');
        if (!testGrid) return;
        
        const tests = this.dashboardData.recentTests;
        
        if (tests.length === 0) {
            this.showEmptyState();
            return;
        }
        
        // 清空现有内容
        testGrid.innerHTML = '';
        
        // 渲染测试卡片
        tests.forEach(test => {
            const testCard = this.createTestCard(test);
            testGrid.appendChild(testCard);
        });
        
        console.log('Recent tests rendered:', tests.length);
    }
    
    /**
     * 创建测试卡片
     * @param {Object} test - 测试数据
     * @returns {Element} 测试卡片元素
     */
    createTestCard(test) {
        const statusClass = `status-${test.status}`;
        const statusText = this.getStatusText(test.status);
        const progressPercentage = test.progress || 0;
        const completedCases = Math.floor((test.testCases?.length || 0) * progressPercentage / 100);
        const totalCases = test.testCases?.length || 0;
        
        const card = Utils.DOMUtils.createElement('div', {
            className: `test-card ${test.status}`,
            onclick: () => this.showTestDetail(test.id)
        });
        
        card.innerHTML = `
            <div class="test-status ${statusClass}">
                ${this.getStatusIcon(test.status)} ${statusText}
            </div>
            <h3>${test.name}</h3>
            <p><strong>开始时间:</strong> ${Utils.DateUtils.format(test.createdTime, 'YYYY-MM-DD HH:mm')}</p>
            <p><strong>描述:</strong> ${test.description || '暂无描述'}</p>
            <div class="test-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progressPercentage}%"></div>
                </div>
                <div class="progress-text">${progressPercentage}% (${completedCases}/${totalCases})</div>
            </div>
            <div class="test-meta">
                <span class="test-duration">${this.getTestDuration(test)}</span>
                <span class="test-cases-count">${totalCases} 个测试用例</span>
            </div>
        `;
        
        return card;
    }
    
    /**
     * 获取状态文本
     * @param {string} status - 状态
     * @returns {string} 状态文本
     */
    getStatusText(status) {
        const statusMap = {
            pending: '待执行',
            running: '进行中',
            completed: '已完成',
            failed: '失败',
            cancelled: '已取消'
        };
        
        return statusMap[status] || '未知';
    }
    
    /**
     * 获取状态图标
     * @param {string} status - 状态
     * @returns {string} 状态图标
     */
    getStatusIcon(status) {
        const iconMap = {
            pending: '⏳',
            running: '🏃',
            completed: '✅',
            failed: '❌',
            cancelled: '🚫'
        };
        
        return iconMap[status] || '❓';
    }
    
    /**
     * 获取测试持续时间
     * @param {Object} test - 测试数据
     * @returns {string} 持续时间描述
     */
    getTestDuration(test) {
        if (!test.createdTime) return '';
        
        if (test.status === 'completed' && test.completedTime) {
            return Utils.DateUtils.getDuration(test.createdTime, test.completedTime);
        } else if (test.status === 'running') {
            return Utils.DateUtils.getDuration(test.createdTime);
        } else {
            return Utils.DateUtils.getRelativeTime(test.createdTime);
        }
    }
    
    /**
     * 显示测试详情
     * @param {string} testId - 测试ID
     */
    showTestDetail(testId) {
        console.log('Show test detail:', testId);
        
        // 这里可以跳转到测试详情页面或显示详情模态框
        window.app.navigation.showTestDetail();
        
        // 如果需要显示特定测试的详情，可以传递testId参数
        // window.app.testPlan.loadTestPlan(testId);
    }
    
    /**
     * 过滤测试列表
     */
    filterTests() {
        const statusFilter = Utils.DOMUtils.$('#statusFilter');
        if (!statusFilter) return;
        
        const selectedStatus = statusFilter.value;
        const testCards = Utils.DOMUtils.$$('.test-card');
        
        testCards.forEach(card => {
            if (selectedStatus === 'all') {
                card.style.display = 'block';
            } else {
                const hasStatus = card.classList.contains(selectedStatus);
                card.style.display = hasStatus ? 'block' : 'none';
            }
        });
        
        // 更新显示的测试数量
        const visibleCards = Array.from(testCards).filter(card => 
            card.style.display !== 'none'
        );
        
        console.log(`Filtered tests: ${visibleCards.length} visible out of ${testCards.length}`);
    }
    
    /**
     * 显示加载状态
     */
    showLoadingState() {
        const testGrid = Utils.DOMUtils.$('#testGrid');
        if (testGrid) {
            testGrid.innerHTML = `
                <div class="loading-placeholder">
                    <div class="spinner"></div>
                    <p>加载测试数据中...</p>
                </div>
            `;
        }
    }
    
    /**
     * 隐藏加载状态
     */
    hideLoadingState() {
        // 加载状态会在renderRecentTests中被替换
    }
    
    /**
     * 显示错误状态
     * @param {string} message - 错误消息
     */
    showErrorState(message) {
        const testGrid = Utils.DOMUtils.$('#testGrid');
        if (testGrid) {
            testGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">❌</div>
                    <h3>数据加载失败</h3>
                    <p>${message}</p>
                    <button class="action-btn primary" onclick="app.dashboard.refresh()">
                        重试
                    </button>
                </div>
            `;
        }
    }
    
    /**
     * 显示空状态
     */
    showEmptyState() {
        const testGrid = Utils.DOMUtils.$('#testGrid');
        if (testGrid) {
            testGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <h3>暂无测试数据</h3>
                    <p>还没有创建任何测试计划，点击下方按钮开始创建吧！</p>
                    <button class="action-btn primary" onclick="app.navigation.showTestDetail()">
                        <i class="icon-plus"></i>创建测试计划
                    </button>
                </div>
            `;
        }
    }
    
    /**
     * 获取Dashboard统计摘要
     * @returns {Object} 统计摘要
     */
    getStatsSummary() {
        const stats = this.dashboardData.stats;
        const total = stats.total || 0;
        
        if (total === 0) {
            return {
                message: '暂无测试数据',
                recommendation: '创建您的第一个测试计划'
            };
        }
        
        const runningPercentage = Math.round((stats.running / total) * 100);
        const completedPercentage = Math.round((stats.completed / total) * 100);
        const failedPercentage = Math.round((stats.failed / total) * 100);
        
        let message = `总共 ${total} 个测试`;
        if (stats.running > 0) {
            message += `，${stats.running} 个正在执行`;
        }
        if (stats.completed > 0) {
            message += `，${stats.completed} 个已完成`;
        }
        if (stats.failed > 0) {
            message += `，${stats.failed} 个失败`;
        }
        
        let recommendation = '';
        if (failedPercentage > 20) {
            recommendation = '建议检查失败的测试用例';
        } else if (runningPercentage > 50) {
            recommendation = '系统负载较高，建议适当控制并发测试数量';
        } else if (completedPercentage > 80) {
            recommendation = '测试执行情况良好';
        }
        
        return { message, recommendation };
    }
    
    /**
     * 导出Dashboard报告
     */
    async exportDashboardReport() {
        try {
            const summary = this.getStatsSummary();
            const reportData = {
                generatedAt: Utils.DateUtils.format(new Date()),
                stats: this.dashboardData.stats,
                summary: summary,
                recentTests: this.dashboardData.recentTests.map(test => ({
                    name: test.name,
                    status: this.getStatusText(test.status),
                    progress: `${test.progress || 0}%`,
                    createdTime: Utils.DateUtils.format(test.createdTime),
                    duration: this.getTestDuration(test)
                }))
            };
            
            // 生成CSV格式的报告
            const csvContent = this.generateCSVReport(reportData);
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            
            const filename = `dashboard_report_${Utils.DateUtils.format(new Date(), 'YYYY-MM-DD_HH-mm-ss')}.csv`;
            window.app.ui.downloadFile(blob, filename);
            
            window.app.ui.showToast('报告导出成功', 'success');
            
        } catch (error) {
            console.error('Export dashboard report error:', error);
            window.app.ui.showToast('报告导出失败', 'error');
        }
    }
    
    /**
     * 生成CSV格式报告
     * @param {Object} reportData - 报告数据
     * @returns {string} CSV内容
     */
    generateCSVReport(reportData) {
        let csv = '\ufeff'; // BOM for UTF-8
        
        // 报告头部
        csv += 'Dashboard报告\n';
        csv += `生成时间,${reportData.generatedAt}\n`;
        csv += `总结,${reportData.summary.message}\n`;
        csv += `建议,${reportData.summary.recommendation}\n\n`;
        
        // 统计数据
        csv += '统计数据\n';
        csv += '项目,数量\n';
        csv += `总计,${reportData.stats.total}\n`;
        csv += `进行中,${reportData.stats.running}\n`;
        csv += `已完成,${reportData.stats.completed}\n`;
        csv += `失败,${reportData.stats.failed}\n`;
        csv += `待执行,${reportData.stats.pending}\n\n`;
        
        // 最近测试
        csv += '最近测试\n';
        csv += '测试名称,状态,进度,创建时间,持续时间\n';
        reportData.recentTests.forEach(test => {
            csv += `"${test.name}","${test.status}","${test.progress}","${test.createdTime}","${test.duration}"\n`;
        });
        
        return csv;
    }
    
    /**
     * 清理资源
     */
    cleanup() {
        this.stopAutoRefresh();
    }
    
    /**
     * 获取当前Dashboard数据
     * @returns {Object} Dashboard数据
     */
    getDashboardData() {
        return Utils.DataUtils.deepClone(this.dashboardData);
    }
}

// 创建全局Dashboard管理器实例
window.DashboardManager = DashboardManager;
