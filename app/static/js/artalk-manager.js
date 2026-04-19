// artalk-manager.js - Artalk评论系统全局管理器
// 用于在AJAX页面切换中管理Artalk实例

/**
 * Artalk全局管理器
 */
const ArtalkManager = (function() {
    // 默认配置
    const defaultConfig = {
        el: '#Comments',
        server: '',
        site: '',
        locale: 'zh-CN',
        pageKey: '',
        pageTitle: ''
    };

    // 私有变量
    let artalkInstance = null;
    let currentConfig = { ...defaultConfig };
    let isInitialized = false;
    let isEnabled = false;
    let pendingCommentsQueue = []; // 待处理的评论区显示任务
    let isProcessingAutoShow = false; // 防止重复处理自动显示的标志
    let lastProcessedUrl = ''; // 最后处理的URL，用于避免重复处理
    let lastShowTime = 0; // 上次显示评论区的时间戳
    const SHOW_COOLDOWN = 1000; // 显示后冷却时间（毫秒）

    /**
     * 初始化Artalk管理器
     * @param {Object} config - Artalk配置
     */
    function init(config = {}) {
        if (isInitialized) {
            console.warn('ArtalkManager: 已经初始化');
            return;
        }

        console.log('ArtalkManager: 初始化中...');
        
        // 合并配置
        currentConfig = { ...defaultConfig, ...config };
        isEnabled = currentConfig.server && currentConfig.site;
        
        if (!isEnabled) {
            console.warn('ArtalkManager: Artalk未启用，缺少server或site配置');
            return;
        }

        // 检查Artalk库是否已加载
        if (typeof window.Artalk === 'undefined') {
            console.error('ArtalkManager: Artalk库未加载，请确保已引入Artalk.js');
            return;
        }

        isInitialized = true;
        console.log('ArtalkManager: 初始化完成，配置:', currentConfig);
        
        // 执行待处理的评论区显示任务
        if (pendingCommentsQueue.length > 0) {
            console.log(`ArtalkManager: 执行 ${pendingCommentsQueue.length} 个待处理任务`);
            pendingCommentsQueue.forEach(task => {
                showComments(task.pageKey, task.pageTitle);
            });
            pendingCommentsQueue = [];
        }
    }

    /**
     * 创建或更新Artalk实例
     * @param {Object} config - 页面特定配置
     * @returns {Artalk|null} Artalk实例或null
     */
    function createOrUpdateInstance(config = {}) {
        if (!isEnabled || !isInitialized) {
            console.warn('ArtalkManager: Artalk未启用或未初始化');
            return null;
        }

        try {
            const mergedConfig = { ...currentConfig, ...config };
            
            // 验证必要参数
            if (!mergedConfig.pageKey) {
                console.error('ArtalkManager: 缺少pageKey参数');
                return null;
            }

            if (artalkInstance) {
                // 更新现有实例配置
                console.log('ArtalkManager: 更新现有Artalk实例配置', mergedConfig);
                try {
                    artalkInstance.update(mergedConfig);
                    artalkInstance.reload();
                } catch (error) {
                    console.error('ArtalkManager: 更新Artalk实例失败:', error);
                    handleArtalkError(error);
                    // 即使更新失败，也返回实例以便容器保持显示
                }
            } else {
                // 创建新实例
                console.log('ArtalkManager: 创建新Artalk实例', mergedConfig);
                try {
                    artalkInstance = window.Artalk.init(mergedConfig);

                    // 监听事件
                    artalkInstance.on('list-loaded', handleCommentsLoaded);
                    artalkInstance.on('error', handleArtalkError);

                    // 将实例挂载到window对象，便于调试和外部访问
                    window.artalk = artalkInstance;
                } catch (error) {
                    console.error('ArtalkManager: 创建Artalk实例失败:', error);
                    handleArtalkError(error);
                    // 即使创建失败，也返回null，但容器已经显示
                    return null;
                }
            }

            return artalkInstance;
        } catch (error) {
            console.error('ArtalkManager: 创建/更新Artalk实例失败:', error);
            showErrorMessage('评论系统加载失败，请刷新页面重试');
            return null;
        }
    }

    /**
     * 销毁Artalk实例
     */
    function destroyInstance() {
        if (artalkInstance) {
            try {
                console.log('ArtalkManager: 销毁Artalk实例');
                artalkInstance.destroy();
                artalkInstance = null;
                window.artalk = null;
            } catch (error) {
                console.error('ArtalkManager: 销毁Artalk实例失败:', error);
            }
        }
    }

    /**
     * 检查artalk实例是否仍然有效
     * @returns {boolean}
     */
    function isInstanceValid() {
        if (!artalkInstance) return false;

        // 检查实例是否有el配置，并且该元素仍在DOM中
        try {
            const config = artalkInstance.conf || artalkInstance.getConf?.() || artalkInstance.ctx?.getConf?.();
            if (!config || !config.el) return false;

            const el = document.querySelector(config.el);
            if (!el) {
                console.log('ArtalkManager: artalk实例的DOM元素不在文档中，实例无效');
                return false;
            }

            // 检查元素是否已挂载artalk（是否有artalk相关类）
            const hasArtalkClass = el.classList.contains('artalk');
            if (!hasArtalkClass) {
                console.log('ArtalkManager: artalk实例的DOM元素缺少artalk类，实例可能未正确初始化');
                return false;
            }

            return true;
        } catch (error) {
            console.error('ArtalkManager: 检查实例有效性时出错:', error);
            return false;
        }
    }

    /**
     * 显示评论区
     * @param {string} pageKey - 页面标识
     * @param {string} pageTitle - 页面标题
     */
    function showComments(pageKey, pageTitle) {
        // 如果尚未初始化，将任务加入队列
        if (!isInitialized) {
            console.log(`ArtalkManager: 尚未初始化，将评论区显示任务加入队列 pageKey=${pageKey}`);
            pendingCommentsQueue.push({ pageKey, pageTitle });
            return false;
        }

        if (!isEnabled) {
            console.warn('ArtalkManager: Artalk未启用');
            return false;
        }

        console.log(`ArtalkManager: 显示评论区 pageKey=${pageKey}, pageTitle=${pageTitle}`);

        // 检查容器元素是否存在
        const container = document.querySelector(currentConfig.el);
        if (!container) {
            console.error(`ArtalkManager: 未找到评论区容器 ${currentConfig.el}`);
            showErrorMessage('评论区容器不存在');
            return false;
        }

        // 防重复检查：如果容器已显示且artalk实例有效且为相同页面，跳过重复调用
        const isContainerVisible = container.style.display !== 'none';
        const hasValidInstance = isInstanceValid();

        // 检查是否为相同页面（通过pageKey）
        let isSamePageKey = false;
        if (artalkInstance && hasValidInstance) {
            // 尝试从不同属性获取pageKey
            const instancePageKey = artalkInstance.conf?.pageKey ||
                                   artalkInstance.getConf?.()?.pageKey ||
                                   (artalkInstance.ctx?.getConf?.()?.pageKey);
            isSamePageKey = instancePageKey === pageKey;
        }

        if (isContainerVisible && hasValidInstance && isSamePageKey) {
            console.log(`ArtalkManager: 评论区已显示且实例有效 pageKey=${pageKey}，跳过重复调用`);
            return true;
        }

        // 如果实例存在但无效，销毁它以便重新创建
        if (artalkInstance && !hasValidInstance) {
            console.log('ArtalkManager: artalk实例无效，销毁旧实例');
            destroyInstance();
        }

        // 显示容器
        container.style.display = 'block';

        // 更新上次显示时间
        lastShowTime = Date.now();

        // 更新配置并创建实例
        const config = {
            pageKey: pageKey,
            pageTitle: pageTitle || document.title
        };

        const instance = createOrUpdateInstance(config);
        // 即使实例创建失败，容器也已经显示，返回true
        // 更新评论计数显示（如果实例存在）
        if (instance) {
            updateCommentCount();
        } else {
            console.warn('ArtalkManager: Artalk实例创建失败，但评论区容器已显示');
            // 显示通用错误消息
            showErrorMessage('评论系统初始化失败，可能由于网络或服务器问题');
        }

        return true;
    }

    /**
     * 隐藏评论区
     */
    function hideComments() {
        console.log('ArtalkManager: hideComments被调用');
        
        // 检查是否在冷却期内（刚刚显示过评论区）
        const now = Date.now();
        if (now - lastShowTime < SHOW_COOLDOWN) {
            console.log(`ArtalkManager: 在显示冷却期内（${now - lastShowTime}ms < ${SHOW_COOLDOWN}ms），跳过隐藏`);
            return;
        }
        
        // 检查当前是否应该显示评论区（针对已答题目页面）
        const shouldShow = shouldShowComments();
        if (shouldShow) {
            console.log('ArtalkManager: 当前应该显示评论区，跳过隐藏');
            return;
        }
        
        const container = document.querySelector(currentConfig.el);
        if (container) {
            container.style.display = 'none';
            console.log('ArtalkManager: 隐藏评论区');
        }
    }

    /**
     * 更新评论计数显示
     */
    function updateCommentCount() {
        if (!artalkInstance) return;
        
        // 使用setTimeout等待评论加载
        setTimeout(() => {
            try {
                const countEl = document.querySelector('.artalk-comment-count');
                if (countEl) {
                    // 这里可以获取实际评论数量
                    // 由于Artalk API限制，可能需要从DOM中获取
                    const commentItems = document.querySelectorAll('.atk-comment');
                    const count = commentItems.length;
                    countEl.textContent = count || '0';
                }
            } catch (error) {
                console.warn('ArtalkManager: 更新评论计数失败:', error);
            }
        }, 1000);
    }

    /**
     * 处理评论加载完成事件
     * @param {Array} comments - 评论列表
     */
    function handleCommentsLoaded(comments) {
        console.log(`ArtalkManager: 评论加载完成，共${comments.length}条评论`);
        updateCommentCount();
    }

    /**
     * 处理Artalk错误
     * @param {Error} error - 错误对象
     */
    function handleArtalkError(error) {
        console.error('ArtalkManager: Artalk错误:', error);

        // 检查是否为CORS错误
        const isCorsError = error.message && (
            error.message.includes('CORS') ||
            error.message.includes('Access-Control-Allow-Origin') ||
            error.message.includes('Failed to fetch') ||
            error.name === 'TypeError'
        );

        let errorMessage = `评论系统错误: ${error.message}`;
        if (isCorsError) {
            errorMessage = '评论系统连接失败（跨域限制）。请检查Artalk服务器配置或本地网络连接。';
            console.warn('ArtalkManager: 检测到CORS错误，Artalk服务器可能未正确配置CORS');
        }

        showErrorMessage(errorMessage);
    }

    /**
     * 显示错误消息
     * @param {string} message - 错误消息
     */
    function showErrorMessage(message) {
        // 创建错误提示
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.style.marginTop = '10px';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        // 插入到评论区容器前
        const container = document.querySelector(currentConfig.el);
        if (container && container.parentNode) {
            container.parentNode.insertBefore(errorDiv, container);
            
            // 添加关闭按钮事件
            const closeBtn = errorDiv.querySelector('.close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    errorDiv.remove();
                });
            }
        }
    }

    /**
     * 检查当前页面是否应该显示评论区
     * @returns {boolean}
     */
    function shouldShowComments() {
        // 检查是否是题目页面：存在评论区容器且有题目相关元素
        const hasCommentsContainer = document.querySelector(currentConfig.el) !== null;
        const hasQuestionElements = document.querySelector('.question-stem, .question-form, .question-info') !== null;
        const isQuestionPage = hasCommentsContainer && hasQuestionElements;

        if (!isQuestionPage) {
            return false;
        }

        // 检查是否有.result-message元素（表示已提交答案）
        const resultMessageEl = document.querySelector('.result-message');
        const hasResultMessage = resultMessageEl !== null;

        // 检查是否有已禁用的选项表单（表示已答题）
        const disabledOptions = document.querySelectorAll('.question-form .form-check-input:disabled');
        const hasDisabledOptions = disabledOptions.length > 0;

        // 检查评论区容器是否已经显示
        const container = document.querySelector(currentConfig.el);
        const isContainerVisible = container && container.style.display !== 'none';

        // 检查是否有已答题的其他标识：已禁用的提交按钮
        const disabledSubmitBtn = document.querySelector('.question-form button[type="submit"]:disabled');
        const hasDisabledSubmitBtn = disabledSubmitBtn !== null;

        // 检查URL参数：如果通过ajax加载，可能不是标准路径
        const urlPath = window.location.pathname;
        const isAjaxQuestionPage = urlPath.includes('/ajax/question-');

        console.log(`ArtalkManager: shouldShowComments检查:
          hasResultMessage: ${hasResultMessage} (元素: ${resultMessageEl?.tagName || 'null'})
          hasDisabledOptions: ${hasDisabledOptions} (数量: ${disabledOptions.length})
          hasDisabledSubmitBtn: ${hasDisabledSubmitBtn}
          hasCommentsContainer: ${hasCommentsContainer}
          hasQuestionElements: ${hasQuestionElements}
          isQuestionPage: ${isQuestionPage}
          isContainerVisible: ${isContainerVisible}
          isAjaxQuestionPage: ${isAjaxQuestionPage}
          pathname: ${urlPath}`);

        // 如果容器已经显示，或者有已答题的标识，就应该显示评论区
        return isContainerVisible || hasResultMessage || hasDisabledOptions || hasDisabledSubmitBtn;
    }

    /**
     * 页面加载时自动检查并显示评论区
     */
    function autoShowCommentsIfNeeded() {
        // 防止重复处理
        if (isProcessingAutoShow) {
            console.log('ArtalkManager: 正在处理自动显示，跳过');
            return;
        }
        
        const currentUrl = window.location.href;
        if (currentUrl === lastProcessedUrl) {
            console.log('ArtalkManager: 当前URL已处理过，跳过', currentUrl);
            return;
        }
        
        isProcessingAutoShow = true;
        console.log('ArtalkManager: 开始自动检查评论区显示，URL:', currentUrl);
        
        try {
            // 检查是否在题目页面：存在评论区容器且有题目相关元素
            const hasCommentsContainer = document.querySelector(currentConfig.el) !== null;
            const hasQuestionElements = document.querySelector('.question-stem, .question-form, .question-info') !== null;
            const isQuestionPage = hasCommentsContainer && hasQuestionElements;

            if (isQuestionPage) {
                // 检查评论区容器是否已经显示
                const container = document.querySelector(currentConfig.el);
                const isContainerVisible = container && container.style.display !== 'none';

                // 检查是否应该显示评论区
                if (shouldShowComments()) {
                    // 如果容器已显示且artalk实例有效，跳过重复处理
                    if (isContainerVisible && isInstanceValid()) {
                        console.log('ArtalkManager: 评论区已显示且实例有效，跳过自动显示');
                        lastProcessedUrl = currentUrl;
                        return;
                    }

                    // 尝试从评论区容器获取pageKey
                    const commentsContainer = document.querySelector(currentConfig.el);
                    let pageKey = '';

                    if (commentsContainer) {
                        pageKey = commentsContainer.getAttribute('data-page-key');
                    }

                    // 如果容器中没有pageKey，尝试从URL提取
                    if (!pageKey) {
                        const pathParts = window.location.pathname.split('/');
                        // 尝试从路径中提取题目ID
                        // 预期路径: /questions/{qid} 或 /question/{qid} 或 /ajax/question-{qid}
                        for (let i = 0; i < pathParts.length; i++) {
                            if ((pathParts[i] === 'questions' || pathParts[i] === 'question') && i + 1 < pathParts.length) {
                                pageKey = pathParts[i + 1];
                                break;
                            }
                        }

                        // 检查ajax路径格式: /ajax/question-{qid}
                        if (!pageKey && pathParts.includes('ajax')) {
                            const ajaxPart = pathParts.find(part => part.startsWith('question-'));
                            if (ajaxPart) {
                                pageKey = ajaxPart.replace('question-', '');
                            }
                        }
                    }

                    if (pageKey) {
                        console.log('ArtalkManager: 自动显示评论区 pageKey=', pageKey);
                        showComments(pageKey, document.title);
                        lastProcessedUrl = currentUrl;
                    } else {
                        console.warn('ArtalkManager: 无法从页面或URL提取pageKey');
                        lastProcessedUrl = currentUrl;
                    }
                } else {
                    // 在题目页面但不应显示评论区，不执行任何操作
                    // 评论区容器默认通过CSS隐藏（display: none）
                    console.log('ArtalkManager: 在题目页面但未答题，保持评论区隐藏状态');
                    lastProcessedUrl = currentUrl;
                }
            } else {
                // 不在题目页面，不执行任何操作
                // 其他页面可能没有评论区容器，或者有自己的评论区逻辑
                console.log('ArtalkManager: 不在题目页面，不操作评论区');
                lastProcessedUrl = currentUrl;
            }
        } finally {
            isProcessingAutoShow = false;
        }
    }

    /**
     * 获取当前Artalk实例
     * @returns {Artalk|null}
     */
    function getInstance() {
        return artalkInstance;
    }

    /**
     * 获取当前配置
     * @returns {Object}
     */
    function getConfig() {
        return { ...currentConfig };
    }

    /**
     * 判断Artalk是否启用
     * @returns {boolean}
     */
    function isArtalkEnabled() {
        return isEnabled && isInitialized;
    }

    // 初始化事件监听
    document.addEventListener('DOMContentLoaded', function() {
        // 延迟执行，确保其他脚本已加载
        setTimeout(() => {
            autoShowCommentsIfNeeded();
        }, 100);
    });

    /**
     * 从当前页面的评论区容器中获取pageKey
     * @returns {string|null}
     */
    function getPageKeyFromDOM() {
        const container = document.querySelector(currentConfig.el);
        if (!container) return null;
        return container.getAttribute('data-page-key');
    }

    /**
     * 处理页面更新事件
     */
    function handlePageUpdated() {
        console.log('ArtalkManager: 检测到页面更新');

        // 检查新页面中是否有评论区容器
        const newPageKey = getPageKeyFromDOM();
        const hasCommentsContainer = newPageKey !== null;

        // 如果没有评论区容器，销毁实例
        if (!hasCommentsContainer) {
            console.log('ArtalkManager: 新页面没有评论区容器，销毁实例');
            destroyInstance();
        } else if (artalkInstance) {
            // 如果有实例，检查是否为相同页面
            const instancePageKey = artalkInstance.conf?.pageKey ||
                                  artalkInstance.getConf?.()?.pageKey ||
                                  (artalkInstance.ctx?.getConf?.()?.pageKey);

            // 如果pageKey不同，销毁旧实例（新页面需要新实例）
            if (instancePageKey && newPageKey !== instancePageKey) {
                console.log(`ArtalkManager: 页面切换 (${instancePageKey} -> ${newPageKey})，销毁旧实例`);
                destroyInstance();
            }
        }

        // 清除之前的定时器
        if (pageUpdateTimeout) {
            clearTimeout(pageUpdateTimeout);
        }

        // 设置新的定时器，延迟更长以确保页面完全加载
        pageUpdateTimeout = setTimeout(() => {
            autoShowCommentsIfNeeded();
        }, 500);
    }

    // 监听AJAX页面更新事件
    let pageUpdateTimeout = null;
    window.addEventListener('ajax:page:updated', handlePageUpdated);

    // 监听答题完成事件（从question.js触发）
    window.addEventListener('question:answer:submitted', function(event) {
        console.log('ArtalkManager: 检测到答题完成事件', event.detail);
        if (event.detail && event.detail.questionId) {
            showComments(event.detail.questionId, event.detail.questionTitle);
        }
    });

    // 公共API
    return {
        init,
        showComments,
        hideComments,
        destroyInstance,
        getInstance,
        getConfig,
        isArtalkEnabled,
        shouldShowComments,
        autoShowCommentsIfNeeded
    };
})();

