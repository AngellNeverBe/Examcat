/**
 * AJAX页面动态加载导航器（增强版，带详细日志）
 */
class AjaxNavigator {
    constructor(options = {}) {
        // 默认配置
        this.config = {
            contentSelector: '#ajax-content',
            linkSelector: '.ajax-nav-link',
            formSelector: 'form',
            loadingClass: 'ajax-loading',
            errorClass: 'ajax-error',
            ...options
        };
        
        // 存储事件监听器引用，便于后续移除
        this.eventListeners = new Map();
        this.isInitialized = false;
        
        // 资源追踪系统
        this.resourceTracker = {
            // 记录每个页面加载的资源 {page: {styles: Set, scripts: Set}}
            pageResources: new Map(),
            // 当前激活的页面
            currentPage: null,
            // 全局资源（来自base.html）不应该被禁用
            globalResources: {
                styles: new Set([
                    '/static/css/sakura.css',
                    '/static/css/base_auth.css',
                    '/static/css/style.css',
                    '/static/css/base.css',
                    '/static/css/cursors.css',
                    '/static/css/ajax_navigator.css',
                    '/ajax/libs/artalk/2.9.1/Artalk.css'
                ]),
                scripts: new Set([
                    '/static/js/sakura.js',
                    '/static/js/base_auth.js',
                    '/static/js/base.js',
                    '/static/js/ajax_navigator.js',
                    '/static/js/ajax_nav_activator.js',
                    '/static/js/index.js',
                    '/npm/live2d-widgets@1.0.0/dist/autoload.js',
                    '/ajax/libs/artalk/2.9.1/Artalk.js',
                    '/static/js/artalk-manager.js'
                ])
            },
            // 资源日志开关
            loggingEnabled: true
        };
        
        // 初始化
        this.init();
    }
    
    /**
     * 初始化方法
     */
    init() {
        if (this.isInitialized) {
            this.logResource('info', 'AjaxNavigator: 已经初始化，跳过重复初始化');
            return;
        }
        
        this.logResource('info', 'AjaxNavigator: 初始化中...');
        
        // 清理可能存在的旧事件监听器
        this.cleanupEventListeners();
        
        // 拦截链接点击
        this.setupLinkInterception();
        
        // 拦截浏览器后退/前进
        this.setupPopState();
        
        // 确保所有必要的元素都存在
        this.ensureContentElement();
        
        // 记录初始页面资源
        this.recordInitialPageResources();
        
        this.isInitialized = true;
        this.logResource('info', 'AjaxNavigator: 初始化完成');
    }
    
    /**
     * 清理事件监听器
     */
    cleanupEventListeners() {
        // 清理所有存储的事件监听器
        this.eventListeners.forEach((listener, eventName) => {
            window.removeEventListener(eventName, listener);
        });
        this.eventListeners.clear();
    }
    
    /**
     * 确保内容元素存在
     */
    ensureContentElement() {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (!contentElement) {
            console.warn(`AjaxNavigator: 未找到内容元素 ${this.config.contentSelector}`);
            return false;
        }
        return true;
    }
    
    /**
     * 记录初始页面资源
     */
    recordInitialPageResources() {
        this.logResource('info', '开始记录初始页面资源');
        
        // 检测当前页面类型
        const pathname = window.location.pathname;
        let pageName = 'index'; // 默认页面
        
        // 根据URL路径判断页面类型
        if (pathname.includes('/exams/') && /\d+$/.test(pathname)) {
            // 考试页面
            const match = pathname.match(/\/exams\/(\d+)/);
            if (match) {
                pageName = `exam-${match[1]}`;
            }
        } else if (pathname.includes('/banks')) {
            pageName = 'banks';
        } else if (pathname.includes('/user')) {
            pageName = 'user';
        } else if (pathname.includes('/question') || pathname.includes('/questions')) {
            pageName = 'question';
        }
        
        this.logResource('info', `检测到初始页面: ${pageName} (路径: ${pathname})`);
        
        // 收集当前页面加载的资源
        const styles = [];
        const scripts = [];
        
        // 收集页面特定的CSS
        const cssLinks = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
        cssLinks.forEach(link => {
            const href = link.href;
            // 跳过第三方资源
            if (href.includes('googleapis.com') || href.includes('cdnjs.cloudflare.com') || href.includes('fastly.jsdelivr.net')) {
                return;
            }
            // 跳过全局资源
            if (this.resourceTracker.globalResources.styles.has(new URL(href, window.location.origin).pathname)) {
                return;
            }
            styles.push(href);
        });
        
        // 收集页面特定的JS
        const jsScripts = Array.from(document.querySelectorAll('script[src]'));
        jsScripts.forEach(script => {
            const src = script.src;
            // 跳过第三方资源
            if (src.includes('cdnjs.cloudflare.com') || src.includes('fastly.jsdelivr.net')) {
                return;
            }
            // 跳过全局资源
            if (this.resourceTracker.globalResources.scripts.has(new URL(src, window.location.origin).pathname)) {
                return;
            }
            scripts.push(src);
        });
        
        // 记录初始页面资源
        this.recordPageResources(pageName, styles, scripts);
        this.resourceTracker.currentPage = pageName;
        
        this.logResource('info', `初始页面 ${pageName} 资源记录完成: ${styles.length} CSS, ${scripts.length} JS`);
    }

