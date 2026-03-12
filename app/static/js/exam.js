// 配置管理器
const ExamConfig = (function() {
    // 默认配置
    const defaultConfig = {
        examId: 0,
        totalQuestions: 0,
        elapsedTime: 0,
        examCompleted: false,
        saveUrl: '',
        showExamsUrl: ''
    };
    
    // 从data属性获取配置
    function getConfigFromDataAttributes() {
        const configElement = document.getElementById('examConfig');
        if (!configElement) {
            console.warn('考试配置元素未找到，使用默认配置');
            return defaultConfig;
        }
        
        const dataset = configElement.dataset;
        
        // 解析配置，处理数据类型转换
        return {
            examId: parseInt(dataset.examId) || 0,
            totalQuestions: parseInt(dataset.totalQuestions) || 0,
            elapsedTime: parseInt(dataset.elapsedTime) || 0,
            examCompleted: dataset.examCompleted === '1' || dataset.examCompleted === 'true',
            saveUrl: dataset.saveUrl || '',
            showExamsUrl: dataset.showExamsUrl || ''
        };
    }
    
    // 获取配置（单例模式）
    let config = null;
    
    return {
        getConfig: function() {
            if (!config) {
                config = getConfigFromDataAttributes();
            }
            return config;
        },
        
        // 重新加载配置（如果需要）
        reloadConfig: function() {
            config = getConfigFromDataAttributes();
            return config;
        }
    };
})();

// 使用配置
const config = ExamConfig.getConfig();

// 计时器功能
let totalSeconds = config.elapsedTime;
let timerInterval;

