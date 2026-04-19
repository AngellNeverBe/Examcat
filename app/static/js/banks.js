/**
 * banks.js - 题库页面交互 (最终重构版)
 * 切换题库后只更新按钮状态，不重新加载页面
 */

// console.log('banks.js 加载成功 - 最终版本');

class BanksPage {
    constructor() {
        this.init();
    }
    
    init() {
        // console.log('BanksPage 初始化');
        this.setupEventDelegation();
        this.bindAdminActions();
    }
    
    /**
     * 设置事件委托 - 统一处理所有点击事件
     */
    setupEventDelegation() {
        // console.log('设置事件委托');
        
        // 处理切换题库按钮点击
        document.addEventListener('click', (e) => {
            const switchBtn = e.target.closest('.btn-switch-bank:not(:disabled)');
            if (switchBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                const bankId = switchBtn.dataset.bankId;
                // console.log(`点击切换题库按钮 - bank_id: ${bankId}`);
                this.switchBank(bankId);
                return;
            }
            
            // 处理下拉详情按钮点击
            const toggleBtn = e.target.closest('.btn-toggle-details');
            if (toggleBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                const bankId = toggleBtn.dataset.bankId;
                // console.log(`点击下拉按钮 - bank_id: ${bankId}`);
                this.toggleBankDetails(bankId);
                return;
            }
        });
    }
    
