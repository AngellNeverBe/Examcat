function initIndexPage() {
    // 检查是否是考试页面，如果是则跳过首页初始化
    const examConfigElement = document.getElementById('examConfig');
    if (examConfigElement) {
        // console.log('检测到考试页面，跳过首页初始化');
        return;
    }
    
    // 所有初始化代码放到这里
    initIndexAnimation();
    initHitokoto();
    initCountdown();
    initQuestionNavigation();
    initResetButton();
}

/**
 * 初始化首页动画效果
 */
function initIndexAnimation() {
    const indexSection = document.querySelector('.index-section');
    if (!indexSection) return;
    
    // 如果是通过AJAX导航切换的页面，需要重新触发动画
    if (document.body.classList.contains('page-content-updated')) {
        // 先移除动画类
        indexSection.classList.remove('animate-in');
        
        // 强制重排，确保动画可以重新触发
        void indexSection.offsetWidth;
        
        // 添加动画类触发动画
        setTimeout(() => {
            indexSection.classList.add('animate-in');
        }, 10);
    }
}
/**
 * 初始化一言
 */
function initHitokoto() {
    const hitokotoLink = document.querySelector("#hitokoto-text");
    const fromElement = document.querySelector("#hitokoto-from");
    
    // 如果一言元素不存在，直接返回（可能不是首页）
    if (!hitokotoLink || !fromElement) {
        return;
    }
    
    fetch("https://v1.hitokoto.cn?c=a&c=b&c=d&c=h&c=i&c=k")
        .then((response) => response.json())
        .then((data) => {
            hitokotoLink.href = `https://hitokoto.cn/?uuid=${data.uuid}`;

            // 原始句子
            let sentence = data.hitokoto;
            // 处理换行：寻找中间附近的逗号
            let displayText = sentence.length > 12 ? insertLineBreakNearMiddle(sentence) : sentence;
            hitokotoLink.innerText = `「${displayText}」`;

            if (data.from) {
                fromElement.innerText = `—— 《 ${data.from} 》`;
            } else {
                fromElement.innerText = "";
            }
        })
        .catch(console.error);

    /**
    * 在句子中间附近的逗号（中英文逗号、顿号）后插入换行符
    * @param {string} text 原始句子
    * @returns {string} 处理后的句子
    */
    function insertLineBreakNearMiddle(text) {
        const mid = Math.floor(text.length / 2);
        const searchRange = Math.floor(text.length * 0.2); // 在中点前后各20%范围内查找
        let bestIndex = -1;
        let minDistance = Infinity;

        // 查找范围内所有逗号类标点
        for (let i = Math.max(0, mid - searchRange); i < Math.min(text.length, mid + searchRange); i++) {
            const char = text[i];
            if (char === ';' || char === '；' || char === '，' || char === ',' || char === '、' || char === '。'|| char === '.'|| char === '？'|| char === '?'|| char === '！'|| char === '!'|| char === '：'|| char === ':') {
                const distance = Math.abs(i - mid);
                if (distance < minDistance) {
                    minDistance = distance;
                    bestIndex = i;
                }
            }
        }

        if (bestIndex !== -1) {
            // 在逗号后插入换行符，并保留逗号
            return text.slice(0, bestIndex + 1) + '\n' + text.slice(bestIndex + 1);
        }
        // 没找到合适逗号则原样返回
        return text;
    }
}

/**
 * 初始化首页倒计时
 */
