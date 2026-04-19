// question.js
document.addEventListener('DOMContentLoaded', function() {
    // console.log('question.js: DOMContentLoaded');
    initQuestionPage();
});

function initQuestionPage() {
    // console.log('question.js: 初始化题目页面');
    
    // 初始化收藏按钮
    initFavoriteButtons();

    // 检查页面是否已提交答案
    const hasSubmitted = document.querySelector('.result-message') !== null;
    
    if (!hasSubmitted) {
        // 未提交答案，初始化表单
        initQuestionForm();
    } else {
        // 已提交答案，禁用表单
        disableFormOptions();
        
        // 显示评论区（针对已答题目）
        showCommentsSection();
        
        // console.log('question.js: 已答题目，不创建初始导航按钮以避免竞争条件');
        // 对于直接浏览已答题的情况，不创建导航按钮
        // 避免触发额外的AJAX请求导致事件循环
        
        // 检查页面是否已经有导航按钮
        const existingNavButtons = document.querySelector('.question-actions .btn-group');
        if (!existingNavButtons) {
            // 尝试从页面获取导航数据
            const nextQid = document.querySelector('[data-next-qid]')?.getAttribute('data-next-qid');
            const prevQid = document.querySelector('[data-prev-qid]')?.getAttribute('data-prev-qid');
            const mode = document.querySelector('[data-mode]')?.getAttribute('data-mode');
            const bid = document.querySelector('[data-bid]')?.getAttribute('data-bid');
            
            if (nextQid || prevQid) {
                // 使用页面中的数据创建导航
                // console.log('question.js: 使用页面数据创建导航');
                createNavigationFromPageData({ bid, mode, next_qid: nextQid, prev_qid: prevQid });
            } else {
                // 没有页面数据，检查是否需要导航
                // 对于直接浏览已答题，可能不需要导航按钮
                // console.log('question.js: 没有页面导航数据，跳过创建导航按钮');
            }
        }
    }
}

// 从页面数据创建导航
function createNavigationFromPageData(data) {
    // console.log('question.js: 从页面数据创建导航:', data);
    
    const actionsDiv = document.querySelector('.question-actions');
    if (!actionsDiv) return;
    
    actionsDiv.innerHTML = '';
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'btn-group';
    actionsDiv.appendChild(buttonGroup);
    
    if (data.prev_qid && data.prev_qid !== 'null') {
        const prevBtn = document.createElement('a');
        // URL格式：/banks/{bid}/questions/{qid}?mode={mode}
        prevBtn.href = `/questions/${data.prev_qid}?mode=${encodeURIComponent(data.mode || 'other')}`;
        prevBtn.className = 'ajax-nav-link btn btn-primary';
        prevBtn.setAttribute('data-page', 'question');
        prevBtn.setAttribute('data-mode', data.mode || 'other'); // 添加data-mode
        prevBtn.innerHTML = '<i class="fas fa-arrow-left"></i> 上一题';
        buttonGroup.appendChild(prevBtn);
    }
    
    if (data.next_qid && data.next_qid !== 'null') {
        const nextBtn = document.createElement('a');
        // URL格式：/banks/{bid}/questions/{qid}?mode={mode}
        nextBtn.href = `/questions/${data.next_qid}?mode=${encodeURIComponent(data.mode || 'other')}`;
        nextBtn.className = 'ajax-nav-link btn btn-primary';
        nextBtn.setAttribute('data-page', 'question');
        nextBtn.setAttribute('data-mode', data.mode || 'other'); // 添加data-mode
        nextBtn.innerHTML = '<i class="fas fa-arrow-right"></i> 下一题';
        buttonGroup.appendChild(nextBtn);
    }
}

function initQuestionForm() {
    const questionForm = document.querySelector('.question-form');
    if (!questionForm) {
        // console.log('question.js: 未找到题目表单');
        return;
    }
    
    // console.log('question.js: 找到表单，绑定事件');
    
    // 移除旧的submit事件监听器
    const newForm = questionForm.cloneNode(true);
    questionForm.parentNode.replaceChild(newForm, questionForm);
    
    // 绑定新的submit事件
    newForm.addEventListener('submit', handleQuestionSubmit);
    
    // console.log('question.js: 表单事件绑定完成');
}