    /**
     * 切换题库 - 核心方法
     * 成功后只更新按钮状态，不重新加载页面
     */
    async switchBank(bankId) {
        // console.log(`开始切换题库 - bank_id: ${bankId}`);
        
        try {
            const formData = new FormData();
            formData.append('bank_id', bankId);
            
            const response = await fetch('/switch_bank', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            // console.log('切换题库响应:', data);
            
            if (data.success) {
                this.showMessage('题库切换成功', 'success');
                
                // 只更新按钮状态，不重新加载页面
                this.updateBankButtons(data.old_bank_id, data.bank_id);
                
            } else {
                console.error('题库切换失败:', data.error);
                this.showMessage(`切换失败: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('切换题库请求失败:', error);
            this.showMessage('切换题库时发生错误，请重试', 'error');
        }
    }
    
    /**
     * 更新按钮状态 - 核心更新逻辑
     */
    updateBankButtons(oldBankId, newBankId) {
        // console.log(`更新按钮状态 - 旧: ${oldBankId}, 新: ${newBankId}`);
        
        // 1. 找到旧的当前题库按钮（应该是一个disabled按钮）
        const oldCurrentBtn = this.findCurrentBankButton();
        
        if (oldCurrentBtn) {
            // 如果找到了旧的当前题库按钮，更新它
            // console.log(`找到旧的当前题库按钮: ${oldCurrentBtn.dataset.bankId}`);
            
            // 启用按钮
            oldCurrentBtn.disabled = false;
            // 更新文字
            oldCurrentBtn.textContent = '切换题库';
            // 移除current类
            oldCurrentBtn.classList.remove('current-bank-btn');
            // 确保data-bank-id存在
            oldCurrentBtn.dataset.bankId = oldBankId;
            
            // 更新对应卡片的current类
            const oldCard = oldCurrentBtn.closest('.bank-card');
            if (oldCard) {
                oldCard.classList.remove('current');
                oldCard.dataset.isCurrent = 'false';
            }
        } else {
            // console.log('未找到旧的当前题库按钮，可能页面状态异常');
        }
        
        // 2. 找到新的题库按钮（应该是可点击的切换按钮）
        const newCurrentBtn = document.querySelector(`.btn-switch-bank[data-bank-id="${newBankId}"]:not(:disabled)`);
        
        if (newCurrentBtn) {
            // console.log(`找到新的题库按钮: ${newCurrentBtn.dataset.bankId}`);
            
            // 禁用按钮
            newCurrentBtn.disabled = true;
            // 更新文字
            newCurrentBtn.textContent = '当前题库';
            // 添加current类
            newCurrentBtn.classList.add('current-bank-btn');
            // 确保data-bank-id存在
            newCurrentBtn.dataset.bankId = newBankId;
            
            // 更新对应卡片的current类
            const newCard = newCurrentBtn.closest('.bank-card');
            if (newCard) {
                newCard.classList.add('current');
                newCard.dataset.isCurrent = 'true';
            }
        } else {
            console.error(`未找到新的题库按钮: bank_id=${newBankId}`);
        }
        
        // console.log('按钮状态更新完成');
    }
    
    /**
     * 查找当前题库按钮（disabled状态）
     */
    findCurrentBankButton() {
        // 方法1：查找disabled的按钮
        const disabledBtn = document.querySelector('.btn-switch-bank:disabled');
        if (disabledBtn) return disabledBtn;
        
        // 方法2：查找有current-bank-btn类的按钮
        const currentBtn = document.querySelector('.btn-switch-bank.current-bank-btn');
        if (currentBtn) return currentBtn;
        
        // 方法3：查找文字为"当前题库"的按钮
        const buttons = document.querySelectorAll('.btn-switch-bank');
        for (const btn of buttons) {
            if (btn.textContent.trim() === '当前题库') {
                return btn;
            }
        }
        
        return null;
    }
    
    /**
     * 切换题库详情显示/隐藏
     */
    toggleBankDetails(bankId) {
        const detailsDiv = document.getElementById(`details-${bankId}`);
        const icon = document.querySelector(`.btn-toggle-details[data-bank-id="${bankId}"] i`);
        
        if (!detailsDiv) {
            console.error(`未找到详情区域 #details-${bankId}`);
            return;
        }
        
        if (detailsDiv.style.display === 'none' || !detailsDiv.style.display) {
            // 展开
            detailsDiv.style.display = 'block';
            if (icon) icon.style.transform = 'rotate(180deg)';
            // console.log(`展开题库 ${bankId} 的详情区域`);
        } else {
            // 收起
            detailsDiv.style.display = 'none';
            if (icon) icon.style.transform = 'rotate(0deg)';
            // console.log(`收起题库 ${bankId} 的详情区域`);
        }
    }
    
    /**
     * 绑定管理员功能
     */
    bindAdminActions() {
        // console.log('绑定管理员按钮事件');
        
        // 加载题库按钮
        const loadBtn = document.getElementById('btnLoadBanks');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => {
                // console.log('点击加载题库按钮');
                this.loadBanks();
            });
        }
        
        // 上传题库按钮
        const uploadBtn = document.getElementById('btnUploadBank');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                // console.log('点击上传题库按钮');
                this.triggerFileUpload();
            });
        }
        
        // 文件上传输入
        const fileInput = document.getElementById('bankFileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    // console.log(`选择文件: ${file.name}, 大小: ${file.size} bytes`);
                    this.uploadBank(file);
                }
            });
        }
    }
    
    /**
     * 加载题库
     */
    async loadBanks() {
        // console.log('开始加载题库流程');
        
        try {
            const response = await fetch('/load_bank', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            // console.log('加载题库响应:', data);
            
            if (data.status === 'success' || data.status === 'partial') {
                this.showMessage(data.message, data.status);
                // console.log('题库加载成功，3秒后重新加载页面');
                
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            } else {
                console.error('题库加载失败:', data.message);
                this.showMessage(data.message || '加载题库失败', 'error');
            }
            
        } catch (error) {
            console.error('加载题库请求失败:', error);
            this.showMessage('加载题库时发生错误', 'error');
        }
    }
    
    /**
     * 触发文件上传
     */
    triggerFileUpload() {
        // console.log('触发文件上传对话框');
        const fileInput = document.getElementById('bankFileInput');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    /**
     * 上传题库文件
     */
    async uploadBank(file) {
        // console.log(`开始上传题库文件: ${file.name}`);
        
        const formData = new FormData();
        formData.append('bank_file', file);
        
        try {
            const response = await fetch('/upload_bank', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            // console.log('上传题库响应:', data);
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                // console.log('题库上传成功，3秒后重新加载页面');
                
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
            } else {
                console.error('题库上传失败:', data.message);
                this.showMessage(data.message || '上传失败', 'error');
            }
            
        } catch (error) {
            console.error('上传题库请求失败:', error);
            this.showMessage('上传题库时发生错误', 'error');
        }
    }
    
    /**
     * 显示消息
     */
    showMessage(message, type = 'info') {
        // console.log(`显示消息 [${type}]: ${message}`);
        
        // 移除现有的消息
        document.querySelectorAll('.flash-message').forEach(msg => msg.remove());
        
        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} flash-message`;
        messageDiv.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
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
}

// 全局初始化
document.addEventListener('DOMContentLoaded', () => {
    // console.log('DOM加载完成，初始化BanksPage');
    try {
        window.banksPage = new BanksPage();
        // console.log('BanksPage 初始化成功');
    } catch (error) {
        console.error('BanksPage 初始化失败:', error);
    }
});

// 确保在AJAX导航器之后执行
if (document.readyState === 'loading') {
    // console.log('文档仍在加载中，等待DOMContentLoaded事件');
} else {
    // console.log('文档已准备就绪，立即初始化');
    try {
        window.banksPage = new BanksPage();
        // console.log('BanksPage 立即初始化成功');
    } catch (error) {
        console.error('BanksPage 立即初始化失败:', error);
    }
}

// 导出全局访问
window.BanksPage = BanksPage;
// console.log('banks.js 加载完成 - 使用局部更新策略');