function initCountdown(){
    const ROTATE_INTERVAL = 5000, FADE_DURATION = 280;
    const normalView = document.getElementById('countdownNormalView');
    const emptyView = document.getElementById('countdownEmptyView');
    
    // 如果倒计时容器不存在，直接返回（可能不是首页）
    if (!normalView && !emptyView) {
        return;
    }
    
    const courseEl = document.getElementById('countdownCourse');
    const daysEl = document.getElementById('countdownDays');
    const hintCourseEl = document.getElementById('hintCourseName');
    const fadeEls = [courseEl, daysEl, hintCourseEl].filter(el => el);

    let rawExams = [], futureExams = [], currentIdx = 0, timer = null, animLock = false, pending = null;

    const parseDate = s => s ? new Date(s.replace(/-/g,'/')) : null;
    const daysUntil = s => { const e=parseDate(s); if(!e||isNaN(e)) return null; const n=new Date(); n.setHours(0,0,0,0); e.setHours(0,0,0,0); return Math.floor((e-n)/86400000); };
    const filterFuture = data => { const t=new Date(); t.setHours(0,0,0,0); return data.filter(i=>i.course&&i.date).map(i=>({...i, examDate:parseDate(i.date)})).filter(i=>i.examDate&&i.examDate>=t).sort((a,b)=>a.examDate-b.examDate); };

    const animateUpdate = fn => {
        if(animLock){ if(pending)clearTimeout(pending); animLock=false; fadeEls.forEach(e=>e.style.opacity='1'); }
        animLock=true; fadeEls.forEach(e=>e.style.opacity='0');
        pending=setTimeout(()=>{ fn(); requestAnimationFrame(()=>fadeEls.forEach(e=>e.style.opacity='1')); animLock=false; pending=null; }, FADE_DURATION);
    };

    const updateHint = () => { if(!hintCourseEl) return; const next = futureExams[(currentIdx+1)%futureExams.length]; hintCourseEl.textContent = futureExams.length ? next.course : '—'; };

    const refreshDisplay = () => {
        futureExams = filterFuture(rawExams);
        if(!futureExams.length){ normalView.style.display='none'; emptyView.style.display='block'; stopCarousel(); animateUpdate(()=>updateHint()); return; }
        normalView.style.display=''; emptyView.style.display='none'; currentIdx=Math.min(currentIdx, futureExams.length-1);
        const exam = futureExams[currentIdx], days = daysUntil(exam.date)??'?';
        animateUpdate(()=>{ courseEl.textContent=exam.course; daysEl.textContent=days; updateHint(); });
    };

    const nextExam = () => {
        if(!futureExams.length) return refreshDisplay();
        currentIdx=(currentIdx+1)%futureExams.length;
        const exam = futureExams[currentIdx], days = daysUntil(exam.date)??'?';
        animateUpdate(()=>{ courseEl.textContent=exam.course; daysEl.textContent=days; updateHint(); });
    };

    const stopCarousel = ()=> timer && clearInterval(timer);
    const startCarousel = ()=> { stopCarousel(); if(futureExams.length>1) timer=setInterval(nextExam, ROTATE_INTERVAL); };

    const fetchData = async ()=>{
        try{ const r=await fetch('/api/exams'); if(!r.ok) throw new Error(); const d=await r.json(); if(Array.isArray(d)) rawExams=d; }
        catch(e){ console.warn('模拟数据'); const d=new Date(), y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=d.getDate(); rawExams=[{course:'消化与内分泌系统Ⅱ',date:`2026-04-26`},{course:'心血管、呼吸、血液与泌尿系统Ⅱ',date:`2026-05-10`}]; }
        refreshDisplay(); startCarousel();
    };

    fadeEls.forEach(e=>e.style.opacity='1');
    fetchData();
    window.addEventListener('beforeunload', ()=>{ stopCarousel(); pending&&clearTimeout(pending); });
}

/**
 * 初始化题目导航
 */
