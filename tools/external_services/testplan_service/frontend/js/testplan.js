/**
 * 测试计划管理模块
 * 处理测试计划的创建、编辑、执行和管理功能
 */

class TestPlanManager {
    constructor() {
        this.testPlans = [];
        this.currentPlan = null;
        this.uploadProgress = 0;
        this.isUploading = false;
        this.searchQuery = '';
        this.sortBy = 'createdTime';
        this.sortOrder = 'desc';
        
        this.init();
    }
    
    /**
     * 初始化测试计划管理器
     */
    init() {
        this.setupFileUpload();
        console.log('TestPlan manager initialized');
    }
    
    /**
     * 设置文件上传功能
     */
    setupFileUpload() {
        const fileInput = Utils.DOMUtils.$('#xlsxFile');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.handleFileUpload(files);
            });
        }
    }
    
    /**
     * 加载测试计划列表
     */
    async loadTestPlans() {
        try {
            this.showPlansLoading();
            
            const params = {
                search: this.searchQuery,
                sort: this.sortBy,
                order: this.sortOrder,
                limit: 100
            };
            
            const result = await window.api.getTestPlans(params);
            this.testPlans = result.data || [];
            
            this.renderTestPlans();
            console.log('Test plans loaded:', this.testPlans.length);
            
        } catch (error) {
            console.error('Load test plans error:', error);
            window.app.ui.showToast('加载测试计划失败', 'error');
            this.showPlansError(error.message);
        }
    }
    
    /**
     * 渲染测试计划列表
     */
    renderTestPlans() {
        const plansList = Utils.DOMUtils.$('#plansList');
        if (!plansList) return;
        
        if (this.testPlans.length === 0) {
            this.showEmptyPlansState();
            return;
        }
        
        plansList.innerHTML = '';
        
        this.testPlans.forEach(plan => {
            const planItem = this.createPlanItem(plan);
            plansList.appendChild(planItem);
        });
    }
    
    /**
     * 创建测试计划项目
     * @param {Object} plan - 测试计划数据
     * @returns {Element} 计划项目元素
     */
    createPlanItem(plan) {
        const planItem = Utils.DOMUtils.createElement('div', {
            className: 'plan-item'
        });
        
        const testCasesCount = plan.testCases?.length || 0;
        const statusText = this.getStatusText(plan.status);
        const statusIcon = this.getStatusIcon(plan.status);
        
        planItem.innerHTML = `
            <div class="plan-header" onclick="app.testPlan.togglePlan('${plan.id}')">
                <div class="plan-info">
                    <h4>${plan.name}</h4>
                    <div class="plan-meta">
                        <span><i class="icon-file"></i> ${plan.fileName}</span>
                        <span><i class="icon-clock"></i> ${Utils.DateUtils.format(plan.createdTime, 'YYYY-MM-DD HH:mm')}</span>
                        <span><i class="icon-list"></i> ${testCasesCount} 个测试用例</span>
                        <span class="plan-status ${plan.status}">
                            ${statusIcon} ${statusText}
                        </span>
                    </div>
                </div>
                <span class="expand-icon" id="icon-${plan.id}">▶</span>
            </div>
            <div class="plan-content" id="content-${plan.id}">
                ${this.createPlanContent(plan)}
            </div>
        `;
        
        return planItem;
    }
    
    /**
     * 创建计划内容
     * @param {Object} plan - 测试计划数据
     * @returns {string} 内容HTML
     */
    createPlanContent(plan) {
        const testCases = plan.testCases || [];
        
        let content = `
            <div class="plan-actions">
                <div class="export-buttons">
                    <button class="export-btn" onclick="app.testPlan.exportPlan('${plan.id}', 'xlsx')">
                        <i class="icon-download"></i>导出XLSX
                    </button>
                    <button class="export-btn" onclick="app.testPlan.exportPlan('${plan.id}', 'csv')">
                        <i class="icon-download"></i>导出CSV
                    </button>
                    <button class="export-btn" onclick="app.testPlan.exportPlan('${plan.id}', 'pdf')">
                        <i class="icon-download"></i>导出PDF
                    </button>
                </div>
                <div class="plan-controls">
                    <button class="action-btn secondary" onclick="app.testPlan.editPlan('${plan.id}')">
                        <i class="icon-edit"></i>编辑
                    </button>
                    <button class="action-btn primary" onclick="app.testPlan.executePlan('${plan.id}')">
                        <i class="icon-play"></i>执行测试
                    </button>
                    <button class="action-btn danger" onclick="app.testPlan.deletePlan('${plan.id}')">
                        <i class="icon-delete"></i>删除
                    </button>
                </div>
            </div>
        `;
        
        if (testCases.length > 0) {
            content += `
                <div class="plan-table-wrapper">
                    <table class="plan-table">
                        <thead>
                            <tr>
                                <th>用例ID</th>
                                <th>用例名称</th>
                                <th>测试类型</th>
                                <th>优先级</th>
                                <th>状态</th>
                                <th>执行时长</th>
                                <th>描述</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${testCases.map(tc => this.createTestCaseRow(plan.id, tc)).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            content += `
                <div class="empty-test-cases">
                    <p>该测试计划暂无测试用例</p>
                    <button class="action-btn primary" onclick="app.testPlan.addTestCases('${plan.id}')">
                        <i class="icon-plus"></i>添加测试用例
                    </button>
                </div>
            `;
        }
        
        return content;
    }
    
    /**
     * 创建测试用例行
     * @param {string} planId - 计划ID
     * @param {Object} testCase - 测试用例数据
     * @returns {string} 表格行HTML
     */
    createTestCaseRow(planId, testCase) {
        const statusClass = this.getTestCaseStatusClass(testCase.status);
        const statusText = this.getTestCaseStatusText(testCase.status);
        
        return `
            <tr class="test-case-row ${statusClass}" data-case-id="${testCase.id}">
                <td><code>${testCase.id}</code></td>
                <td><strong>${testCase.name}</strong></td>
                <td><span class="test-type">${testCase.type}</span></td>
                <td><span class="priority priority-${testCase.priority?.toLowerCase()}">${testCase.priority}</span></td>
                <td><span class="case-status ${statusClass}">${statusText}</span></td>
                <td>${testCase.duration || '-'}</td>
                <td class="description-cell" title="${testCase.description}">
                    ${this.truncateText(testCase.description, 50)}
                </td>
                <td class="actions-cell">
                    <button class="icon-btn" onclick="app.testPlan.viewTestCase('${planId}', '${testCase.id}')" title="查看详情">
                        <i class="icon-eye"></i>
                    </button>
                    <button class="icon-btn" onclick="app.testPlan.editTestCase('${planId}', '${testCase.id}')" title="编辑">
                        <i class="icon-edit"></i>
                    </button>
                    <button class="icon-btn" onclick="app.testPlan.runTestCase('${planId}', '${testCase.id}')" title="运行">
                        <i class="icon-play"></i>
                    </button>
                </td>
            </tr>
        `;
    }
    
    /**
     * 切换计划展开/收起
     * @param {string} planId - 计划ID
     */
    togglePlan(planId) {
        const content = Utils.DOMUtils.$(`#content-${planId}`);
        const icon = Utils.DOMUtils.$(`#icon-${planId}`);
        const header = content?.previousElementSibling;
        
        if (content && icon) {
            const isExpanded = content.classList.contains('expanded');
            
            if (isExpanded) {
                content.classList.remove('expanded');
                icon.classList.remove('rotated');
                header?.classList.remove('expanded');
            } else {
                content.classList.add('expanded');
                icon.classList.add('rotated');
                header?.classList.add('expanded');
            }
        }
    }
    
    /**
     * 处理文件上传
     * @param {File[]} files - 文件列表
     */
    async handleFileUpload(files) {
        if (!files || files.length === 0) return;
        
        // 验证文件
        const validFiles = files.filter(file => {
            if (!Utils.FileUtils.validateFileType(file, ['.xlsx', '.xls'])) {
                window.app.ui.showToast(`文件 ${file.name} 格式不支持，只支持 .xlsx 和 .xls 格式`, 'error');
                return false;
            }
            
            if (!Utils.FileUtils.validateFileSize(file, 100)) {
                window.app.ui.showToast(`文件 ${file.name} 大小超过100MB限制`, 'error');
                return false;
            }
            
            return true;
        });
        
        if (validFiles.length === 0) return;
        
        // 逐个上传文件
        for (const file of validFiles) {
            await this.uploadSingleFile(file);
        }
    }
    
    /**
     * 上传单个文件
     * @param {File} file - 文件对象
     */
    async uploadSingleFile(file) {
        try {
            this.isUploading = true;
            this.showUploadProgress();
            
            const options = {
                parseOptions: {
                    generateTestCases: true,
                    validateFormat: true,
                    extractMetadata: true
                }
            };
            
            const result = await window.api.uploadXLSXFile(
                file, 
                options,
                (progress) => this.updateUploadProgress(progress)
            );
            
            // 上传成功
            window.app.ui.showToast(
                `文件 ${file.name} 上传成功，已生成测试计划 "${result.data.name}"`, 
                'success'
            );
            
            // 刷新测试计划列表
            await this.loadTestPlans();
            
        } catch (error) {
            console.error('File upload error:', error);
            window.app.ui.showToast(
                `文件 ${file.name} 上传失败: ${error.message}`, 
                'error'
            );
        } finally {
            this.isUploading = false;
            this.hideUploadProgress();
            
            // 清空文件选择
            const fileInput = Utils.DOMUtils.$('#xlsxFile');
            if (fileInput) {
                fileInput.value = '';
            }
        }
    }
    
    /**
     * 显示上传进度
     */
    showUploadProgress() {
        const uploadStatus = Utils.DOMUtils.$('#uploadStatus');
        const statusText = Utils.DOMUtils.$('#statusText');
        const progressFill = Utils.DOMUtils.$('#progressFill');
        
        if (uploadStatus) {
            uploadStatus.classList.remove('hidden');
        }
        
        if (statusText) {
            statusText.textContent = '正在上传文件...';
        }
        
        if (progressFill) {
            progressFill.style.width = '0%';
        }
    }
    
    /**
     * 更新上传进度
     * @param {number} progress - 进度百分比
     */
    updateUploadProgress(progress) {
        this.uploadProgress = progress;
        
        const statusText = Utils.DOMUtils.$('#statusText');
        const progressFill = Utils.DOMUtils.$('#progressFill');
        
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        
        if (statusText) {
            if (progress < 50) {
                statusText.textContent = '正在上传文件...';
            } else if (progress < 90) {
                statusText.textContent = '正在解析文件...';
            } else {
                statusText.textContent = '正在生成测试计划...';
            }
        }
    }
    
    /**
     * 隐藏上传进度
     */
    hideUploadProgress() {
        const uploadStatus = Utils.DOMUtils.$('#uploadStatus');
        if (uploadStatus) {
            uploadStatus.classList.add('hidden');
        }
    }
    
    /**
     * 搜索测试计划
     */
    searchPlans() {
        const searchInput = Utils.DOMUtils.$('#planSearch');
        if (!searchInput) return;
        
        this.searchQuery = searchInput.value.trim();
        
        // 使用防抖延迟搜索
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        this.searchTimeout = setTimeout(() => {
            this.loadTestPlans();
        }, 300);
    }
    
    /**
     * 刷新测试计划列表
     */
    async refreshPlans() {
        await this.loadTestPlans();
        window.app.ui.showToast('测试计划列表已刷新', 'success', 2000);
    }
    
    /**
     * 创建新测试计划
     */
    async createNew() {
        const name = await window.app.ui.showPrompt(
            '请输入测试计划名称：',
            `新测试计划_${Utils.DateUtils.format(new Date(), 'YYYY-MM-DD')}`
        );
        
        if (!name) return;
        
        try {
            const planData = {
                name: name.trim(),
                description: '',
                testCases: [],
                status: 'pending',
                createdTime: new Date().toISOString()
            };
            
            const result = await window.api.createTestPlan(planData);
            
            window.app.ui.showToast(`测试计划 "${name}" 创建成功`, 'success');
            await this.loadTestPlans();
            
        } catch (error) {
            console.error('Create test plan error:', error);
            window.app.ui.showToast('创建测试计划失败', 'error');
        }
    }
    
    /**
     * 编辑测试计划
     * @param {string} planId - 计划ID
     */
    async editPlan(planId) {
        const plan = this.testPlans.find(p => p.id === planId);
        if (!plan) return;
        
        const newName = await window.app.ui.showPrompt(
            '请输入新的测试计划名称：',
            plan.name
        );
        
        if (!newName || newName === plan.name) return;
        
        try {
            await window.api.updateTestPlan(planId, {
                name: newName.trim()
            });
            
            window.app.ui.showToast('测试计划更新成功', 'success');
            await this.loadTestPlans();
            
        } catch (error) {
            console.error('Update test plan error:', error);
            window.app.ui.showToast('更新测试计划失败', 'error');
        }
    }
    
    /**
     * 删除测试计划
     * @param {string} planId - 计划ID
     */
    async deletePlan(planId) {
        const plan = this.testPlans.find(p => p.id === planId);
        if (!plan) return;
        
        const confirmed = await window.app.ui.showConfirm(
            `确定要删除测试计划 "${plan.name}" 吗？此操作不可恢复。`,
            '确认删除'
        );
        
        if (!confirmed) return;
        
        try {
            await window.api.deleteTestPlan(planId);
            
            window.app.ui.showToast(`测试计划 "${plan.name}" 已删除`, 'success');
            await this.loadTestPlans();
            
        } catch (error) {
            console.error('Delete test plan error:', error);
            window.app.ui.showToast('删除测试计划失败', 'error');
        }
    }
    
    /**
     * 执行测试计划
     * @param {string} planId - 计划ID
     */
    async executePlan(planId) {
        const plan = this.testPlans.find(p => p.id === planId);
        if (!plan) return;
        
        const confirmed = await window.app.ui.showConfirm(
            `确定要执行测试计划 "${plan.name}" 吗？`,
            '确认执行'
        );
        
        if (!confirmed) return;
        
        try {
            const config = {
                parallel: true,
                maxConcurrency: 5,
                stopOnError: false
            };
            
            const result = await window.api.executeTestPlan(planId, config);
            
            window.app.ui.showToast(`测试计划 "${plan.name}" 开始执行`, 'success');
            
            // 跳转到Dashboard查看执行状态
            setTimeout(() => {
                window.app.navigation.showDashboard();
            }, 1000);
            
        } catch (error) {
            console.error('Execute test plan error:', error);
            window.app.ui.showToast('执行测试计划失败', 'error');
        }
    }
    
    /**
     * 导出测试计划
     * @param {string} planId - 计划ID
     * @param {string} format - 导出格式
     */
    async exportPlan(planId, format) {
        const plan = this.testPlans.find(p => p.id === planId);
        if (!plan) return;
        
        try {
            const blob = await window.api.exportTestPlan(planId, format);
            const filename = `${plan.name}.${format}`;
            
            window.app.ui.downloadFile(blob, filename);
            window.app.ui.showToast(`测试计划导出成功: ${filename}`, 'success');
            
        } catch (error) {
            console.error('Export test plan error:', error);
            window.app.ui.showToast(`导出${format.toUpperCase()}失败`, 'error');
        }
    }
    
    /**
     * 下载模板
     */
    async downloadTemplate() {
        try {
            const blob = await window.api.downloadTemplate('standard');
            const filename = `3GPP测试计划模板_${Utils.DateUtils.format(new Date(), 'YYYY-MM-DD')}.xlsx`;
            
            window.app.ui.downloadFile(blob, filename);
            window.app.ui.showToast('模板下载成功', 'success');
            
        } catch (error) {
            console.error('Download template error:', error);
            window.app.ui.showToast('模板下载失败', 'error');
        }
    }
    
    /**
     * 显示模板选择
     */
    showTemplates() {
        const content = `
            <div class="templates-content">
                <h4>选择测试计划模板</h4>
                <div class="template-list">
                    <div class="template-item" onclick="app.testPlan.downloadTemplate('standard')">
                        <div class="template-icon">📋</div>
                        <h5>标准测试模板</h5>
                        <p>包含基础的3GPP测试用例结构</p>
                    </div>
                    <div class="template-item" onclick="app.testPlan.downloadTemplate('lte')">
                        <div class="template-icon">📶</div>
                        <h5>LTE测试模板</h5>
                        <p>专门用于LTE网络功能测试</p>
                    </div>
                    <div class="template-item" onclick="app.testPlan.downloadTemplate('5g')">
                        <div class="template-icon">🚀</div>
                        <h5>5G NR测试模板</h5>
                        <p>适用于5G新空口测试场景</p>
                    </div>
                </div>
            </div>
        `;
        
        window.app.ui.showModal('测试计划模板', content);
    }
    
    // ===== 工具方法 =====
    
    /**
     * 获取状态文本
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
     * 获取测试用例状态类
     */
    getTestCaseStatusClass(status) {
        return `status-${status?.toLowerCase() || 'unknown'}`;
    }
    
    /**
     * 获取测试用例状态文本
     */
    getTestCaseStatusText(status) {
        const statusMap = {
            pending: '待执行',
            running: '执行中',
            passed: '通过',
            failed: '失败',
            skipped: '跳过'
        };
        return statusMap[status] || '未知';
    }
    
    /**
     * 截断文本
     */
    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
    
    /**
     * 显示计划加载状态
     */
    showPlansLoading() {
        const plansList = Utils.DOMUtils.$('#plansList');
        if (plansList) {
            plansList.innerHTML = `
                <div class="loading-placeholder">
                    <div class="spinner"></div>
                    <p>加载测试计划中...</p>
                </div>
            `;
        }
    }
    
    /**
     * 显示计划错误状态
     */
    showPlansError(message) {
        const plansList = Utils.DOMUtils.$('#plansList');
        if (plansList) {
            plansList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">❌</div>
                    <h3>加载失败</h3>
                    <p>${message}</p>
                    <button class="action-btn primary" onclick="app.testPlan.loadTestPlans()">
                        重试
                    </button>
                </div>
            `;
        }
    }
    
    /**
     * 显示空计划状态
     */
    showEmptyPlansState() {
        const plansList = Utils.DOMUtils.$('#plansList');
        if (plansList) {
            plansList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <h3>暂无测试计划</h3>
                    <p>还没有创建任何测试计划，点击上方按钮开始创建或上传XLSX文件生成测试计划。</p>
                    <div class="empty-actions">
                        <button class="action-btn primary" onclick="app.testPlan.createNew()">
                            <i class="icon-plus"></i>创建测试计划
                        </button>
                        <button class="action-btn secondary" onclick="document.getElementById('xlsxFile').click()">
                            <i class="icon-upload"></i>上传文件
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// 创建全局测试计划管理器实例
window.TestPlanManager = TestPlanManager;
