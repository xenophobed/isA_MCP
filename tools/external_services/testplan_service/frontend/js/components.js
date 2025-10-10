/**
 * UI组件管理
 * 提供通用的UI组件功能，包括模态框、通知、加载状态等
 */

class UIComponents {
    constructor() {
        this.toasts = [];
        this.modals = [];
        this.init();
    }
    
    /**
     * 初始化UI组件
     */
    init() {
        this.setupEventListeners();
        this.setupDragAndDrop();
    }
    
    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 模态框关闭事件
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal();
            }
        });
        
        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
        
        // 用户菜单点击外部关闭
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.user-menu')) {
                this.closeAllDropdowns();
            }
        });
    }
    
    /**
     * 设置拖拽上传功能
     */
    setupDragAndDrop() {
        const uploadArea = Utils.DOMUtils.$('#uploadArea');
        if (!uploadArea) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('dragover');
            }, false);
        });
        
        uploadArea.addEventListener('drop', this.handleDrop.bind(this), false);
    }
    
    /**
     * 阻止默认事件
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    /**
     * 处理文件拖拽
     */
    handleDrop(e) {
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0 && window.app && window.app.testPlan) {
            window.app.testPlan.handleFileUpload(files);
        }
    }
    
    // ===== Toast通知系统 =====
    
    /**
     * 显示Toast通知
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 ('success', 'error', 'warning', 'info')
     * @param {number} duration - 显示时长(ms)
     * @returns {string} Toast ID
     */
    showToast(message, type = 'info', duration = 5000) {
        const toastId = Utils.DataUtils.generateId('toast');
        const toast = this.createToastElement(toastId, message, type);
        
        const container = Utils.DOMUtils.$('#toastContainer');
        if (container) {
            container.appendChild(toast);
        }
        
        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                this.removeToast(toastId);
            }, duration);
        }
        
        // 记录Toast
        this.toasts.push({
            id: toastId,
            element: toast,
            type,
            message,
            createdAt: new Date()
        });
        
        return toastId;
    }
    
    /**
     * 创建Toast元素
     */
    createToastElement(id, message, type) {
        const toast = Utils.DOMUtils.createElement('div', {
            className: `toast ${type}`,
            id: id
        });
        
        const titleMap = {
            success: '成功',
            error: '错误',
            warning: '警告',
            info: '信息'
        };
        
        toast.innerHTML = `
            <div class="toast-header">
                <h4 class="toast-title">${titleMap[type]}</h4>
                <button class="toast-close" onclick="app.ui.removeToast('${id}')">&times;</button>
            </div>
            <p class="toast-message">${message}</p>
        `;
        
        return toast;
    }
    
    /**
     * 移除Toast
     * @param {string} toastId - Toast ID
     */
    removeToast(toastId) {
        const toastIndex = this.toasts.findIndex(t => t.id === toastId);
        if (toastIndex === -1) return;
        
        const toast = this.toasts[toastIndex];
        if (toast.element && toast.element.parentNode) {
            toast.element.style.animation = 'toastSlideOut 0.3s ease-in forwards';
            setTimeout(() => {
                if (toast.element.parentNode) {
                    toast.element.parentNode.removeChild(toast.element);
                }
            }, 300);
        }
        
        this.toasts.splice(toastIndex, 1);
    }
    
    /**
     * 清除所有Toast
     */
    clearAllToasts() {
        this.toasts.forEach(toast => {
            this.removeToast(toast.id);
        });
    }
    
    // ===== 模态框系统 =====
    
    /**
     * 显示模态框
     * @param {string} title - 标题
     * @param {string} content - 内容HTML
     * @param {Object} options - 选项
     * @returns {string} 模态框ID
     */
    showModal(title, content, options = {}) {
        const modalId = Utils.DataUtils.generateId('modal');
        const modal = Utils.DOMUtils.$('#modal');
        
        if (!modal) {
            console.error('Modal element not found');
            return null;
        }
        
        // 设置内容
        Utils.DOMUtils.$('#modalTitle').textContent = title;
        Utils.DOMUtils.$('#modalBody').innerHTML = content;
        
        // 设置按钮
        const footer = Utils.DOMUtils.$('#modalFooter');
        footer.innerHTML = '';
        
        if (options.buttons) {
            options.buttons.forEach(button => {
                const btn = Utils.DOMUtils.createElement('button', {
                    className: `action-btn ${button.type || 'secondary'}`,
                    onclick: button.onclick || (() => this.closeModal())
                }, button.text);
                footer.appendChild(btn);
            });
        } else {
            // 默认关闭按钮
            const closeBtn = Utils.DOMUtils.createElement('button', {
                className: 'action-btn secondary',
                onclick: () => this.closeModal()
            }, '关闭');
            footer.appendChild(closeBtn);
        }
        
        // 显示模态框
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // 记录模态框
        this.modals.push({
            id: modalId,
            title,
            content,
            options,
            createdAt: new Date()
        });
        
        return modalId;
    }
    
    /**
     * 关闭模态框
     */
    closeModal() {
        const modal = Utils.DOMUtils.$('#modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
        
        // 清除记录
        this.modals = [];
    }
    
    /**
     * 显示确认对话框
     * @param {string} message - 确认消息
     * @param {string} title - 标题
     * @returns {Promise<boolean>} 用户选择结果
     */
    showConfirm(message, title = '确认') {
        return new Promise((resolve) => {
            const content = `<p style="font-size: 16px; line-height: 1.5; margin: 20px 0;">${message}</p>`;
            
            this.showModal(title, content, {
                buttons: [
                    {
                        text: '取消',
                        type: 'secondary',
                        onclick: () => {
                            this.closeModal();
                            resolve(false);
                        }
                    },
                    {
                        text: '确认',
                        type: 'primary',
                        onclick: () => {
                            this.closeModal();
                            resolve(true);
                        }
                    }
                ]
            });
        });
    }
    
    /**
     * 显示提示对话框
     * @param {string} message - 提示消息
     * @param {string} title - 标题
     * @returns {Promise<void>}
     */
    showAlert(message, title = '提示') {
        return new Promise((resolve) => {
            const content = `<p style="font-size: 16px; line-height: 1.5; margin: 20px 0;">${message}</p>`;
            
            this.showModal(title, content, {
                buttons: [
                    {
                        text: '确定',
                        type: 'primary',
                        onclick: () => {
                            this.closeModal();
                            resolve();
                        }
                    }
                ]
            });
        });
    }
    
    /**
     * 显示输入对话框
     * @param {string} message - 提示消息
     * @param {string} defaultValue - 默认值
     * @param {string} title - 标题
     * @returns {Promise<string|null>} 用户输入的值
     */
    showPrompt(message, defaultValue = '', title = '输入') {
        return new Promise((resolve) => {
            const inputId = Utils.DataUtils.generateId('input');
            const content = `
                <div style="margin: 20px 0;">
                    <p style="font-size: 16px; line-height: 1.5; margin-bottom: 15px;">${message}</p>
                    <input type="text" id="${inputId}" value="${defaultValue}" 
                           style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px;">
                </div>
            `;
            
            this.showModal(title, content, {
                buttons: [
                    {
                        text: '取消',
                        type: 'secondary',
                        onclick: () => {
                            this.closeModal();
                            resolve(null);
                        }
                    },
                    {
                        text: '确定',
                        type: 'primary',
                        onclick: () => {
                            const input = Utils.DOMUtils.$(`#${inputId}`);
                            const value = input ? input.value.trim() : '';
                            this.closeModal();
                            resolve(value);
                        }
                    }
                ]
            });
            
            // 聚焦输入框
            setTimeout(() => {
                const input = Utils.DOMUtils.$(`#${inputId}`);
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        });
    }
    
    // ===== 下拉菜单系统 =====
    
    /**
     * 切换用户菜单
     */
    toggleUserMenu() {
        const dropdown = Utils.DOMUtils.$('#userDropdown') || Utils.DOMUtils.$('#userDropdown2');
        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    }
    
    /**
     * 关闭所有下拉菜单
     */
    closeAllDropdowns() {
        const dropdowns = Utils.DOMUtils.$$('.user-dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.classList.add('hidden');
        });
    }
    
    // ===== 加载状态管理 =====
    
    /**
     * 显示加载状态
     * @param {Element|string} element - 目标元素或选择器
     * @param {string} message - 加载消息
     */
    showLoading(element, message = '加载中...') {
        const el = typeof element === 'string' ? Utils.DOMUtils.$(element) : element;
        if (!el) return;
        
        const loadingId = Utils.DataUtils.generateId('loading');
        const loading = Utils.DOMUtils.createElement('div', {
            className: 'loading-overlay',
            id: loadingId
        }, `
            <div class="loading-content">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `);
        
        el.style.position = 'relative';
        el.appendChild(loading);
        
        return loadingId;
    }
    
    /**
     * 隐藏加载状态
     * @param {string} loadingId - 加载ID
     */
    hideLoading(loadingId) {
        const loading = Utils.DOMUtils.$(`#${loadingId}`);
        if (loading && loading.parentNode) {
            loading.parentNode.removeChild(loading);
        }
    }
    
    /**
     * 显示按钮加载状态
     * @param {Element|string} button - 按钮元素或选择器
     * @param {boolean} loading - 是否显示加载状态
     */
    setButtonLoading(button, loading = true) {
        const btn = typeof button === 'string' ? Utils.DOMUtils.$(button) : button;
        if (!btn) return;
        
        const textSpan = btn.querySelector('.btn-text');
        const spinner = btn.querySelector('.loading-spinner');
        
        if (loading) {
            btn.disabled = true;
            if (textSpan) textSpan.style.display = 'none';
            if (spinner) spinner.classList.remove('hidden');
        } else {
            btn.disabled = false;
            if (textSpan) textSpan.style.display = 'inline';
            if (spinner) spinner.classList.add('hidden');
        }
    }
    
    // ===== 进度条管理 =====
    
    /**
     * 更新进度条
     * @param {Element|string} progressBar - 进度条元素或选择器
     * @param {number} percentage - 进度百分比 (0-100)
     * @param {string} text - 进度文本
     */
    updateProgress(progressBar, percentage, text = null) {
        const bar = typeof progressBar === 'string' ? Utils.DOMUtils.$(progressBar) : progressBar;
        if (!bar) return;
        
        const fill = bar.querySelector('.progress-fill');
        if (fill) {
            fill.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
        }
        
        if (text) {
            const textEl = bar.nextElementSibling;
            if (textEl && textEl.classList.contains('progress-text')) {
                textEl.textContent = text;
            }
        }
    }
    
    // ===== 表单验证 =====
    
    /**
     * 验证表单
     * @param {Element|string} form - 表单元素或选择器
     * @returns {Object} 验证结果
     */
    validateForm(form) {
        const formEl = typeof form === 'string' ? Utils.DOMUtils.$(form) : form;
        if (!formEl) return { valid: false, errors: ['表单不存在'] };
        
        const errors = [];
        const requiredFields = formEl.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            const value = field.value.trim();
            if (!value) {
                const label = field.previousElementSibling?.textContent || field.name || '字段';
                errors.push(`${label}不能为空`);
                this.setFieldError(field, `${label}不能为空`);
            } else {
                this.clearFieldError(field);
            }
        });
        
        // 邮箱验证
        const emailFields = formEl.querySelectorAll('input[type="email"]');
        emailFields.forEach(field => {
            if (field.value && !Utils.ValidationUtils.isEmail(field.value)) {
                errors.push('邮箱格式不正确');
                this.setFieldError(field, '邮箱格式不正确');
            }
        });
        
        return {
            valid: errors.length === 0,
            errors
        };
    }
    
    /**
     * 设置字段错误状态
     * @param {Element} field - 字段元素
     * @param {string} message - 错误消息
     */
    setFieldError(field, message) {
        field.classList.add('error');
        
        // 移除现有错误消息
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // 添加错误消息
        const errorEl = Utils.DOMUtils.createElement('div', {
            className: 'field-error'
        }, message);
        
        field.parentNode.appendChild(errorEl);
    }
    
    /**
     * 清除字段错误状态
     * @param {Element} field - 字段元素
     */
    clearFieldError(field) {
        field.classList.remove('error');
        
        const errorEl = field.parentNode.querySelector('.field-error');
        if (errorEl) {
            errorEl.remove();
        }
    }
    
    // ===== 工具方法 =====
    
    /**
     * 显示用户资料
     */
    showUserProfile() {
        const user = Utils.StorageUtils.get('current_user');
        if (!user) return;
        
        const content = `
            <div class="user-profile">
                <div class="profile-field">
                    <label>用户名:</label>
                    <span>${user.username}</span>
                </div>
                <div class="profile-field">
                    <label>姓名:</label>
                    <span>${user.name}</span>
                </div>
                <div class="profile-field">
                    <label>邮箱:</label>
                    <span>${user.email}</span>
                </div>
                <div class="profile-field">
                    <label>角色:</label>
                    <span>${user.role === 'admin' ? '管理员' : '用户'}</span>
                </div>
            </div>
        `;
        
        this.showModal('个人资料', content);
    }
    
    /**
     * 显示系统设置
     */
    showSettings() {
        const content = `
            <div class="settings-content">
                <h4>系统设置</h4>
                <p>系统设置功能正在开发中...</p>
            </div>
        `;
        
        this.showModal('系统设置', content);
    }
    
    /**
     * 下载文件
     * @param {Blob} blob - 文件blob
     * @param {string} filename - 文件名
     */
    downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = Utils.DOMUtils.createElement('a', {
            href: url,
            download: filename,
            style: 'display: none;'
        });
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// 创建全局UI组件实例
window.UIComponents = UIComponents;
