/**
 * 工具函数集合
 * 提供通用的实用函数，包括日期格式化、文件处理、数据验证等
 */

// ===== 日期和时间工具 =====
const DateUtils = {
    /**
     * 格式化日期时间
     * @param {Date|string} date - 日期对象或字符串
     * @param {string} format - 格式模板 (YYYY-MM-DD HH:mm:ss)
     * @returns {string} 格式化后的日期字符串
     */
    format(date, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!date) return '';
        
        const d = new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },
    
    /**
     * 获取相对时间描述
     * @param {Date|string} date - 日期
     * @returns {string} 相对时间描述
     */
    getRelativeTime(date) {
        if (!date) return '';
        
        const now = new Date();
        const target = new Date(date);
        const diff = now - target;
        
        const minute = 60 * 1000;
        const hour = minute * 60;
        const day = hour * 24;
        const week = day * 7;
        const month = day * 30;
        const year = day * 365;
        
        if (diff < minute) return '刚刚';
        if (diff < hour) return `${Math.floor(diff / minute)}分钟前`;
        if (diff < day) return `${Math.floor(diff / hour)}小时前`;
        if (diff < week) return `${Math.floor(diff / day)}天前`;
        if (diff < month) return `${Math.floor(diff / week)}周前`;
        if (diff < year) return `${Math.floor(diff / month)}个月前`;
        return `${Math.floor(diff / year)}年前`;
    },
    
    /**
     * 计算持续时间
     * @param {Date|string} startDate - 开始时间
     * @param {Date|string} endDate - 结束时间
     * @returns {string} 持续时间描述
     */
    getDuration(startDate, endDate = new Date()) {
        if (!startDate) return '';
        
        const start = new Date(startDate);
        const end = new Date(endDate);
        const diff = end - start;
        
        if (diff < 0) return '0秒';
        
        const seconds = Math.floor(diff / 1000) % 60;
        const minutes = Math.floor(diff / (1000 * 60)) % 60;
        const hours = Math.floor(diff / (1000 * 60 * 60)) % 24;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days > 0) return `${days}天${hours}小时${minutes}分钟`;
        if (hours > 0) return `${hours}小时${minutes}分钟`;
        if (minutes > 0) return `${minutes}分钟${seconds}秒`;
        return `${seconds}秒`;
    }
};

// ===== 文件处理工具 =====
const FileUtils = {
    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string} 格式化后的文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    },
    
    /**
     * 获取文件扩展名
     * @param {string} filename - 文件名
     * @returns {string} 文件扩展名
     */
    getFileExtension(filename) {
        if (!filename) return '';
        return filename.split('.').pop().toLowerCase();
    },
    
    /**
     * 验证文件类型
     * @param {File} file - 文件对象
     * @param {string[]} allowedTypes - 允许的文件类型
     * @returns {boolean} 是否为允许的文件类型
     */
    validateFileType(file, allowedTypes = ['.xlsx', '.xls']) {
        if (!file) return false;
        const extension = this.getFileExtension(file.name);
        return allowedTypes.some(type => type.toLowerCase().includes(extension));
    },
    
    /**
     * 验证文件大小
     * @param {File} file - 文件对象
     * @param {number} maxSizeMB - 最大文件大小(MB)
     * @returns {boolean} 是否符合大小限制
     */
    validateFileSize(file, maxSizeMB = 100) {
        if (!file) return false;
        return file.size <= maxSizeMB * 1024 * 1024;
    },
    
    /**
     * 读取文件内容
     * @param {File} file - 文件对象
     * @param {string} readAs - 读取方式 ('text', 'dataURL', 'arrayBuffer')
     * @returns {Promise<string|ArrayBuffer>} 文件内容
     */
    readFile(file, readAs = 'arrayBuffer') {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            
            switch (readAs) {
                case 'text':
                    reader.readAsText(file);
                    break;
                case 'dataURL':
                    reader.readAsDataURL(file);
                    break;
                case 'arrayBuffer':
                default:
                    reader.readAsArrayBuffer(file);
                    break;
            }
        });
    }
};