function initQuestionNavigation() {
    // console.log('========== 题目导航初始化开始 ==========');
    
    // 0. 如果是考试页面，跳过题目导航初始化
    const examConfigElement = document.getElementById('examConfig');
    if (examConfigElement) {
        // console.log('检测到考试页面，跳过题目导航初始化');
        return;
    }
    
    // 1. 查找配置元素
    const configElement = document.getElementById('questionNavConfig');
    // console.log('步骤1: 查找配置元素');
    // console.log('配置元素:', configElement);
    
    if (!configElement) {
        console.error('❌ 错误: 未找到题目导航配置元素 #questionNavConfig');
        // console.log('当前页面URL:', window.location.href);
        // console.log('页面body前500字符:', document.body.innerHTML.substring(0, 500) + '...');
        return;
    }
    // console.log('✅ 找到配置元素');
    
    // 2. 解析基础配置数据
    // console.log('步骤2: 解析基础配置数据');
    const config = {
        bankId: parseInt(configElement.dataset.bankId) || 0,
        totalQuestions: parseInt(configElement.dataset.totalQuestions) || 0,
        correct: parseInt(configElement.dataset.correct) || 0,
        wrong: parseInt(configElement.dataset.wrong) || 0,
        unanswered: parseInt(configElement.dataset.unanswered) || 0
    };
    // console.log('基础配置:', config);
    
    if (config.bankId === 0 || config.totalQuestions === 0) {
        console.warn('⚠️ 警告: 题库ID或题目总数无效，跳过题目导航初始化');
        // console.log('bankId:', config.bankId, 'totalQuestions:', config.totalQuestions);
        return;
    }
    
    // 3. 查找并解析JSON数据script标签
    // console.log('步骤3: 查找并解析JSON数据script标签');
    try {
        // 查找script标签
        const dataScript = document.getElementById('questionDataScript');
        // console.log('数据script标签:', dataScript);
        
        if (!dataScript) {
            console.error('❌ 错误: 未找到JSON数据script标签 #questionDataScript');
            return;
        }
        
        // 解析script标签中的JSON
        const dataText = dataScript.textContent.trim();
        // console.log('原始JSON数据文本长度:', dataText.length);
        // console.log('原始JSON数据文本前200字符:', dataText.substring(0, 200));
        
        let questionData;
        try {
            questionData = JSON.parse(dataText);
            // console.log('✅ JSON数据解析成功');
        } catch (jsonError) {
            console.error('❌ JSON解析失败:', jsonError);
            console.error('JSON文本内容:', dataText);
            return;
        }
        
        const questionIdMapping = questionData.questionIdMapping || {};
        const userQuestionStatus = questionData.userQuestionStatus || { correct: [], wrong: [] };
        
        // console.log('✅ 题目ID映射数据解析成功, 长度:', Object.keys(questionIdMapping).length);
        // console.log('✅ 用户题目状态解析成功 - 正确:', userQuestionStatus.correct?.length || 0, '错误:', userQuestionStatus.wrong?.length || 0);
        
        // 4. 创建反向映射：order -> question_id
        // console.log('步骤4: 创建反向映射 order -> question_id');
        const orderToQuestionId = {};
        Object.entries(questionIdMapping).forEach(([questionIdStr, order]) => {
            const questionId = parseInt(questionIdStr);
            orderToQuestionId[order] = questionId;
        });
        // console.log('✅ 反向映射创建完成, 包含', Object.keys(orderToQuestionId).length, '个条目');
        
        // 5. 创建题目状态映射：question_id -> 状态
        // console.log('步骤5: 创建题目状态映射');
        const questionStatusMap = {};
        userQuestionStatus.correct?.forEach(id => {
            questionStatusMap[id] = 'correct';
        });
        userQuestionStatus.wrong?.forEach(id => {
            // 如果题目同时出现在correct和wrong中，优先显示correct
            if (!questionStatusMap[id]) {
                questionStatusMap[id] = 'incorrect'; // 注意: CSS中使用的是incorrect
            }
        });
        // console.log('✅ 状态映射创建完成, 正确:', userQuestionStatus.correct?.length || 0, '错误:', userQuestionStatus.wrong?.length || 0);
        
        // 6. 查找网格容器
        // console.log('步骤6: 查找网格容器');
        const gridContainer = document.getElementById('questionGridAll');
        // console.log('网格容器:', gridContainer);
        
        if (!gridContainer) {
            console.error('❌ 错误: 未找到网格容器 #questionGridAll');
            return;
        }
        
        // 清空容器
        gridContainer.innerHTML = '';
        // console.log('✅ 网格容器清空完成');
        
        // 7. 生成所有题目格子
        // console.log('步骤7: 生成所有题目格子');
        // console.log('总题数:', config.totalQuestions);
        
        let createdCount = 0;
        let correctCount = 0;
        let incorrectCount = 0;
        let unansweredCount = 0;
        
        for (let order = 1; order <= config.totalQuestions; order++) {
            const questionId = orderToQuestionId[order] || 0;
            
            // 确定题目状态
            let statusClass = 'unanswered';
            if (questionId && questionStatusMap[questionId]) {
                statusClass = questionStatusMap[questionId]; // 'correct' 或 'incorrect'
                if (statusClass === 'correct') correctCount++;
                else if (statusClass === 'incorrect') incorrectCount++;
            } else {
                unansweredCount++;
            }
            
            // 创建格子元素
            let gridElement;
            if (questionId) {
                // 有效题目：创建链接元素，支持AJAX导航
                gridElement = document.createElement('a');
                gridElement.href = `/questions/${questionId}?mode=sequential`;
                gridElement.dataset.page = 'question';
                gridElement.className = `question-grid-item ${statusClass} ajax-nav-link`;
            } else {
                // 无效题目：创建div元素，禁用点击
                gridElement = document.createElement('div');
                gridElement.className = `question-grid-item ${statusClass}`;
                gridElement.style.cursor = 'not-allowed';
                gridElement.style.opacity = '0.5';
            }
            
            // 设置公共属性
            gridElement.textContent = order;
            gridElement.dataset.order = order;
            gridElement.dataset.questionId = questionId;
            gridElement.dataset.bankId = config.bankId;
            gridElement.title = `第 ${order} 题 (${statusClass})`;
            
            gridContainer.appendChild(gridElement);
            createdCount++;
        }
        
        // console.log('✅ 题目格子生成完成');
        // console.log('生成统计: 总数=', createdCount, '正确=', correctCount, '错误=', incorrectCount, '未答=', unansweredCount);
        
        // 8. 验证网格布局
        // console.log('步骤8: 验证网格布局');
        // console.log('网格容器子元素数量:', gridContainer.children.length);
        // console.log('网格容器CSS类:', gridContainer.className);
        // console.log('网格容器计算样式:', window.getComputedStyle(gridContainer).display);
        
        // 触发淡入动画
        setTimeout(() => {
            gridContainer.classList.remove('fade-out');
            gridContainer.classList.add('fade-in');
            // console.log('✅ 淡入动画已触发');
        }, 100);
        
        // console.log('========== 题目导航初始化完成 ==========');
        
    } catch (error) {
        console.error('❌ 解析题目映射数据失败:', error);
        console.error('错误详情:', error.message);
        console.error('堆栈:', error.stack);
    }
}