function handleQuestionSubmit(event) {
    event.preventDefault();
    event.stopPropagation();
    
    // console.log('question.js: 处理表单提交');
    
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    if (!submitBtn) {
        console.error('question.js: 未找到提交按钮');
        return;
    }
    
    // 显示加载状态
    submitBtn.disabled = true;
    const originalHTML = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';
    
    // 收集表单数据
    const formData = new FormData(form);
    
    // 添加AJAX请求头
    const headers = {
        'X-Requested-With': 'XMLHttpRequest'
    };
    
    // console.log('question.js: 发送AJAX请求到', form.action);
    
    // 发送AJAX请求
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: headers
    })
    .then(response => {
        // console.log('question.js: 收到响应，状态码:', response.status);
        const contentType = response.headers.get('content-type');
        // console.log('question.js: content-type:', contentType);
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            return response.text().then(text => {
                console.error('question.js: 服务器返回了非JSON响应:', text.substring(0, 200));
                throw new Error('服务器返回了HTML而不是JSON响应');
            });
        }
    })
    .then(data => {
        // console.log('question.js: 解析到的数据:', data);
        
        if (data.success) {
            // ✅ 关键修改：直接更新页面，而不是重新加载
            updateQuestionUI(data);
            
            // 恢复按钮状态
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
            
            // 隐藏提交按钮（因为答案已提交）
            submitBtn.style.display = 'none';
            
            // 更新导航按钮的URL
            updateNavigationButtons(data);
            
        } else {
            alert(data.message || '提交失败');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
        }
    })
    .catch(error => {
        console.error('question.js: 请求出错:', error);
        alert('网络错误，请稍后重试');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
    });
}

// ✅ 新增：直接更新页面UI
function updateQuestionUI(data) {
    // console.log('question.js: 更新页面UI');
    
    // 1. 显示结果消息
    showResultMessage(data);
    
    // 2. 更新统计信息
    updateStats(data.stats);
    
    // 3. 标记正确/错误选项
    markCorrectAnswers(data.question.answer);
    
    // 4. 禁用表单选项
    disableFormOptions();
    
    // 5. 更新收藏状态（如果有）
    updateFavoriteStatus(data.is_favorite);
    
    // 6. 显示评论区（如果有）
    showCommentsSection();
}

// 显示结果消息
function showResultMessage(data) {
    // 移除现有的Flash消息
    const existingMessages = document.querySelectorAll('.result-message, .alert');
    existingMessages.forEach(msg => msg.remove());
    
    // 创建结果消息
    const resultDiv = document.createElement('div');
    resultDiv.className = data.result_msg.includes('正确') ? 
        'result-message result-correct' : 'result-message result-incorrect';
    
    const icon = document.createElement('i');
    icon.className = data.result_msg.includes('正确') ? 
        'fas fa-check-circle' : 'fas fa-times-circle';
    
    resultDiv.appendChild(icon);
    resultDiv.appendChild(document.createTextNode(' ' + data.result_msg));
    
    // 插入到合适的位置（在题干之后，选项之前）
    const questionStem = document.querySelector('.question-stem');
    if (questionStem) {
        questionStem.parentNode.insertBefore(resultDiv, questionStem.nextSibling);
    } else {
        // 备用位置：插入到表单顶部
        const form = document.querySelector('.question-form');
        if (form) {
            form.insertBefore(resultDiv, form.firstChild);
        }
    }
    
    // 添加动画
    resultDiv.style.opacity = '0';
    resultDiv.style.transition = 'opacity 0.5s';
    setTimeout(() => {
        resultDiv.style.opacity = '1';
    }, 10);
}

