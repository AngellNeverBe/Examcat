/**
 * 考试历史页面功能模块
 */

// ==================== 筛选功能 ====================
class ExamFilter {
    constructor() {
        this.filterAllBtn = document.getElementById('filter-all');
        this.filterCompletedBtn = document.getElementById('filter-completed');
        this.filterUnfinishedBtn = document.getElementById('filter-unfinished');
        this.examRows = document.querySelectorAll('.exam-row');
        
        if (this.filterAllBtn && this.filterCompletedBtn && this.filterUnfinishedBtn) {
            this.init();
        }
    }
    
    init() {
        // 绑定按钮点击事件
        this.filterAllBtn.addEventListener('click', () => this.updateFilter('all'));
        this.filterCompletedBtn.addEventListener('click', () => this.updateFilter('completed'));
        this.filterUnfinishedBtn.addEventListener('click', () => this.updateFilter('unfinished'));
        
        // 初始化：显示全部
        this.updateFilter('all');
    }
    
    updateFilter(selectedFilter) {
        // 更新按钮状态
        [this.filterAllBtn, this.filterCompletedBtn, this.filterUnfinishedBtn].forEach(btn => {
            btn.classList.remove('active');
        });
        
        switch(selectedFilter) {
            case 'all':
                this.filterAllBtn.classList.add('active');
                break;
            case 'completed':
                this.filterCompletedBtn.classList.add('active');
                break;
            case 'unfinished':
                this.filterUnfinishedBtn.classList.add('active');
                break;
        }
        
        // 显示/隐藏行
        this.examRows.forEach(row => {
            const status = row.dataset.status;
            
            switch(selectedFilter) {
                case 'all':
                    row.style.display = '';
                    break;
                case 'completed':
                    row.style.display = status === 'completed' ? '' : 'none';
                    break;
                case 'unfinished':
                    row.style.display = status === 'unfinished' ? '' : 'none';
                    break;
            }
        });
        
        // 更新行号
        this.updateRowNumbers(selectedFilter);
    }
    
    updateRowNumbers(selectedFilter) {
        let visibleIndex = 1;
        
        this.examRows.forEach(row => {
            const isVisible = row.style.display !== 'none';
            const firstCell = row.querySelector('td:first-child');
            
            if (firstCell && isVisible) {
                firstCell.textContent = visibleIndex++;
            }
        });
    }
}

// ==================== 模态框 ====================
class ModalManager {
    constructor() {
        this.modals = new Map();
        this.currentModal = null;
        this.init();
    }
    
    /**
     * 初始化模态框管理器
     */
    init() {
        // 查找所有模态框元素
        const modalElements = document.querySelectorAll('.modal');
        
        // 初始化每个模态框
        modalElements.forEach(modalElement => {
            this.createModal(modalElement);
        });
        
        // 添加ESC键监听
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentModal) {
                this.hide(this.currentModal);
            }
        });
    }
    
    /**
     * 创建模态框实例
     * @param {HTMLElement} modalElement - 模态框DOM元素
     * @returns {Modal} 模态框实例
     */
    createModal(modalElement) {
        const modalId = modalElement.id;
        const modal = new Modal(modalElement);
        this.modals.set(modalId, modal);
        
        // 设置关闭按钮点击事件
        const closeBtn = modalElement.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hide(modalId);
            });
        }
        
        // 设置关闭按钮点击事件（如果有多个关闭按钮）
        const dismissBtns = modalElement.querySelectorAll('[data-dismiss="modal"]');
        dismissBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.hide(modalId);
            });
        });
        
        // 点击模态框背景关闭
        modalElement.addEventListener('click', (e) => {
            if (e.target === modalElement) {
                this.hide(modalId);
            }
        });
        
        return modal;
    }
    
    /**
     * 显示模态框
     * @param {string} modalId - 模态框ID
     * @param {Object} options - 配置选项
     */
    show(modalId, options = {}) {
        const modal = this.modals.get(modalId);
        if (!modal) {
            console.error(`模态框 ${modalId} 不存在`);
            return;
        }
        
        // 如果已经有打开的模态框，先关闭它
        if (this.currentModal && this.currentModal !== modal) {
            this.hide(this.currentModal.element.id);
        }
        
        modal.show(options);
        this.currentModal = modal;
        
        // 阻止body滚动
        document.body.classList.add('modal-open');
    }
    
    /**
     * 隐藏模态框
     * @param {string} modalId - 模态框ID
     */
    hide(modalId) {
        const modal = this.modals.get(modalId);
        if (!modal) {
            console.error(`模态框 ${modalId} 不存在`);
            return;
        }
        
        modal.hide();
        this.currentModal = null;
        
        // 恢复body滚动
        document.body.classList.remove('modal-open');
    }
    
    /**
     * 获取模态框实例
     * @param {string} modalId - 模态框ID
     * @returns {Modal} 模态框实例
     */
    get(modalId) {
        return this.modals.get(modalId);
    }
    
    /**
     * 检查模态框是否可见
     * @param {string} modalId - 模态框ID
     * @returns {boolean} 是否可见
     */
    isVisible(modalId) {
        const modal = this.modals.get(modalId);
        return modal ? modal.visible : false;
    }
    
    /**
     * 销毁模态框
     * @param {string} modalId - 模态框ID
     */
    destroy(modalId) {
        const modal = this.modals.get(modalId);
        if (modal) {
            modal.destroy();
            this.modals.delete(modalId);
            
            if (this.currentModal === modal) {
                this.currentModal = null;
                document.body.classList.remove('modal-open');
            }
        }
    }
}