    /**
     * 设置链接点击拦截（使用单一事件委托）
     */
    setupLinkInterception() {
        // 创建单一的事件处理函数
        const clickHandler = (e) => {
            // 查找被点击的链接
            let target = e.target;
            
            // 向上查找符合条件的链接元素
            while (target && target !== document.documentElement) {
                if (target.matches && target.matches(this.config.linkSelector)) {
                    e.preventDefault();
                    e.stopPropagation(); // 阻止事件冒泡
                    e.stopImmediatePropagation(); // 阻止其他事件监听器
                    
                    // 添加防抖机制，防止快速连续点击
                    if (this.lastClickTime && Date.now() - this.lastClickTime < 500) {
                        // console.log('AjaxNavigator: 点击过于频繁，忽略');
                        return;
                    }
                    this.lastClickTime = Date.now();
                    
                    this.handleLinkClick(target);
                    return;
                }
                target = target.parentNode;
            }
        };
        
        // 添加事件监听器并存储引用
        document.addEventListener('click', clickHandler, true); // 使用捕获阶段
        this.eventListeners.set('click', clickHandler);
    }
    
    /**
     * 处理链接点击
     * @param {HTMLElement} link - 被点击的链接元素
     */
    handleLinkClick(link) {
        const url = link.getAttribute('href');
        const page = link.getAttribute('data-page');
        
        if (!url) {
            console.error('AjaxNavigator: 链接缺少href属性');
            return;
        }
        
        // 如果是当前页面，忽略
        if (window.location.pathname === url) {
            // console.log('AjaxNavigator: 已经是当前页面，忽略');
            return;
        }
        
        // console.log(`AjaxNavigator: 加载页面 ${url} (${page})`);
        
        // 开始加载
        this.startLoading();
        
        // 请求新页面内容
        this.loadPage(url, page)
            .then(() => {
                // console.log(`AjaxNavigator: 页面 ${url} 加载完成`);
                this.lastClickTime = 0; // 重置防抖计时
            })
            .catch((error) => {
                console.error('AjaxNavigator: 页面加载失败:', error);
                this.showError('页面加载失败，请重试');
                this.lastClickTime = 0; // 重置防抖计时
            })
            .finally(() => {
                this.stopLoading();
            });
    }
    
    /**
     * 加载页面内容
     * @param {string} url - 请求的URL
     * @param {string} page - 页面标识（可选）
     * @returns {Promise} 加载Promise
     */
    async loadPage(url, page = null) {
        try {

            // 解析原始URL（包含查询参数）
            const urlObj = new URL(url, window.location.origin);
            const pathname = urlObj.pathname;
            const searchParams = new URLSearchParams(urlObj.search);
            const mode = searchParams.get('mode') || 'other';
            
            // 匹配题目页路径
            const questionMatch = pathname.match(/\/questions\/(\d+)/);
            
            if (questionMatch) {
                const [, qid] = questionMatch;
                
                // 构造新的AJAX URL，包含mode参数
                const ajaxUrl = `/ajax/question-${qid}?mode=${encodeURIComponent(mode)}`;
                
                url = ajaxUrl;
                // console.log(`AjaxNavigator: 重写URL，保留mode参数: ${url}`);
            }
            
            // 匹配考试页路径
            const examMatch = pathname.match(/\/exams\/(\d+)/);
            
            if (examMatch) {
                const [, examId] = examMatch;
                
                // 构造新的AJAX URL
                const ajaxUrl = `/ajax/exam-${examId}`;
                
                url = ajaxUrl;
                // console.log(`AjaxNavigator: 重写考试URL: ${url}`);
            }
            // 设置自定义请求头
            const headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'X-Ajax-Navigation': 'true',
                'Accept': 'application/json, text/html'
            };
            // console.log('发送请求头:', headers);
            // 发送请求
            const response = await fetch(url, { headers });
            
            // console.log(`收到响应: 状态码 ${response.status}, content-type: ${response.headers.get('content-type')}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // 淡出旧内容
            await this.fadeOutContent();
            
            // 处理响应
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                // console.log('✅ JSON 分支');
                const data = await response.json();
                // console.log('接收到的 JSON 数据:', data);
                
                if (!data.success) {
                    throw new Error(data.error || '页面加载失败');
                }

                // 停止加载
                this.stopLoading();
                
                // 更新内容
                await this.updateContentWithResources(data);
                
                // 更新历史记录
                this.updateHistory(url, page || data.page);
                
            } else {
                // console.log('❌ HTML 分支');
                const html = await response.text();
                // console.log('响应文本前 300 个字符:', html.substring(0, 300));
                
                // 停止加载
                this.stopLoading();
                
                // 更新内容
                const content = this.extractContentFromHtml(html, page);
                await this.updateContent(content);
                
                this.updateHistory(url, page);
                this.updateTitle(html);
            }
            