// ===== DOM 操作工具 =====
const DOMUtils = {
    /**
     * 安全地获取DOM元素
     * @param {string} selector - CSS选择器
     * @param {Element} parent - 父元素
     * @returns {Element|null} DOM元素
     */
    $(selector, parent = document) {
        return parent.querySelector(selector);
    },
    
    /**
     * 获取多个DOM元素
     * @param {string} selector - CSS选择器
     * @param {Element} parent - 父元素
     * @returns {NodeList} DOM元素列表
     */
    $$(selector, parent = document) {
        return parent.querySelectorAll(selector);
    },
    
    /**
     * 创建DOM元素
     * @param {string} tag - 标签名
     * @param {Object} attributes - 属性对象
     * @param {string} content - 内容
     * @returns {Element} 创建的元素
     */
    createElement(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else if (key === 'textContent') {
                element.textContent = value;
            } else {
                element.setAttribute(key, value);
            }
        });
        
        if (content) {
            element.innerHTML = content;
        }
        
        return element;
    },
    
    /**
     * 添加事件监听器
     * @param {Element|string} element - DOM元素或选择器
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     * @param {boolean} useCapture - 是否使用捕获
     */
    on(element, event, handler, useCapture = false) {
        const el = typeof element === 'string' ? this.$(element) : element;
        if (el) {
            el.addEventListener(event, handler, useCapture);
        }
    },
    
    /**
     * 移除事件监听器
     * @param {Element|string} element - DOM元素或选择器
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     */
    off(element, event, handler) {
        const el = typeof element === 'string' ? this.$(element) : element;
        if (el) {
            el.removeEventListener(event, handler);
        }
    },
    
    /**
     * 显示/隐藏元素
     * @param {Element|string} element - DOM元素或选择器
     * @param {boolean} show - 是否显示
     */
    toggle(element, show = null) {
        const el = typeof element === 'string' ? this.$(element) : element;
        if (!el) return;
        
        if (show === null) {
            el.classList.toggle('hidden');
        } else {
            el.classList.toggle('hidden', !show);
        }
    },
    
    /**
     * 平滑滚动到元素
     * @param {Element|string} element - 目标元素或选择器
     * @param {Object} options - 滚动选项
     */
    scrollTo(element, options = {}) {
        const el = typeof element === 'string' ? this.$(element) : element;
        if (el) {
            el.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest',
                ...options
            });
        }
    }
};

// ===== 数据处理工具 =====
const DataUtils = {
    /**
     * 深度克隆对象
     * @param {any} obj - 要克隆的对象
     * @returns {any} 克隆后的对象
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            Object.keys(obj).forEach(key => {
                cloned[key] = this.deepClone(obj[key]);
            });
            return cloned;
        }
        return obj;
    },
    
    /**
     * 防抖函数
     * @param {Function} func - 要防抖的函数
     * @param {number} wait - 等待时间(ms)
     * @returns {Function} 防抖后的函数
     */
    debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * 节流函数
     * @param {Function} func - 要节流的函数
     * @param {number} limit - 时间限制(ms)
     * @returns {Function} 节流后的函数
     */
    throttle(func, limit = 300) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    /**
     * 生成唯一ID
     * @param {string} prefix - 前缀
     * @returns {string} 唯一ID
     */
    generateId(prefix = 'id') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },
    
    /**
     * 过滤和搜索数组
     * @param {Array} array - 要搜索的数组
     * @param {string} query - 搜索关键词
     * @param {string[]} fields - 要搜索的字段
     * @returns {Array} 过滤后的数组
     */
    filterArray(array, query, fields = []) {
        if (!query || !array.length) return array;
        
        const lowerQuery = query.toLowerCase();
        return array.filter(item => {
            if (fields.length === 0) {
                // 如果没有指定字段，搜索所有字符串值
                return Object.values(item).some(value => 
                    String(value).toLowerCase().includes(lowerQuery)
                );
            } else {
                // 搜索指定字段
                return fields.some(field => 
                    String(item[field] || '').toLowerCase().includes(lowerQuery)
                );
            }
        });
    },
    
    /**
     * 数组排序
     * @param {Array} array - 要排序的数组
     * @param {string} key - 排序字段
     * @param {string} order - 排序方向 ('asc' | 'desc')
     * @returns {Array} 排序后的数组
     */
    sortArray(array, key, order = 'asc') {
        return [...array].sort((a, b) => {
            const aVal = a[key];
            const bVal = b[key];
            
            if (aVal < bVal) return order === 'asc' ? -1 : 1;
            if (aVal > bVal) return order === 'asc' ? 1 : -1;
            return 0;
        });
    }
};