function startTimer() {
    if (config.examCompleted) return;
    
    timerInterval = setInterval(() => {
        totalSeconds++;
        updateTimerDisplay();
        // 每60秒自动保存一次
        if (totalSeconds % 60 === 0) {
            autoSave();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    document.getElementById('timerDisplay').textContent = 
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// 生成题目导航格子
function generateQuestionGrid() {
    const grid = document.getElementById('questionGrid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    for (let i = 1; i <= config.totalQuestions; i++) {
        const gridItem = document.createElement('div');
        gridItem.className = 'question-grid-item unanswered';
        gridItem.textContent = i;
        gridItem.dataset.index = i;
        
        gridItem.addEventListener('click', () => {
            scrollToQuestion(i);
            updateCurrentQuestion(i);
        });
        
        grid.appendChild(gridItem);
    }
    
    // 初始化当前题目为第一个
    updateCurrentQuestion(1);
}

function updateQuestionGridStatus(questionIndex, status) {
    const gridItem = document.querySelector(`.question-grid-item[data-index="${questionIndex}"]`);
    if (!gridItem) return;
    
    // 如果状态是 'current'，只添加 current 类，不影响其他状态
    if (status === 'current') {
        // 移除所有格子的 current 类
        document.querySelectorAll('.question-grid-item').forEach(item => {
            item.classList.remove('current');
        });
        // 为当前格子添加 current 类
        gridItem.classList.add('current');
        return;
    }
    
    // 对于其他状态（answered/unanswered/correct/incorrect）
    // 移除所有状态类（除了 current）
    gridItem.classList.remove('unanswered', 'answered', 'correct', 'incorrect');
    
    // 添加新状态类
    gridItem.classList.add(status);
}

function updateCurrentQuestion(questionIndex) {
    // 移除所有格子的当前标记
    document.querySelectorAll('.question-grid-item').forEach(item => {
        item.classList.remove('current');
    });
    
    // 标记当前题目 - 只添加 current 类，不影响其他状态
    const gridItem = document.querySelector(`.question-grid-item[data-index="${questionIndex}"]`);
    if (gridItem) {
        gridItem.classList.add('current');
    }
    
    // 更新对应题目容器的样式
    document.querySelectorAll('.question-container').forEach(container => {
        container.classList.remove('current-question');
    });
    
    const currentQuestion = document.getElementById(`question-${questionIndex}`);
    if (currentQuestion) {
        currentQuestion.classList.add('current-question');
    }
}

function scrollToQuestion(questionIndex) {
    const element = document.getElementById(`question-${questionIndex}`);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// 设置选项卡片点击事件
function setupOptionCards() {
    const form = document.getElementById('examForm');
    if (!form || config.examCompleted) return;
    
    const optionCards = document.querySelectorAll('.option-card');
    
    optionCards.forEach(card => {
        card.addEventListener('click', function() {
            if (config.examCompleted) return;
            
            const questionId = this.dataset.questionId;
            const optionKey = this.dataset.optionKey;
            const questionType = this.dataset.questionType; // 获取题目类型
            const questionElement = this.closest('.question-container');
            const questionIndex = questionElement ? questionElement.id.replace('question-', '') : null;
            const hiddenInput = document.getElementById(`answer_${questionId}`);
            
            if (!hiddenInput || !questionIndex) return;
            
            let currentAnswer = hiddenInput.value ? hiddenInput.value.split('') : [];
            
            // 根据题目类型处理选择逻辑
            if (questionType === '单选题') {
                // 单选题：清除所有选中状态，设置当前选项
                const allCards = questionElement.querySelectorAll('.option-card');
                allCards.forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                currentAnswer = [optionKey];
            } else {
                // 多选题：切换选中状态
                if (this.classList.contains('selected')) {
                    this.classList.remove('selected');
                    currentAnswer = currentAnswer.filter(key => key !== optionKey);
                } else {
                    this.classList.add('selected');
                    currentAnswer.push(optionKey);
                }
                // 去重并排序（保持答案顺序一致）
                currentAnswer = [...new Set(currentAnswer)].sort();
            }
            
            // 更新隐藏输入字段
            hiddenInput.value = currentAnswer.join('');
            
            // 更新导航格子状态 - 保持已有的 current 状态
            const gridItem = document.querySelector(`.question-grid-item[data-index="${questionIndex}"]`);
            if (gridItem) {
                // 移除所有状态类（除了 current）
                gridItem.classList.remove('unanswered', 'answered', 'correct', 'incorrect');
                
                // 根据是否有答案设置状态
                if (currentAnswer.length > 0) {
                    gridItem.classList.add('answered');
                } else {
                    gridItem.classList.add('unanswered');
                }
                
                // 如果这个格子当前有 current 类，保持它
                if (gridItem.classList.contains('current')) {
                    // current 类已经存在，不需要额外操作
                }
            }
        });
    });
}

// 设置鼠标悬停检测当前题目
function setupMouseHoverDetection() {
    const questionContainers = document.querySelectorAll('.question-container');
    
    questionContainers.forEach(container => {
        container.addEventListener('mouseenter', function() {
            if (config.examCompleted) return;
            
            const questionIndex = parseInt(this.id.replace('question-', ''));
            if (!isNaN(questionIndex) && questionIndex >= 1 && questionIndex <= config.totalQuestions) {
                updateCurrentQuestion(questionIndex);
            }
        });
    });
}

// 自动保存
function autoSave() {
    if (config.examCompleted) return;
    
    const form = document.getElementById('examForm');
    if (!form) return;
    
    const formData = new FormData(form);
    formData.append('action', 'save');
    formData.append('elapsed_time', totalSeconds);
    
    // 检查是否有保存按钮处于保存中状态
    const savingButtons = document.querySelectorAll('button[value="save"].saving');
    if (savingButtons.length > 0) {
        // 如果有按钮正在保存，跳过本次自动保存
        return;
    }
    
    fetch(config.saveUrl, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('自动保存成功');
            // 静默更新导航格子状态
            updateAllGridStatuses();
        }
    })
    .catch(error => {
        console.error('自动保存失败:', error);
    });
}

// 表单提交处理
function setupFormSubmit() {
    const form = document.getElementById('examForm');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        if (config.examCompleted) {
            e.preventDefault();
            return;
        }
        
        // 获取触发提交的元素
        const submitter = e.submitter;
        if (!submitter) return;
        
        const action = submitter.value;
        
        // 如果是保存按钮，已经被AJAX拦截，这里阻止默认提交
        if (action === 'save') {
            e.preventDefault();
            return;
        }
        
        // 如果是提交按钮，添加确认提示
        if (action === 'submit') {
            const confirmed = confirm('确定要提交考试吗？提交后将无法修改答案。');
            if (!confirmed) {
                e.preventDefault();
                return;
            }
            // 提交按钮允许正常表单提交（会刷新页面）
        }
    });
}

// 初始化页面状态
function initializePageState() {
    // 检查已有答案的题目并更新格子状态
    const form = document.getElementById('examForm');
    if (!form) return;
    
    for (let i = 1; i <= config.totalQuestions; i++) {
        const questionElement = document.getElementById(`question-${i}`);
        if (!questionElement) continue;
        
        // 查找该题目的隐藏输入字段（存储答案）
        const hiddenInput = questionElement.querySelector('input[type="hidden"]');
        let hasAnswer = false;
        
        if (hiddenInput && hiddenInput.value.trim() !== '') {
            // 有答案内容，说明已经作答
            hasAnswer = true;
            
            // 同时更新选项卡片的选中状态
            const answerKeys = hiddenInput.value.split('');
            answerKeys.forEach(key => {
                const optionCard = questionElement.querySelector(`.option-card[data-option-key="${key}"]`);
                if (optionCard) {
                    optionCard.classList.add('selected');
                }
            });
        }
        
        // 更新导航格子状态
        if (hasAnswer) {
            updateQuestionGridStatus(i, 'answered');
        }
        
        // 如果考试已完成，根据正确性更新格子状态
        if (config.examCompleted) {
            // 优先使用 data-is-correct 属性
            const questionContainer = document.getElementById(`question-${i}`);
            if (questionContainer) {
                const isCorrectAttr = questionContainer.getAttribute('data-is-correct');
                if (isCorrectAttr !== null) {
                    if (isCorrectAttr === '1') {
                        updateQuestionGridStatus(i, 'correct');
                    } else {
                        updateQuestionGridStatus(i, 'incorrect');
                    }
                }
            }
        }
    }
}

// 处理保存按钮的AJAX请求
function setupSaveButton() {
    const saveButtons = document.querySelectorAll('button[value="save"]');
    
    saveButtons.forEach(button => {
        // 添加自定义类名
        button.classList.add('btn-save-progress');
        
        // 保存原始状态
        const originalHTML = button.innerHTML;
        const originalClasses = button.className;
        
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            
            if (config.examCompleted) return;
            
            const form = document.getElementById('examForm');
            if (!form) return;
            
            // 收集表单数据
            const formData = new FormData(form);
            formData.append('action', 'save');
            formData.append('elapsed_time', totalSeconds);
            
            // 状态1：保存中
            button.disabled = true;
            button.classList.remove('success');
            button.classList.add('saving');
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 保存中...';
            
            try {
                // 发送AJAX请求
                const response = await fetch(config.saveUrl, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // 状态2：保存成功
                    button.classList.remove('saving');
                    button.classList.add('success');
                    button.innerHTML = '<i class="fas fa-check"></i> 保存成功';
                    
                    // 更新导航格子状态
                    updateAllGridStatuses();
                    
                    // 状态3：1秒后恢复原状
                    setTimeout(() => {
                        button.classList.remove('success');
                        button.disabled = false;
                        button.innerHTML = originalHTML;
                    }, 1000);
                    
                } else {
                    throw new Error(data.message || '保存失败');
                }
            } catch (error) {
                console.error('保存失败:', error);
                
                // 恢复原始状态
                button.classList.remove('saving');
                button.disabled = false;
                button.innerHTML = originalHTML;
                
                // 可选：显示简单错误提示（如果不想要任何消息，可以注释掉）
                const errorSpan = document.createElement('span');
                errorSpan.className = 'text-danger ml-2';
                errorSpan.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
                errorSpan.title = error.message;
                button.appendChild(errorSpan);
                
                // 3秒后移除错误图标
                setTimeout(() => {
                    if (errorSpan.parentNode) {
                        errorSpan.parentNode.removeChild(errorSpan);
                    }
                }, 3000);
            }
        });
    });
}