/**
 * 导航到题目页
 */
function navigateToQuestion(bankId, questionId, order) {
    // 构建正确的题目URL
    const questionUrl = `/banks/${bankId}/questions/${questionId}?mode=sequential`;

    // 使用ajax导航系统（如果可用）
    if (typeof window.ajaxNavigateTo === 'function') {
        window.ajaxNavigateTo(questionUrl);
    } else if (typeof window.loadPage === 'function') {
        // 使用现有的ajax导航
        // 注意：需要检查loadPage函数期望的URL格式
        window.loadPage(`question-${bankId}-${questionId}`, 'question');
    } else {
        // 传统导航
        window.location.href = questionUrl;
    }
}

/**
 * 初始化重置历史按钮
 */
function initResetButton() {
    // 查找重置历史按钮
    const resetButtons = document.querySelectorAll('a[href*="/reset"]');
    
    resetButtons.forEach(button => {
        // 防止重复绑定
        if (button.dataset.resetHandlerBound) {
            return;
        }
        
        // 标记已绑定
        button.dataset.resetHandlerBound = 'true';
        
        // 移除ajax-nav-link类，防止AJAX导航器处理
        button.classList.remove('ajax-nav-link');
        
        // 添加点击事件监听器
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            // 提取题库ID
            const href = button.getAttribute('href');
            const match = href.match(/\/banks\/(\d+)\/reset/);
            if (!match) {
                console.error('无法从URL中提取题库ID:', href);
                return;
            }
            
            const bankId = match[1];
            
            // 显示确认对话框
            if (!confirm('确定要重置该题库的答题状态吗？Examcat 已为你保留错题记录，该操作只会将你的题目变成未答题状态。')) {
                return;
            }
            
            try {
                // 发送POST请求
                const response = await fetch(`/banks/${bankId}/reset`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // 显示成功消息
                    showResetMessage(`已成功重置答题历史，共重置 ${data.reset_count} 条记录`, 'success');
                    
                    // 1秒后通过AJAX重新加载首页以更新数据
                    setTimeout(() => {
                        if (typeof window.ajaxNavigateTo === 'function') {
                            window.ajaxNavigateTo('/');
                        } else if (typeof window.loadPage === 'function') {
                            window.loadPage('index', 'index');
                        } else {
                            // 如果AJAX导航不可用，回退到传统刷新
                            window.location.reload();
                        }
                    }, 1000);
                } else {
                    showResetMessage(`重置失败: ${data.message || '未知错误'}`, 'error');
                }
                
            } catch (error) {
                console.error('重置请求失败:', error);
                showResetMessage('重置时发生错误，请重试', 'error');
            }
        });
    });
}

/**
 * 显示重置消息
 */
function showResetMessage(message, type = 'info') {
    console.log(`显示重置消息 [${type}]: ${message}`);
    
    // 移除现有的消息
    document.querySelectorAll('.reset-message').forEach(msg => msg.remove());
    
    // 创建消息元素
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type === 'error' ? 'danger' : 'success'} reset-message`;
    messageDiv.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
        ${message}
    `;
    
    // 添加到页面顶部
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(messageDiv, container.firstChild);
        
        // 5秒后移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
}

// 页面首次加载时执行
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIndexPage);
} else {
    initIndexPage();
}

// 监听 AJAX 切换后的事件
window.addEventListener('page:content:updated', initIndexPage);