/**
 * 单个模态框类
 */
class Modal {
    constructor(element) {
        this.element = element;
        this.content = element.querySelector('.modal-content');
        this.visible = false;
        this.callbacks = {
            show: [],
            hide: []
        };
        
        this.init();
    }
    
    /**
     * 初始化模态框
     */
    init() {
        // 设置ARIA属性
        this.element.setAttribute('role', 'dialog');
        this.element.setAttribute('aria-modal', 'true');
        
        // 如果没有设置aria-labelledby，尝试自动设置
        if (!this.element.hasAttribute('aria-labelledby')) {
            const title = this.element.querySelector('.modal-title');
            if (title && title.id) {
                this.element.setAttribute('aria-labelledby', title.id);
            }
        }
        
        // 设置初始焦点元素
        this.initialFocusElement = null;
    }
    
    /**
     * 显示模态框
     * @param {Object} options - 配置选项
     */
    show(options = {}) {
        if (this.visible) return;
        
        // 保存当前活动元素，以便恢复焦点
        this.previousActiveElement = document.activeElement;
        
        // 显示模态框
        this.element.classList.add('show');
        this.visible = true;
        
        // 设置焦点
        setTimeout(() => {
            const focusElement = this.getFocusElement(options);
            if (focusElement) {
                focusElement.focus();
                this.initialFocusElement = focusElement;
            }
        }, 10);
        
        // 触发显示事件
        this.triggerEvent('show', this);
    }
    
    /**
     * 获取焦点元素
     * @param {Object} options - 配置选项
     * @returns {HTMLElement} 焦点元素
     */
    getFocusElement(options) {
        // 1. 优先使用options中的focusElement
        if (options.focusElement) {
            return options.focusElement;
        }
        
        // 2. 查找模态框中的第一个可聚焦元素
        const focusableElements = this.element.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length > 0) {
            return focusableElements[0];
        }
        
        // 3. 使用关闭按钮
        const closeBtn = this.element.querySelector('.modal-close');
        if (closeBtn) {
            return closeBtn;
        }
        
        // 4. 返回模态框内容本身
        return this.content;
    }
    
    /**
     * 隐藏模态框
     */
    hide() {
        if (!this.visible) return;
        
        // 隐藏模态框
        this.element.classList.remove('show');
        this.visible = false;
        
        // 恢复焦点到之前的元素
        if (this.previousActiveElement && this.previousActiveElement.focus) {
            setTimeout(() => {
                this.previousActiveElement.focus();
            }, 10);
        }
        
        // 触发隐藏事件
        this.triggerEvent('hide', this);
    }
    
    /**
     * 设置模态框内容
     * @param {string|HTMLElement} content - 内容
     */
    setContent(content) {
        const body = this.element.querySelector('.modal-body');
        if (!body) return;
        
        if (typeof content === 'string') {
            body.innerHTML = content;
        } else if (content instanceof HTMLElement) {
            body.innerHTML = '';
            body.appendChild(content);
        }
    }
    
    /**
     * 设置模态框标题
     * @param {string} title - 标题
     */
    setTitle(title) {
        const titleElement = this.element.querySelector('.modal-title');
        if (titleElement) {
            // 移除图标（如果有的话）
            const icon = titleElement.querySelector('i');
            if (icon) {
                titleElement.removeChild(icon);
            }
            titleElement.textContent = title;
        }
    }
    
    /**
     * 添加事件监听器
     * @param {string} event - 事件名称 ('show' 或 'hide')
     * @param {Function} callback - 回调函数
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }
    
    /**
     * 移除事件监听器
     * @param {string} event - 事件名称 ('show' 或 'hide')
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            const index = this.callbacks[event].indexOf(callback);
            if (index > -1) {
                this.callbacks[event].splice(index, 1);
            }
        }
    }
    
    /**
     * 触发事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     */
    triggerEvent(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`模态框事件 ${event} 回调错误:`, error);
                }
            });
        }
    }
    
    /**
     * 销毁模态框
     */
    destroy() {
        this.hide();
        this.callbacks.show = [];
        this.callbacks.hide = [];
        
        // 移除事件监听器
        const closeBtn = this.element.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.removeEventListener('click', this.hide.bind(this));
        }
        
        const dismissBtns = this.element.querySelectorAll('[data-dismiss="modal"]');
        dismissBtns.forEach(btn => {
            btn.removeEventListener('click', this.hide.bind(this));
        });
        
        this.element.removeEventListener('click', (e) => {
            if (e.target === this.element) {
                this.hide();
            }
        });
    }
}