// 新增：更新所有导航格子状态
function updateAllGridStatuses() {
    const form = document.getElementById('examForm');
    if (!form) return;
    
    for (let i = 1; i <= config.totalQuestions; i++) {
        const questionElement = document.getElementById(`question-${i}`);
        if (!questionElement) continue;
        
        // 查找该题目的隐藏输入字段
        const hiddenInput = questionElement.querySelector('input[type="hidden"]');
        const gridItem = document.querySelector(`.question-grid-item[data-index="${i}"]`);
        
        if (!gridItem || !hiddenInput) continue;
        
        // 移除所有状态类（除了current）
        gridItem.classList.remove('unanswered', 'answered', 'correct', 'incorrect');
        
        // 根据答案状态添加相应类
        if (hiddenInput.value && hiddenInput.value.trim() !== '') {
            gridItem.classList.add('answered');
        } else {
            gridItem.classList.add('unanswered');
        }
        
        // 保持current类
        if (gridItem.classList.contains('current')) {
            // 已经存在current类，无需操作
        }
    }
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 重新加载配置
    ExamConfig.reloadConfig();
    
    // 初始化计时器
    updateTimerDisplay();
    if (!config.examCompleted) {
        startTimer();
    }
    
    // 生成题目导航
    generateQuestionGrid();
    
    // 设置选项卡片事件
    setupOptionCards();

    // 设置保存按钮的AJAX处理
    setupSaveButton();
    
    // 设置表单提交
    setupFormSubmit();
    
    // 初始化页面状态
    initializePageState();
    
    // 设置鼠标悬停检测当前题目
    setupMouseHoverDetection();
    
    // 页面离开时提示
    window.addEventListener('beforeunload', function(e) {
        if (!config.examCompleted) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});