            this.triggerEvent('ajax:navigation:complete', { url, page });
            return true;
            
        } catch (error) {
            this.stopLoading();
            this.showError('页面加载失败，请重试');
            this.triggerEvent('ajax:navigation:error', { url, page, error });
            throw error;
        }
    }
    
    /**
     * 资源日志记录器
     * @param {string} level - 日志级别 (info, warn, error)
     * @param {string} message - 日志消息
     */
    logResource(level, message) {
        if (!this.resourceTracker.loggingEnabled) return;
        
        const timestamp = new Date().toISOString().substr(11, 8);
        const prefix = `[ResourceTracker:${timestamp}]`;
        
        switch(level) {
            case 'info':
                console.log(`${prefix} ${message}`);
                break;
            case 'warn':
                console.warn(`${prefix} ${message}`);
                break;
            case 'error':
                console.error(`${prefix} ${message}`);
                break;
            default:
                console.log(`${prefix} ${message}`);
        }
    }

    /**
     * 禁用指定页面的资源
     * @param {string} pageName - 页面名称
     */
    disablePageResources(pageName) {
        if (!pageName || !this.resourceTracker.pageResources.has(pageName)) {
            this.logResource('info', `没有找到页面 ${pageName} 的资源记录，无需禁用`);
            return;
        }

        const pageResources = this.resourceTracker.pageResources.get(pageName);
        this.logResource('info', `开始禁用页面 ${pageName} 的资源`);
        
        // 标准化URL辅助函数
        const normalizeUrl = (inputUrl) => {
            try {
                const urlObj = new URL(inputUrl, window.location.origin);
                return urlObj.pathname;
            } catch {
                return inputUrl;
            }
        };

        // 禁用CSS资源
        pageResources.styles.forEach(cssUrl => {
            // 跳过全局资源
            if (this.resourceTracker.globalResources.styles.has(cssUrl)) {
                this.logResource('info', `跳过全局CSS: ${cssUrl}`);
                return;
            }
            
            const targetPathname = normalizeUrl(cssUrl);
            const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            
            const matchingLinks = links.filter(link => {
                try {
                    const linkUrl = new URL(link.href, window.location.origin);
                    return normalizeUrl(linkUrl.pathname) === targetPathname;
                } catch {
                    return link.href.includes(targetPathname);
                }
            });
            
            matchingLinks.forEach(link => {
                if (!link.disabled) {
                    link.disabled = true;
                    this.logResource('info', `已禁用CSS: ${cssUrl}`);
                }
            });
        });

        // 禁用JS资源（通过禁用脚本标签或移除执行环境）
        pageResources.scripts.forEach(jsUrl => {
            // 跳过全局资源
            if (this.resourceTracker.globalResources.scripts.has(jsUrl)) {
                this.logResource('info', `跳过全局JS: ${jsUrl}`);
                return;
            }
            
            const targetPathname = normalizeUrl(jsUrl);
            const scripts = Array.from(document.querySelectorAll('script[src]'));
            
            const matchingScripts = scripts.filter(script => {
                try {
                    const scriptUrl = new URL(script.src, window.location.origin);
                    return normalizeUrl(scriptUrl.pathname) === targetPathname;
                } catch {
                    return script.src.includes(targetPathname);
                }
            });
            
            // 标记JS脚本为已禁用（物理移除比较危险，采用标记方式）
            matchingScripts.forEach(script => {
                script.dataset.resourceDisabled = 'true';
                this.logResource('info', `已标记JS为禁用: ${jsUrl}`);
            });
        });

        this.logResource('info', `页面 ${pageName} 的资源禁用完成`);
    }

    /**
     * 启用指定页面的资源
     * @param {string} pageName - 页面名称
     */
    enablePageResources(pageName) {
        if (!pageName || !this.resourceTracker.pageResources.has(pageName)) {
            this.logResource('info', `没有找到页面 ${pageName} 的资源记录，无需启用`);
            return;
        }

        const pageResources = this.resourceTracker.pageResources.get(pageName);
        this.logResource('info', `开始启用页面 ${pageName} 的资源`);
        
        // 标准化URL辅助函数
        const normalizeUrl = (inputUrl) => {
            try {
                const urlObj = new URL(inputUrl, window.location.origin);
                return urlObj.pathname;
            } catch {
                return inputUrl;
            }
        };

        // 启用CSS资源
        pageResources.styles.forEach(cssUrl => {
            const targetPathname = normalizeUrl(cssUrl);
            const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            
            const matchingLinks = links.filter(link => {
                try {
                    const linkUrl = new URL(link.href, window.location.origin);
                    return normalizeUrl(linkUrl.pathname) === targetPathname;
                } catch {
                    return link.href.includes(targetPathname);
                }
            });
            
            matchingLinks.forEach(link => {
                if (link.disabled) {
                    link.disabled = false;
                    this.logResource('info', `已启用CSS: ${cssUrl}`);
                }
            });
        });

        // 启用JS资源
        pageResources.scripts.forEach(jsUrl => {
            const targetPathname = normalizeUrl(jsUrl);
            const scripts = Array.from(document.querySelectorAll('script[src]'));
            
            const matchingScripts = scripts.filter(script => {
                try {
                    const scriptUrl = new URL(script.src, window.location.origin);
                    return normalizeUrl(scriptUrl.pathname) === targetPathname;
                } catch {
                    return script.src.includes(targetPathname);
                }
            });
            
            matchingScripts.forEach(script => {
                if (script.dataset.resourceDisabled === 'true') {
                    delete script.dataset.resourceDisabled;
                    this.logResource('info', `已移除JS禁用标记: ${jsUrl}`);
                }
            });
        });

        this.logResource('info', `页面 ${pageName} 的资源启用完成`);
    }

    /**
     * 记录页面资源
     * @param {string} pageName - 页面名称
     * @param {Array} styles - CSS文件列表
     * @param {Array} scripts - JS文件列表
     */
    recordPageResources(pageName, styles = [], scripts = []) {
        if (!pageName) {
            this.logResource('error', '无法记录资源：缺少页面名称');
            return;
        }

        // 标准化URL（移除查询参数和哈希）
        const normalizeUrl = (url) => {
            try {
                const urlObj = new URL(url, window.location.origin);
                return urlObj.pathname;
            } catch {
                return url;
            }
        };

        const normalizedStyles = styles.map(normalizeUrl);
        const normalizedScripts = scripts.map(normalizeUrl);

        // 记录资源
        if (!this.resourceTracker.pageResources.has(pageName)) {
            this.resourceTracker.pageResources.set(pageName, {
                styles: new Set(),
                scripts: new Set()
            });
        }

        const pageResources = this.resourceTracker.pageResources.get(pageName);
        
        normalizedStyles.forEach(style => {
            pageResources.styles.add(style);
            this.logResource('info', `记录页面 ${pageName} 的CSS: ${style}`);
        });

        normalizedScripts.forEach(script => {
            pageResources.scripts.add(script);
            this.logResource('info', `记录页面 ${pageName} 的JS: ${script}`);
        });

        this.logResource('info', `页面 ${pageName} 资源记录完成，共 ${normalizedStyles.length} 个CSS，${normalizedScripts.length} 个JS`);
    }

    async updateContentWithResources(data) {
        this.logResource('info', `updateContentWithResources 被调用，页面: ${data.page}`);
        const contentElement = document.querySelector(this.config.contentSelector);
        if (!contentElement) {
            console.error('找不到内容元素:', this.config.contentSelector);
            return;
        }
        
        // 第一步：禁用当前页面的资源
        if (this.resourceTracker.currentPage) {
            this.logResource('info', `禁用旧页面资源: ${this.resourceTracker.currentPage}`);
            this.disablePageResources(this.resourceTracker.currentPage);
        }
        
        // 第二步：加载和启用新CSS资源（在HTML更新前）
        this.logResource('info', `准备加载CSS资源, styles: ${data.styles.length}`);
        try {
            await this.loadCSSResources(data.styles);
            this.logResource('info', 'CSS资源加载完成');
        } catch (cssError) {
            this.logResource('error', `CSS资源加载失败: ${cssError.message}`);
            // 继续执行，避免CSS加载失败阻塞页面更新
        }
        
        // 记录新页面的资源（在HTML更新前记录，确保资源追踪正确）
        this.logResource('info', `记录新页面资源: ${data.page}`);
        this.recordPageResources(data.page, data.styles, data.scripts);
        
        // 第三步：更新HTML内容（此时CSS已加载，避免无样式闪烁）
        contentElement.innerHTML = data.html;
        this.logResource('info', 'HTML 已更新');
        
        // 第四步：加载和启用新JS资源（在HTML更新后）
        this.logResource('info', `准备加载JS资源, scripts: ${data.scripts.length}`);
        try {
            await this.loadJSResources(data.scripts);
            this.logResource('info', 'JS资源加载完成');
        } catch (jsError) {
            this.logResource('error', `JS资源加载失败: ${jsError.message}`);
            // 继续执行，JS加载失败不影响基本功能
        }
        
        // 第五步：确保新页面的所有资源都已启用
        this.logResource('info', `启用新页面资源: ${data.page}`);
        this.enablePageResources(data.page);
        
        // 更新当前页面
        this.resourceTracker.currentPage = data.page;
        
        // 重新初始化页面功能（在资源加载完成后）
        this.reinitializePageContent();
        
        // 更新标题
        if (data.title) {
            document.title = data.title;
        }
        
        // 淡入新内容
        await this.fadeInContent(contentElement);
        
        // 更新完成后传递页面标识
        this.triggerEvent('ajax:page:updated', { page: data.page });
        
        this.logResource('info', `页面 ${data.page} 更新完成`);
    }
    
    /**
     * 动态加载CSS和JS资源
     * @param {Array} styles - CSS文件列表
     * @param {Array} scripts - JS文件列表
     * @returns {Promise} 加载完成的Promise
     */
    async loadResources(styles = [], scripts = []) {
        this.logResource('info', `loadResources 被调用, styles: ${styles.length}, scripts: ${scripts.length}`);
        const promises = [];

        // 动态加载CSS - 总是调用loadCSS，它会处理已存在的情况
        styles.forEach(cssUrl => {
            this.logResource('info', `加载 CSS: ${cssUrl}`);
            promises.push(this.loadCSS(cssUrl));
        });

        // 动态加载JS - 总是调用loadJS，它会处理已存在的情况
        scripts.forEach(jsUrl => {
            this.logResource('info', `加载 JS: ${jsUrl}`);
            promises.push(this.loadJS(jsUrl));
        });

        // 等待所有资源加载完成
        return Promise.all(promises);
    }

    /**
     * 仅动态加载CSS资源
     * @param {Array} styles - CSS文件列表
     * @returns {Promise} 加载完成的Promise
     */
    async loadCSSResources(styles = []) {
        this.logResource('info', `loadCSSResources 被调用, styles: ${styles.length}`);
        const promises = [];

        // 动态加载CSS - 总是调用loadCSS，它会处理已存在的情况
        styles.forEach(cssUrl => {
            this.logResource('info', `加载 CSS: ${cssUrl}`);
            promises.push(this.loadCSS(cssUrl));
        });

        // 等待所有CSS加载完成
        return Promise.all(promises);
    }

    /**
     * 仅动态加载JS资源
     * @param {Array} scripts - JS文件列表
     * @returns {Promise} 加载完成的Promise
     */
    async loadJSResources(scripts = []) {
        this.logResource('info', `loadJSResources 被调用, scripts: ${scripts.length}`);
        const promises = [];

        // 动态加载JS - 总是调用loadJS，它会处理已存在的情况
        scripts.forEach(jsUrl => {
            this.logResource('info', `加载 JS: ${jsUrl}`);
            promises.push(this.loadJS(jsUrl));
        });

        // 等待所有JS加载完成
        return Promise.all(promises);
    }

    /**
     * 检查资源是否已加载
     * @param {string} url - 资源URL
     * @returns {boolean} 是否已加载
     */
    isResourceLoaded(url) {
        this.logResource('info', `检查资源是否已加载: ${url}`);
        
        // 标准化URL进行比较
        const normalizeUrl = (inputUrl) => {
            try {
                const urlObj = new URL(inputUrl, window.location.origin);
                return urlObj.pathname;
            } catch {
                return inputUrl;
            }
        };
        
        const normalizedUrl = normalizeUrl(url);
        
        // 检查CSS
        const cssLinks = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
        const cssExists = cssLinks.some(link => {
            try {
                const linkUrl = new URL(link.href, window.location.origin);
                return normalizeUrl(linkUrl.pathname) === normalizedUrl;
            } catch {
                return link.href.includes(normalizedUrl);
            }
        });
        
        if (cssExists) {
            this.logResource('info', `找到已加载的 CSS: ${url}`);
            return true;
        }
        
        // 检查JS
        const jsScripts = Array.from(document.querySelectorAll('script[src]'));
        const jsExists = jsScripts.some(script => {
            try {
                const scriptUrl = new URL(script.src, window.location.origin);
                return normalizeUrl(scriptUrl.pathname) === normalizedUrl;
            } catch {
                return script.src.includes(normalizedUrl);
            }
        });
        
        if (jsExists) {
            this.logResource('info', `找到已加载的 JS: ${url}`);
            return true;
        }
        
        this.logResource('info', `未找到已加载的资源: ${url}`);
        return false;
    }
    
    /**
     * 启用已存在的CSS资源
     * @param {string} url - CSS文件URL
     */
    enableExistingCSS(url) {
        // 标准化目标URL
        const normalizeUrl = (inputUrl) => {
            try {
                const urlObj = new URL(inputUrl, window.location.origin);
                return urlObj.pathname;
            } catch {
                return inputUrl;
            }
        };
        
        const targetPathname = normalizeUrl(url);
        const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
        
        const matchingLinks = links.filter(link => {
            try {
                const linkUrl = new URL(link.href, window.location.origin);
                return normalizeUrl(linkUrl.pathname) === targetPathname;
            } catch {
                return link.href.includes(targetPathname);
            }
        });
        
        matchingLinks.forEach(link => {
            if (link.disabled) {
                link.disabled = false;
                this.logResource('info', `已启用已存在的CSS: ${url}`);
            }
        });
    }

    /**
     * 启用已存在的JS资源
     * @param {string} url - JS文件URL
     */
    enableExistingJS(url) {
        // 标准化目标URL
        const normalizeUrl = (inputUrl) => {
            try {
                const urlObj = new URL(inputUrl, window.location.origin);
                return urlObj.pathname;
            } catch {
                return inputUrl;
            }
        };
        
        const targetPathname = normalizeUrl(url);
        const scripts = Array.from(document.querySelectorAll('script[src]'));
        
        const matchingScripts = scripts.filter(script => {
            try {
                const scriptUrl = new URL(script.src, window.location.origin);
                return normalizeUrl(scriptUrl.pathname) === targetPathname;
            } catch {
                return script.src.includes(targetPathname);
            }
        });
        
        matchingScripts.forEach(script => {
            if (script.dataset.resourceDisabled === 'true') {
                delete script.dataset.resourceDisabled;
                this.logResource('info', `已移除JS禁用标记: ${url}`);
            }
        });
    }

    /**
     * 动态加载CSS文件
     * @param {string} url - CSS文件URL
     * @returns {Promise} 加载完成的Promise
     */
    loadCSS(url) {
        this.logResource('info', `loadCSS 开始: ${url}`);
        return new Promise((resolve, reject) => {
            // 标准化目标URL
            const normalizeUrl = (inputUrl) => {
                try {
                    const urlObj = new URL(inputUrl, window.location.origin);
                    return urlObj.pathname;
                } catch {
                    return inputUrl;
                }
            };

            const targetPathname = normalizeUrl(url);

            // 检查是否已存在相同路径的CSS链接
            const existingLinks = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            const matchingLinks = existingLinks.filter(link => {
                try {
                    const linkUrl = new URL(link.href, window.location.origin);
                    return normalizeUrl(linkUrl.pathname) === targetPathname;
                } catch {
                    return link.href.includes(targetPathname);
                }
            });

            // 总是创建新的link元素，确保CSS完全加载
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = url;

            // 添加超时机制（5秒）
            const timeoutId = setTimeout(() => {
                this.logResource('error', `CSS 加载超时: ${url}`);
                reject(new Error(`CSS加载超时: ${url}`));
                // 移除链接元素，避免继续尝试加载
                if (link.parentNode) {
                    link.parentNode.removeChild(link);
                }
                // 也移除可能已经添加但未加载的旧链接
                matchingLinks.forEach(oldLink => {
                    if (oldLink.parentNode && oldLink !== link) {
                        oldLink.parentNode.removeChild(oldLink);
                    }
                });
            }, 5000);

            link.onload = () => {
                clearTimeout(timeoutId);
                this.logResource('info', `CSS 加载成功: ${url}`);

                // CSS加载成功后，移除旧的匹配链接（如果有）
                matchingLinks.forEach(oldLink => {
                    if (oldLink.parentNode && oldLink !== link) {
                        this.logResource('info', `移除旧的CSS链接: ${url}`);
                        oldLink.parentNode.removeChild(oldLink);
                    }
                });

                resolve();
            };
            link.onerror = () => {
                clearTimeout(timeoutId);
                this.logResource('error', `CSS 加载失败: ${url}`);

                // 加载失败时也移除新创建的链接
                if (link.parentNode) {
                    link.parentNode.removeChild(link);
                }

                reject(new Error(`CSS加载失败: ${url}`));
            };

            document.head.appendChild(link);
            this.logResource('info', `已添加新的CSS链接到DOM: ${url}`);
        });
    }
    
    /**
     * 动态加载JS文件
     * @param {string} url - JS文件URL
     * @returns {Promise} 加载完成的Promise
     */
    loadJS(url) {
        this.logResource('info', `loadJS 开始: ${url}`);
        return new Promise((resolve, reject) => {
            // 标准化目标URL
            const normalizeUrl = (inputUrl) => {
                try {
                    const urlObj = new URL(inputUrl, window.location.origin);
                    return urlObj.pathname;
                } catch {
                    return inputUrl;
                }
            };

            const targetPathname = normalizeUrl(url);

            // 检查是否已存在相同路径的JS脚本
            const existingScripts = Array.from(document.querySelectorAll('script[src]'));
            const matchingScripts = existingScripts.filter(script => {
                try {
                    const scriptUrl = new URL(script.src, window.location.origin);
                    return normalizeUrl(scriptUrl.pathname) === targetPathname;
                } catch {
                    return script.src.includes(targetPathname);
                }
            });

            // 检查是否有未被禁用的脚本
            const enabledScript = matchingScripts.find(script => !script.dataset.resourceDisabled);

            if (enabledScript) {
                // 已经有启用的脚本，不需要重新加载
                this.logResource('info', `JS 已存在且已启用，跳过: ${url}`);
                resolve();
                return;
            }

            // 创建新的script元素
            const script = document.createElement('script');
            script.src = url;

            // 添加超时机制（10秒，JS可能比CSS大）
            const timeoutId = setTimeout(() => {
                this.logResource('error', `JS 加载超时: ${url}`);
                reject(new Error(`JS加载超时: ${url}`));
                // 移除脚本元素，避免继续尝试加载
                if (script.parentNode) {
                    script.parentNode.removeChild(script);
                }
            }, 10000);

            script.onload = () => {
                clearTimeout(timeoutId);
                this.logResource('info', `JS 加载成功: ${url}`);

                // JS加载成功后，移除旧的被禁用的匹配脚本（如果有）
                matchingScripts.forEach(oldScript => {
                    if (oldScript.parentNode && oldScript !== script && oldScript.dataset.resourceDisabled === 'true') {
                        this.logResource('info', `移除旧的被禁用JS脚本: ${url}`);
                        oldScript.parentNode.removeChild(oldScript);
                    }
                });

                resolve();
            };
            script.onerror = () => {
                clearTimeout(timeoutId);
                this.logResource('error', `JS 加载失败: ${url}`);

                // 加载失败时也移除新创建的脚本
                if (script.parentNode) {
                    script.parentNode.removeChild(script);
                }

                reject(new Error(`JS加载失败: ${url}`));
            };

            document.body.appendChild(script);
            this.logResource('info', `已添加新的JS脚本到DOM: ${url}`);
        });
    }
    
    /**
     * 从HTML中提取内容
     * @param {string} html - 完整的HTML字符串
     * @param {string} page - 页面标识
     * @returns {string} 提取的内容
     */
    extractContentFromHtml(html, page) {
        // 创建临时DOM元素来解析HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 尝试多种方式提取内容
        let content = '';
        
        // 方式1：如果有指定的内容区域，提取它
        const contentElement = doc.querySelector(this.config.contentSelector);
        if (contentElement) {
            content = contentElement.innerHTML;
        } 
        // 方式2：尝试提取ajax-content
        else {
            const authContent = doc.querySelector('#ajax-content');
            if (authContent) {
                content = authContent.innerHTML;
            }
            // 方式3：提取主内容区域
            else {
                const mainContent = doc.querySelector('main, .main-content, .content');
                if (mainContent) {
                    content = mainContent.innerHTML;
                }
                // 方式4：如果没有找到，提取整个body的内容（排除脚本等）
                else {
                    const bodyContent = doc.body.innerHTML;
                    // 移除脚本标签
                    content = bodyContent.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
                }
            }
        }
        
        return content;
    }
    
    /**
     * 更新页面内容
     * @param {string} content - 新的HTML内容
     */
    async updateContent(content) {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (!contentElement) return;
        
        // 更新内容
        contentElement.innerHTML = content;
        
        // 重新初始化页面功能
        this.reinitializePageContent();
        
        // 淡入新内容
        await this.fadeInContent(contentElement);
    }
    
    /**
     * 淡出内容
     * @param {HTMLElement} element - 要淡出的元素
     * @returns {Promise} 动画完成的Promise
     */
    async fadeOutContent() {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (!contentElement) return Promise.resolve();
        
        return new Promise((resolve) => {
            contentElement.style.opacity = '0';
            contentElement.style.transition = 'opacity 0.3s ease';
            
            setTimeout(() => {
                resolve();
            }, 300);
        });
    }
    
    /**
     * 淡入内容
     * @param {HTMLElement} element - 要淡入的元素
     * @returns {Promise} 动画完成的Promise
     */
    async fadeInContent(element) {
        return new Promise((resolve) => {
            element.offsetHeight; // 强制重排
            element.style.opacity = '1';
            
            setTimeout(() => {
                element.style.transition = '';
                resolve();
            }, 300);
        });
    }
    
    /**
     * 重新初始化页面内容（不重新绑定链接事件）
     */
    reinitializePageContent() {
        // console.log('AjaxNavigator: 重新初始化页面内容...');
        
        // 重新绑定表单提交事件（需要）
        this.rebindForms();
        
        // 重新绑定页面特定的JavaScript
        this.rebindPageScripts();
        
        // 触发自定义事件，让其他脚本知道页面已更新
        this.triggerEvent('ajax:page:updated');
    }
    
    /**
     * 重新绑定表单提交事件
     */
    rebindForms() {
        const forms = document.querySelectorAll(this.config.formSelector);
        
        forms.forEach(form => {
            // 为每个表单生成唯一ID，避免重复绑定
            if (!form.dataset.ajaxBound) {
                form.dataset.ajaxBound = 'true';
                
                // 查找提交按钮
                const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
                
                submitButtons.forEach(button => {
                    // 确保按钮有唯一标识
                    if (!button.dataset.ajaxBound) {
                        button.dataset.ajaxBound = 'true';
                    }
                });
            }
        });
    }
    
    /**
     * 重新绑定页面特定的JavaScript
     */
    rebindPageScripts() {
        // 触发全局事件，让其他脚本知道可以重新初始化
        window.dispatchEvent(new CustomEvent('page:content:updated'));
    }
    
    /**
     * 更新浏览器历史记录
     * @param {string} url - 新的URL
     * @param {string} page - 页面标识
     */
    updateHistory(url, page) {
        // 更新浏览器URL（不刷新页面）
        window.history.pushState({ 
            url: url, 
            page: page,
            timestamp: Date.now()
        }, '', url);
    }
    
    /**
     * 更新页面标题
     * @param {string} html - HTML字符串
     */
    updateTitle(html) {
        // 从HTML中提取title标签
        const titleMatch = html.match(/<title>(.*?)<\/title>/i);
        if (titleMatch && titleMatch[1]) {
            document.title = titleMatch[1];
        }
    }
    
    /**
     * 设置popstate事件监听（处理浏览器后退/前进）
     */
    setupPopState() {
        const popStateHandler = (event) => {
            if (event.state && event.state.url) {
                // console.log('AjaxNavigator: 处理popstate，URL:', event.state.url);
                
                // 防抖处理
                if (this.popstateTimeout) {
                    clearTimeout(this.popstateTimeout);
                }
                
                this.popstateTimeout = setTimeout(() => {
                    // 加载历史记录中的页面
                    this.startLoading();
                    this.loadPage(event.state.url, event.state.page)
                        .catch(error => {
                            console.error('AjaxNavigator: 历史记录加载失败:', error);
                            // 如果AJAX加载失败，回退到传统导航
                            window.location.href = event.state.url;
                        })
                        .finally(() => {
                            this.stopLoading();
                        });
                }, 100);
            }
        };
        
        window.addEventListener('popstate', popStateHandler);
        this.eventListeners.set('popstate', popStateHandler);
    }
    
    /**
     * 显示加载状态
     */
    startLoading() {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (contentElement) {
            contentElement.classList.add(this.config.loadingClass);
        }
        
        // 触发事件
        this.triggerEvent('ajax:navigation:start');
    }
    
    /**
     * 停止加载状态
     */
    stopLoading() {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (contentElement) {
            contentElement.classList.remove(this.config.loadingClass);
        }
        
        // 触发事件
        this.triggerEvent('ajax:navigation:end');
    }
    
    /**
     * 显示错误信息
     * @param {string} message - 错误消息
     */
    showError(message) {
        const contentElement = document.querySelector(this.config.contentSelector);
        if (contentElement) {
            contentElement.classList.add(this.config.errorClass);
            
            // 临时显示错误消息
            const errorDiv = document.createElement('div');
            errorDiv.className = 'ajax-error-message';
            errorDiv.innerHTML = `<div class="alert alert-danger">${message}</div>`;
            
            contentElement.appendChild(errorDiv);
            
            // 3秒后移除错误消息
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
                contentElement.classList.remove(this.config.errorClass);
            }, 3000);
        }
    }
    
    /**
     * 触发自定义事件
     * @param {string} eventName - 事件名称
     * @param {Object} detail - 事件详情
     */
    triggerEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        window.dispatchEvent(event);
    }
    
    /**
     * 手动导航到指定URL
     * @param {string} url - 目标URL
     * @param {string} page - 页面标识
     */
    navigateTo(url, page = null) {
        this.handleLinkClick({ 
            getAttribute: (attr) => {
                if (attr === 'href') return url;
                if (attr === 'data-page') return page;
                return null;
            }
        });
    }
    
    /**
     * 销毁实例，清理所有事件监听器
     */
    destroy() {
        this.cleanupEventListeners();
        this.isInitialized = false;
        // console.log('AjaxNavigator: 已销毁');
    }
}