// 将管理器挂载到window对象
window.ArtalkManager = ArtalkManager;

// 自动初始化（当artalk配置可用时）
document.addEventListener('DOMContentLoaded', function() {
    // 检查全局配置
    if (window.ARTALK_CONFIG) {
        ArtalkManager.init(window.ARTALK_CONFIG);
    } else {
        console.warn('ArtalkManager: 未找到全局配置，请在页面中设置window.ARTALK_CONFIG');
    }
});

// 导出（用于模块化环境）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ArtalkManager;
}

// 全局错误处理：捕获未处理的Promise拒绝（如CORS错误）
window.addEventListener('unhandledrejection', function(event) {
    const error = event.reason;

    // 检查是否为Artalk相关的CORS错误
    if (error && (
        error.message && error.message.includes('fetch') ||
        error.message && error.message.includes('CORS') ||
        error.message && error.message.includes('Access-Control-Allow-Origin')
    )) {
        console.warn('ArtalkManager: 捕获到未处理的Promise拒绝（可能为CORS错误）:', error);
        event.preventDefault(); // 阻止默认错误处理

        // 如果ArtalkManager已初始化，显示错误消息
        if (window.ArtalkManager && window.ArtalkManager.isArtalkEnabled()) {
            const errorMessage = '评论系统连接失败（跨域限制）。请检查Artalk服务器配置。';
            console.error('ArtalkManager:', errorMessage);

            // 尝试显示错误消息
            try {
                const showErrorMessage = window.ArtalkManager.getInstance()?.showErrorMessage;
                if (typeof showErrorMessage === 'function') {
                    showErrorMessage(errorMessage);
                }
            } catch (e) {
                console.error('ArtalkManager: 无法显示错误消息:', e);
            }
        }
    }
});

// 全局错误监听（用于调试）
window.addEventListener('error', function(event) {
    // 记录所有错误，便于调试
    console.debug('ArtalkManager: 全局错误监听:', event.error);
});