// 更新统计信息
function updateStats(stats) {
    if (!stats) return;
    
    // 查找现有的统计信息显示区域
    let statsContainer = document.querySelector('.question-stats');
    
    if (!statsContainer) {
        // 如果没有，创建一个新的
        const questionInfo = document.querySelector('.question-info');
        if (questionInfo) {
            statsContainer = document.createElement('span');
            statsContainer.className = 'question-stats';
            questionInfo.appendChild(statsContainer);
        }
    }
    
    if (statsContainer) {
        statsContainer.innerHTML = `
            本题总共回答<span class="stats-number"> ${stats.total_answered} </span>次，
            正确<span class="stats-number"> ${stats.total_correct} </span>次，
            总正确率<span class="stats-accuracy 
                ${stats.accuracy >= 80 ? 'text-success' : 
                  stats.accuracy >= 60 ? 'text-warning' : 'text-danger'}">
                ${stats.accuracy}%
            </span>
        `;
    }
}

// 标记正确/错误答案
function markCorrectAnswers(correctAnswer) {
    // 获取用户选择的答案
    const selectedOptions = document.querySelectorAll('.option-checkbox:checked');
    const userAnswers = Array.from(selectedOptions).map(opt => opt.value);
    const correctAnswers = correctAnswer.split('');
    
    // 标记所有选项
    document.querySelectorAll('.option-label').forEach(label => {
        const checkbox = label.querySelector('.option-checkbox');
        const optionKey = checkbox.value;
        
        // 移除旧的样式
        label.classList.remove('option-correct', 'option-incorrect');
        
        // 标记正确答案
        if (correctAnswers.includes(optionKey)) {
            label.classList.add('option-correct');
        }
        
        // 标记用户错误选择的答案
        if (userAnswers.includes(optionKey) && !correctAnswers.includes(optionKey)) {
            label.classList.add('option-incorrect');
        }
    });
}

// 禁用表单选项
function disableFormOptions() {
    document.querySelectorAll('.option-checkbox').forEach(checkbox => {
        checkbox.disabled = true;
    });
}

// 更新收藏状态
function updateFavoriteStatus(isFavorite) {
    const favoriteBtn = document.querySelector('.favorite-btn');
    if (!favoriteBtn) return;
    
    if (isFavorite) {
        favoriteBtn.classList.add('active');
        favoriteBtn.innerHTML = '<i class="fas fa-star"></i> 已收藏';
    } else {
        favoriteBtn.classList.remove('active');
        favoriteBtn.innerHTML = '<i class="far fa-star"></i> 收藏本题';
    }
}

/**
 * 初始化收藏功能
 */
function initFavoriteButtons() {
    const favoriteBtn = document.querySelector('.favorite-btn');
    if (!favoriteBtn) return;
    
    favoriteBtn.addEventListener('click', handleFavoriteClick);
}
/**
 * 处理收藏按钮点击
 */
function handleFavoriteClick(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const button = event.currentTarget;
    const qid = button.getAttribute('data-qid');
    const currentAction = button.getAttribute('data-action');
    const newAction = currentAction === 'add' ? 'remove' : 'add';
    
    // 显示加载状态
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
    
    // 根据action选择请求方法
    const method = currentAction === 'add' ? 'POST' : 'DELETE';
    const url = `/favorites/${qid}`;
    
    // 发送AJAX请求
    fetch(url, {
        method: method,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (response.redirected) {
            return Promise.reject(new Error('请先登录'));
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            return response.text();
        }
    })
    .then(data => {
        if (typeof data === 'object' && data.success !== undefined) {
            // JSON响应
            if (data.success) {
                // 更新按钮状态
                updateFavoriteButton(button, newAction);
                
                // 显示简单的文字提示
                const hintText = currentAction === 'add' ? '收藏成功！' : '已移除！';
                showSimpleHint(button, hintText);
            } else {
                // 显示错误提示
                const errorText = data.error || data.msg || '操作失败';
                showSimpleHint(button, errorText);
                button.disabled = false;
                button.innerHTML = originalHTML;
            }
        } else if (typeof data === 'string') {
            // HTML响应，显示通用提示
            if (data.includes('收藏成功') || data.includes('已取消收藏')) {
                // 更新按钮状态
                updateFavoriteButton(button, newAction);
                
                // 显示简单的文字提示
                const hintText = currentAction === 'add' ? '收藏成功！' : '已移除！';
                showSimpleHint(button, hintText);
            } else {
                showSimpleHint(button, '操作完成');
                button.disabled = false;
                button.innerHTML = originalHTML;
            }
        }
    })
    .catch(error => {
        console.error('收藏操作失败:', error);
        showSimpleHint(button, '操作失败');
        button.disabled = false;
        button.innerHTML = originalHTML;
    });
}
/**
 * 显示简单的文字提示（淡出效果）
 */