// 导出全局实例
window.AjaxNavigator = AjaxNavigator;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 创建全局实例
    window.ajaxNavigator = new AjaxNavigator();
    
    // 监听页面内容更新事件
    window.addEventListener('ajax:page:updated', () => {
        // console.log('AjaxNavigator: 检测到页面更新');
    });
});

/**
 * 处理fetch响应，自动检测JSON或HTML响应
 * @param {Response} response - fetch响应对象
 * @returns {Promise<Object>} 解析后的数据
 */
function handleFetchResponse(response) {
    if (response.redirected) {
        window.location.href = response.url;
        return Promise.resolve(null);
    }
    
    const contentType = response.headers.get('content-type');
    
    // 如果是JSON，直接解析
    if (contentType && contentType.includes('application/json')) {
        return response.json().then(data => {
            if (data && typeof data.success !== 'undefined') {
                return data;
            }
            throw new Error('Invalid JSON response format');
        });
    }
    
    // 否则尝试作为文本解析
    return response.text().then(text => {
        console.warn('Server returned non-JSON response, attempting to extract error message');
        
        // 尝试从HTML中提取常见的错误消息
        const errorPatterns = [
            { pattern: '用户名已存在', message: '用户名已存在，请更换用户名' },
            { pattern: '不能注册管理员账号', message: '不能注册管理员账号' },
            { pattern: '密码长度不能少于6个字符', message: '密码长度不能少于6个字符' },
            { pattern: '两次输入的密码不一致', message: '两次输入的密码不一致' },
            { pattern: '用户名和密码不能为空', message: '用户名和密码不能为空' },
            { pattern: '登录失败，用户名或密码错误', message: '登录失败，用户名或密码错误' }
        ];
        
        for (const { pattern, message } of errorPatterns) {
            if (text.includes(pattern)) {
                return { success: false, message };
            }
        }
        
        // 如果无法提取特定错误，返回通用错误
        return { 
            success: false, 
            message: '请求处理失败，请稍后重试'
        };
    });
}