// ===== 存储工具 =====
const StorageUtils = {
    /**
     * 设置本地存储
     * @param {string} key - 键名
     * @param {any} value - 值
     * @param {boolean} session - 是否使用sessionStorage
     */
    set(key, value, session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            storage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('Storage set error:', error);
        }
    },
    
    /**
     * 获取本地存储
     * @param {string} key - 键名
     * @param {any} defaultValue - 默认值
     * @param {boolean} session - 是否使用sessionStorage
     * @returns {any} 存储的值
     */
    get(key, defaultValue = null, session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            const item = storage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Storage get error:', error);
            return defaultValue;
        }
    },
    
    /**
     * 移除本地存储
     * @param {string} key - 键名
     * @param {boolean} session - 是否使用sessionStorage
     */
    remove(key, session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            storage.removeItem(key);
        } catch (error) {
            console.error('Storage remove error:', error);
        }
    },
    
    /**
     * 清空本地存储
     * @param {boolean} session - 是否使用sessionStorage
     */
    clear(session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            storage.clear();
        } catch (error) {
            console.error('Storage clear error:', error);
        }
    }
};

// ===== 验证工具 =====
const ValidationUtils = {
    /**
     * 验证邮箱格式
     * @param {string} email - 邮箱地址
     * @returns {boolean} 是否有效
     */
    isEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    },
    
    /**
     * 验证手机号格式
     * @param {string} phone - 手机号
     * @returns {boolean} 是否有效
     */
    isPhone(phone) {
        const regex = /^1[3-9]\d{9}$/;
        return regex.test(phone);
    },
    
    /**
     * 验证密码强度
     * @param {string} password - 密码
     * @returns {Object} 验证结果
     */
    validatePassword(password) {
        const result = {
            valid: true,
            score: 0,
            errors: []
        };
        
        if (!password || password.length < 6) {
            result.valid = false;
            result.errors.push('密码长度至少6位');
        } else {
            result.score += 1;
        }
        
        if (!/[a-z]/.test(password)) {
            result.errors.push('密码应包含小写字母');
        } else {
            result.score += 1;
        }
        
        if (!/[A-Z]/.test(password)) {
            result.errors.push('密码应包含大写字母');
        } else {
            result.score += 1;
        }
        
        if (!/\d/.test(password)) {
            result.errors.push('密码应包含数字');
        } else {
            result.score += 1;
        }
        
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
            result.errors.push('密码应包含特殊字符');
        } else {
            result.score += 1;
        }
        
        if (result.errors.length > 0) {
            result.valid = false;
        }
        
        return result;
    }
};

// ===== URL工具 =====
const URLUtils = {
    /**
     * 获取URL参数
     * @param {string} name - 参数名
     * @param {string} url - URL地址
     * @returns {string|null} 参数值
     */
    getParam(name, url = window.location.href) {
        const urlObj = new URL(url);
        return urlObj.searchParams.get(name);
    },
    
    /**
     * 设置URL参数
     * @param {string} name - 参数名
     * @param {string} value - 参数值
     * @param {boolean} replace - 是否替换历史记录
     */
    setParam(name, value, replace = false) {
        const url = new URL(window.location.href);
        url.searchParams.set(name, value);
        
        if (replace) {
            window.history.replaceState({}, '', url.toString());
        } else {
            window.history.pushState({}, '', url.toString());
        }
    },
    
    /**
     * 移除URL参数
     * @param {string} name - 参数名
     * @param {boolean} replace - 是否替换历史记录
     */
    removeParam(name, replace = false) {
        const url = new URL(window.location.href);
        url.searchParams.delete(name);
        
        if (replace) {
            window.history.replaceState({}, '', url.toString());
        } else {
            window.history.pushState({}, '', url.toString());
        }
    }
};

// 导出所有工具函数
window.Utils = {
    DateUtils,
    FileUtils,
    DOMUtils,
    DataUtils,
    StorageUtils,
    ValidationUtils,
    URLUtils
};