function showSimpleHint(button, text) {
    // 获取按钮容器
    const container = button.parentNode;
    if (!container) return;
    
    // 移除现有的提示
    const existingHint = container.querySelector('.simple-hint');
    if (existingHint) {
        existingHint.remove();
    }
    
    // 创建提示元素
    const hint = document.createElement('span');
    hint.className = 'simple-hint';
    hint.textContent = text;
    
    // 添加到按钮前面
    container.insertBefore(hint, button);
    
    // 1.5秒后淡出并移除
    setTimeout(() => {
        hint.style.opacity = '0';
        setTimeout(() => {
            if (hint.parentNode === container) {
                hint.remove();
            }
        }, 500);
    }, 1500);
}
/**
 * 更新收藏按钮状态
 */
function updateFavoriteButton(button, newAction) {    
    button.setAttribute('data-action', newAction);
    
    if (newAction === 'remove') {
        // 改为已收藏状态
        button.classList.add('active');
        button.innerHTML = '<i class="fas fa-star"></i> 已收藏';
    } else {
        // 改为未收藏状态
        button.classList.remove('active');
        button.innerHTML = '<i class="far fa-star"></i> 收藏本题';
    }
    
    button.disabled = false;
}
/**
 * 处理重定向响应（用于未登录情况）
 */
function handleRedirect(response) {
    // 如果是登录重定向，可以在这里处理
    // 比如显示登录模态框或跳转到登录页面
    if (response.url.includes('/login')) {
        // 可以在这里触发登录模态框
        // console.log('需要登录');
        return Promise.reject(new Error('请先登录'));
    }
    
    return Promise.reject(new Error('重定向异常'));
}

// 更新导航按钮
function updateNavigationButtons(data) {
    // console.log('question.js: 更新导航按钮，数据:', data);
    
    const actionsDiv = document.querySelector('.question-actions');
    if (!actionsDiv) {
        console.error('question.js: 找不到question-actions容器');
        return;
    }
    
    // 清空现有按钮
    actionsDiv.innerHTML = '';
    
    // 创建按钮容器
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'btn-group';
    actionsDiv.appendChild(buttonGroup);
    
    // 添加上一题按钮（如果存在）
    if (data.prev_qid) {
        const prevBtn = document.createElement('a');
        prevBtn.href = `/banks/${data.bid}/questions/${data.prev_qid}?mode=${encodeURIComponent(data.mode || 'other')}`;
        prevBtn.className = 'ajax-nav-link btn btn-primary';
        prevBtn.setAttribute('data-page', 'question');
        prevBtn.setAttribute('data-mode', data.mode || 'other'); // 添加data-mode
        prevBtn.innerHTML = '<i class="fas fa-arrow-left"></i> 上一题';
        buttonGroup.appendChild(prevBtn);
    }
    
    // 添加下一题按钮（如果存在）
    if (data.next_qid) {
        const nextBtn = document.createElement('a');
        nextBtn.href = `/banks/${data.bid}/questions/${data.next_qid}?mode=${encodeURIComponent(data.mode || 'other')}`;
        nextBtn.className = 'ajax-nav-link btn btn-primary';
        nextBtn.setAttribute('data-page', 'question');
        nextBtn.setAttribute('data-mode', data.mode || 'other'); // 添加data-mode
        nextBtn.innerHTML = '<i class="fas fa-arrow-right"></i> 下一题';
        buttonGroup.appendChild(nextBtn);
    } else {
        // 没有下一题，显示完成消息
        const completionDiv = document.createElement('div');
        completionDiv.className = 'alert alert-success';
        completionDiv.innerHTML = `
            <i class="fas fa-check-circle"></i> 恭喜！您已完成所有题目。
        `;
        actionsDiv.appendChild(completionDiv);
        
        const homeBtn = document.createElement('a');
        homeBtn.href = '/';
        homeBtn.className = 'ajax-nav-link btn btn-primary';
        homeBtn.setAttribute('data-page', 'index');
        homeBtn.innerHTML = '<i class="fas fa-home"></i> 返回首页';
        buttonGroup.appendChild(homeBtn);
    }
}