// 创建全局模态框管理器实例
const modalManager = new ModalManager();

// 导出到全局作用域（如果需要）
window.ModalManager = modalManager;

/**
 * 考试详情模态框专用功能
 */
class ExamDetailModal {
    constructor() {
        this.modalId = 'examDetailModal';
        this.modal = modalManager.get(this.modalId);
        this.init();
    }
    
    /**
     * 初始化考试详情模态框
     */
    init() {
        if (!this.modal) {
            console.error('考试详情模态框不存在');
            return;
        }
        
        // 设置事件监听器
        this.bindEvents();
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 监听所有查看详情按钮的点击事件
        document.addEventListener('click', (e) => {
            const viewExamBtn = e.target.closest('.view-exam-btn');
            if (viewExamBtn) {
                e.preventDefault();
                const examId = viewExamBtn.dataset.examId;
                this.showExamDetail(examId);
            }
        });
    }
    
    /**
     * 显示考试详情
     * @param {string} examId - 考试ID
     */
    async showExamDetail(examId) {
        if (!this.modal) return;
        
        // 显示加载状态
        this.modal.setContent(`
            <div class="text-center py-4">
                <div class="spinner-border" role="status">
                    <span class="sr-only">加载中...</span>
                </div>
                <p class="mt-3">加载考试详情...</p>
            </div>
        `);
        
        // 显示模态框
        modalManager.show(this.modalId);
        
        try {
            // 获取考试详情
            const response = await fetch(`/exam/detail/${examId}`);
            const data = await response.json();
            
            if (data.success) {
                // 构建详情内容
                this.renderExamDetail(data.exam);
            } else {
                this.modal.setContent(`
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle"></i> 加载考试详情失败: ${data.msg}
                    </div>
                `);
            }
        } catch (error) {
            console.error('获取考试详情失败:', error);
            this.modal.setContent(`
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> 获取考试详情时发生错误
                </div>
            `);
        }
    }
    
    /**
     * 渲染考试详情
     * @param {Object} exam - 考试数据
     */
    renderExamDetail(exam) {
        let content = `
            <div class="exam-detail">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6><i class="fas fa-calendar-alt"></i> 开始时间</h6>
                        <p>${exam.start_time}</p>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-question-circle"></i> 题目数量</h6>
                        <p>${exam.question_count} 题</p>
                    </div>
                </div>
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6><i class="fas fa-clock"></i> 已用时间</h6>
                        <p>${exam.formatted_duration}</p>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-chart-line"></i> 得分</h6>
                        <p><span class="font-weight-bold ${exam.score_class}">${exam.score}%</span></p>
                    </div>
                </div>
        `;
        
        // 添加题目详情（如果有的话）
        if (exam.results && exam.results.length > 0) {
            content += `
                <h6 class="mb-3"><i class="fas fa-list-ol"></i> 题目详情</h6>
                <div class="question-results">
            `;
            
            exam.results.forEach((result, index) => {
                content += `
                    <div class="question-result mb-2 p-2 border rounded ${result.is_correct ? 'border-success' : 'border-danger'}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>题目 ${index + 1}</strong>: ${result.stem.substring(0, 50)}${result.stem.length > 50 ? '...' : ''}
                            </div>
                            <div>
                                ${result.is_correct ? 
                                    '<span class="badge badge-success"><i class="fas fa-check"></i> 正确</span>' : 
                                    '<span class="badge badge-danger"><i class="fas fa-times"></i> 错误</span>'
                                }
                            </div>
                        </div>
                        <div class="mt-1">
                            <small class="text-muted">你的答案: <strong>${result.user_answer || '未作答'}</strong> | 正确答案: <strong>${result.correct_answer}</strong></small>
                        </div>
                    </div>
                `;
            });
            
            content += `</div>`;
        }
        
        content += `</div>`;
        this.modal.setContent(content);
    }
    
    /**
     * 关闭考试详情模态框
     */
    close() {
        modalManager.hide(this.modalId);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 初始化筛选功能
    const examFilter = new ExamFilter();
    
    // 初始化模态框系统
    modalManager.init();
    
    // 初始化考试详情模态框（如果存在）
    if (document.getElementById('examDetailModal')) {
        const examDetailModal = new ExamDetailModal();
        
        // 导出到全局作用域（如果需要）
        window.ExamDetailModal = examDetailModal;
    }
    
    // API调用示例函数
    window.showExamDetail = (examId) => {
        const examDetailModal = window.ExamDetailModal || new ExamDetailModal();
        examDetailModal.showExamDetail(examId);
    };
    
    // 通用API：显示模态框
    window.showModal = (modalId, options = {}) => {
        modalManager.show(modalId, options);
    };
    
    // 通用API：隐藏模态框
    window.hideModal = (modalId) => {
        modalManager.hide(modalId);
    };
    
    // 通用API：设置模态框内容
    window.setModalContent = (modalId, content) => {
        const modal = modalManager.get(modalId);
        if (modal) {
            modal.setContent(content);
        }
    };
    // 导出筛选功能
    window.ExamFilter = examFilter;
});