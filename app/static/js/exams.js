/**
 * exams.js - 考试主页面交互
 * 处理开始考试、考试历史滚动等交互
 */

// console.log('exams.js 加载成功');

class ExamsPage {
    constructor() {
        this.init();
    }
    
    init() {
        // console.log('ExamsPage 初始化');
        this.setupEventListeners();
        this.setupHistoryScrolling();
        this.updateScrollButtons();
        this.setupAnimation();
    }
    
    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 开始考试表单提交
        const startExamForm = document.getElementById('startExamForm');
        if (startExamForm) {
            startExamForm.addEventListener('submit', (e) => {
                this.handleStartExamSubmit(e);
            });
        }
        
        // 继续考试按钮
        const continueExamBtn = document.querySelector('.btn-continue-exam:not(:disabled)');
        if (continueExamBtn) {
            continueExamBtn.addEventListener('click', (e) => {
                if (continueExamBtn.disabled) return;
                this.handleContinueExam(e);
            });
        }
        
        // 查看详情按钮（事件委托）
        document.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.btn-view-exam');
            if (viewBtn) {
                this.handleViewExam(e, viewBtn);
            }
        });
    }
    
    /**
     * 设置考试历史滚动
     */
    setupHistoryScrolling() {
        const historyItems = document.getElementById('historyItems');
        if (!historyItems) return;
        
        // 滚动事件监听，更新按钮状态
        historyItems.addEventListener('scroll', () => {
            this.updateScrollButtons();
        });
        
        // 向上滚动按钮
        const scrollUpBtn = document.querySelector('.btn-scroll-up');
        if (scrollUpBtn) {
            scrollUpBtn.addEventListener('click', () => {
                this.scrollHistory('up');
            });
        }
        
        // 向下滚动按钮
        const scrollDownBtn = document.querySelector('.btn-scroll-down');
        if (scrollDownBtn) {
            scrollDownBtn.addEventListener('click', () => {
                this.scrollHistory('down');
            });
        }
    }

    /**
     * 设置考试页面动画效果
     */
    setupAnimation() {
        const examsContainer = document.querySelector('.exams-container');
        if (!examsContainer) return;
        
        // 如果是通过AJAX导航切换的页面，需要重新触发动画
        if (document.body.classList.contains('page-content-updated')) {
            // 先移除动画类
            examsContainer.classList.remove('animate-in');
            
            // 强制重排，确保动画可以重新触发
            void examsContainer.offsetWidth;
            
            // 添加动画类触发动画
            setTimeout(() => {
                examsContainer.classList.add('animate-in');
            }, 10);
        }
    }

    /**
     * 处理开始考试表单提交
     */
    handleStartExamSubmit(event) {
        event.preventDefault();

        const form = event.target;
        const questionCount = form.querySelector('#questionCount').value;
        const submitBtn = form.querySelector('.btn-start-exam');

        // console.log(`开始考试，题目数量: ${questionCount}`);

        // 禁用按钮防止重复提交
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 准备中...';

        // 使用AJAX提交表单
        const formData = new FormData(form);

        // 添加AJAX请求头
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'X-Ajax-Navigation': 'true'
        };

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: headers
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // 显示成功消息
                this.showMessage(data.message, data.category || 'success');

                // 如果返回了AJAX导航指令，使用AJAX导航
                if (data.ajax_navigate && data.redirect) {
                    // 使用ajax_navigator进行导航
                    if (window.ajaxNavigator) {
                        window.ajaxNavigator.navigateTo(data.redirect);
                    } else {
                        // 回退到传统导航
                        window.location.href = data.redirect;
                    }
                } else if (data.redirect) {
                    // 普通重定向
                    window.location.href = data.redirect;
                }
            } else {
                // 显示错误消息
                this.showMessage(data.message, data.category || 'error');
                // 重新启用按钮
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-play-circle"></i> 开始考试';
            }
        })
        .catch(error => {
            console.error('开始考试失败:', error);
            this.showMessage('开始考试失败，请重试', 'error');
            // 重新启用按钮
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-play-circle"></i> 开始考试';
        });
    }
    
    /**
     * 处理继续考试
     */
    handleContinueExam(event) {
        // 继续考试直接跳转，无需额外处理
        // console.log('继续考试');
    }
    
    /**
     * 处理查看考试详情
     */
    handleViewExam(event, button) {
        // 查看详情直接跳转，无需额外处理
        // console.log('查看考试详情');
    }
    
    /**
     * 滚动考试历史
     */
    scrollHistory(direction) {
        const historyItems = document.getElementById('historyItems');
        if (!historyItems) return;
        
        const scrollAmount = 200; // 每次滚动距离
        const currentScroll = historyItems.scrollTop;
        const maxScroll = historyItems.scrollHeight - historyItems.clientHeight;
        
        if (direction === 'up') {
            // 向上滚动
            historyItems.scrollTo({
                top: Math.max(currentScroll - scrollAmount, 0),
                behavior: 'smooth'
            });
        } else if (direction === 'down') {
            // 向下滚动
            historyItems.scrollTo({
                top: Math.min(currentScroll + scrollAmount, maxScroll),
                behavior: 'smooth'
            });
        }
        
        // 延迟更新按钮状态
        setTimeout(() => {
            this.updateScrollButtons();
        }, 300);
    }
    
    /**
     * 更新滚动按钮状态
     */
    updateScrollButtons() {
        const historyItems = document.getElementById('historyItems');
        if (!historyItems) return;
        
        const scrollUpBtn = document.querySelector('.btn-scroll-up');
        const scrollDownBtn = document.querySelector('.btn-scroll-down');
        
        if (!scrollUpBtn || !scrollDownBtn) return;
        
        const currentScroll = historyItems.scrollTop;
        const maxScroll = historyItems.scrollHeight - historyItems.clientHeight;
        
        // 更新向上滚动按钮状态
        scrollUpBtn.disabled = currentScroll <= 0;
        scrollUpBtn.style.opacity = scrollUpBtn.disabled ? '0.5' : '1';
        scrollUpBtn.style.cursor = scrollUpBtn.disabled ? 'not-allowed' : 'pointer';
        
        // 更新向下滚动按钮状态
        scrollDownBtn.disabled = currentScroll >= maxScroll;
        scrollDownBtn.style.opacity = scrollDownBtn.disabled ? '0.5' : '1';
        scrollDownBtn.style.cursor = scrollDownBtn.disabled ? 'not-allowed' : 'pointer';
    }
    
    /**
     * 显示消息提示
     */
    showMessage(message, type = 'info') {
        // 使用已有的消息系统
        const messageContainer = document.getElementById('flashMessages');
        if (!messageContainer) {
            // console.log(`${type}: ${message}`);
            return;
        }
        
        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type}`;
        messageDiv.textContent = message;
        
        // 添加到容器
        messageContainer.appendChild(messageDiv);
        
        // 自动消失
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            messageDiv.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                messageDiv.remove();
            }, 300);
        }, 5000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const examsPage = new ExamsPage();
    
    // 添加到全局对象以便调试
    window.examsPage = examsPage;
    
    // console.log('ExamsPage 初始化完成');
});

// 监听 AJAX 切换后的事件
window.addEventListener('page:content:updated', () => {
    // 重新初始化动画效果
    if (window.examsPage && typeof window.examsPage.setupAnimation === 'function') {
        window.examsPage.setupAnimation();
    }
});

// 导出类供其他模块使用（如果需要）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExamsPage;
}