// 创建初始导航按钮（页面加载时调用）
function createInitialNavigationButtons() {
    // console.log('question.js: 创建初始导航按钮');
    
    // 从当前URL获取参数
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode') || 'other';
    
    // 解析路径获取 qid
    const pathParts = window.location.pathname.split('/');
    // 预期路径: /questions/{qid}
    
    if (pathParts.length >= 5) {
        const qid = pathParts[2]; // questions/后的第一个参数
        
        // console.log('question.js: 解析到的参数:', {mode, qid});
        
        // 从服务器获取题目信息（使用新的URL格式）
        fetchQuestionInfo(mode, qid);
    }
}

// 从服务器获取题目信息
function fetchQuestionInfo(mode, qid) {
    // console.log('question.js: 获取题目信息');
    
    fetch(`/questions/${qid}?mode=${encodeURIComponent(mode)}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-Ajax-Navigation': 'true'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // console.log('question.js: 获取到的题目信息:', data);
            // 更新导航按钮
            updateNavigationButtons(data);
        }
    })
    .catch(error => {
        console.error('question.js: 获取题目信息失败:', error);
    });
}

// 显示完成消息
function showCompletionMessage() {
    const actionsDiv = document.querySelector('.question-actions');
    if (!actionsDiv) return;
    
    const completionDiv = document.createElement('div');
    completionDiv.className = 'alert alert-success';
    completionDiv.innerHTML = `
        <i class="fas fa-check-circle"></i> 
        恭喜！您已完成所有题目。
    `;
    
    actionsDiv.insertBefore(completionDiv, actionsDiv.firstChild);
}

// 显示评论区
function showCommentsSection() {
    const artalkSection = document.querySelector('#artalk-section');
    const commentsContainer = document.querySelector('#Comments');
    
    if (artalkSection) {
        artalkSection.style.display = 'block';
    }
    
    if (commentsContainer) {
        // 如果ArtalkManager可用，使用管理器显示评论区
        if (window.ArtalkManager && window.ArtalkManager.isArtalkEnabled()) {
            const pageKey = commentsContainer.getAttribute('data-page-key');
            const pageTitle = commentsContainer.getAttribute('data-page-title') || document.title;
            
            if (pageKey) {
                // console.log('question.js: 使用ArtalkManager显示评论区 pageKey=', pageKey);
                window.ArtalkManager.showComments(pageKey, pageTitle);
            } else {
                console.warn('question.js: 未找到pageKey属性');
                commentsContainer.style.display = 'block';
            }
        } else {
            console.warn('question.js: ArtalkManager不可用，简单显示容器');
            commentsContainer.style.display = 'block';
        }
    }
}

// 检查是否有已提交的答案
function checkForExistingAnswer() {
    // 这里可以检查URL参数或本地存储，恢复答题状态
    // 例如：如果页面是通过后退按钮返回的，可能需要恢复状态
}

// 监听AJAX页面更新事件
window.addEventListener('ajax:page:updated', function() {
    // console.log('question.js: 检测到页面更新，重新初始化');
    setTimeout(() => {
        initQuestionPage();
        initFavoriteButtons();
    }, 100);
});

// // 导出函数（如果需要）
// window.QuestionManager = {
//     init: initQuestionPage,
//     submitAnswer: handleQuestionSubmit,
//     updateUI: updateQuestionUI
// };