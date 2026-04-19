// user.js - 用户中心页面交互功能 (重构版，类似banks.js)

console.log('user.js 加载成功 - 重构版');

class UserProfile {
    constructor() {
        this.initialized = false;
        this.handleSidebarNavClick = this.handleSidebarNavClick.bind(this);
        this.handleUserContentClick = this.handleUserContentClick.bind(this);
        this.activateTabFromHash = this.activateTabFromHash.bind(this);
        this.handleAjaxPageUpdated = this.handleAjaxPageUpdated.bind(this);
        this.init();
    }
    
    init() {
        console.log('UserProfile 初始化');
        
        // 检查是否在用户页面中
        const userProfileContainer = document.querySelector('.user-profile-container');
        if (!userProfileContainer) {
            console.log('不在用户页面，退出初始化');
            return;
        }
        
        // 防止重复初始化
        if (this.initialized) {
            this.cleanup();
        }
        
        console.log('初始化用户中心页面');
        
        // 初始化侧边栏导航
        this.initSidebarNavigation();
        
        // 初始化按钮事件
        this.initButtonEvents();
        
        // 设置默认激活的标签页
        this.activateTabFromHash();
        
        // 监听hash变化（用于浏览器前进/后退）
        window.addEventListener('hashchange', this.activateTabFromHash);
        
        // 监听 AJAX 页面更新事件
        window.addEventListener('ajax:page:updated', this.handleAjaxPageUpdated);
        
        this.initialized = true;
    }
    
    /**
     * 清理用户中心页面状态
     */
    cleanup() {
        console.log('清理用户中心页面状态');
        
        // 移除hashchange事件监听器
        window.removeEventListener('hashchange', this.activateTabFromHash);
        
        // 移除 AJAX 页面更新事件监听器
        window.removeEventListener('ajax:page:updated', this.handleAjaxPageUpdated);
        
        // 移除侧边栏导航事件监听器
        const sidebarNav = document.querySelector('.sidebar-nav');
        if (sidebarNav && sidebarNav.dataset.ajaxBound) {
            sidebarNav.removeEventListener('click', this.handleSidebarNavClick);
            delete sidebarNav.dataset.ajaxBound;
        }
        
        // 移除按钮事件监听器
        const userContent = document.querySelector('.user-content');
        if (userContent && userContent.dataset.buttonEventsBound) {
            userContent.removeEventListener('click', this.handleUserContentClick);
            delete userContent.dataset.buttonEventsBound;
        }
        
        this.initialized = false;
    }
    
    /**
     * 初始化侧边栏导航（使用事件委托，避免重复绑定）
     */
    initSidebarNavigation() {
        const sidebarNav = document.querySelector('.sidebar-nav');
        if (!sidebarNav) return;
        
        // 如果已经绑定了事件，先移除旧的事件监听器
        if (sidebarNav.dataset.ajaxBound) {
            sidebarNav.removeEventListener('click', this.handleSidebarNavClick);
        }
        
        // 使用事件委托处理侧边栏导航点击
        sidebarNav.addEventListener('click', this.handleSidebarNavClick);
        sidebarNav.dataset.ajaxBound = 'true';
    }
    
    /**
     * 处理侧边栏导航点击事件
     */
    handleSidebarNavClick(e) {
        const navLink = e.target.closest('.nav-link');
        if (!navLink) return;
        
        e.preventDefault();
        
        const tabId = navLink.getAttribute('data-tab');
        if (tabId) {
            // 更新URL hash（不触发页面跳转）
            window.location.hash = tabId;
            
            // 激活选中的标签页
            this.activateTab(tabId);
            
            // 更新导航链接激活状态
            this.updateNavActiveState(navLink);
        }
    }
    
    /**
     * 激活指定的标签页
     * @param {string} tabId - 标签页ID（不带#前缀）
     */
    activateTab(tabId) {
        // 隐藏所有标签页内容
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
        });
        
        // 显示选中的标签页内容
        const activeTab = document.getElementById(`${tabId}-tab`);
        if (activeTab) {
            activeTab.classList.add('active');
            
            // 如果标签页有特定的初始化函数，调用它
            if (typeof this[`init${this.capitalizeFirstLetter(tabId)}Tab`] === 'function') {
                this[`init${this.capitalizeFirstLetter(tabId)}Tab`]();
            }
        } else {
            console.warn(`标签页 ${tabId}-tab 未找到`);
        }
    }
    
    /**
     * 从URL hash激活标签页
     */
    activateTabFromHash() {
        const hash = window.location.hash.substring(1); // 去掉#前缀
        const validTabs = ['profile', 'replies', 'statistics', 'favorites', 'wrong'];
        
        console.log('activateTabFromHash: 当前hash =', hash, '完整URL =', window.location.href);
        
        let tabId = 'profile'; // 默认标签页
        
        if (hash && validTabs.includes(hash)) {
            tabId = hash;
            console.log('activateTabFromHash: 激活标签页', tabId);
        } else {
            console.log('activateTabFromHash: 使用默认标签页', tabId);
        }
        
        // 激活标签页
        this.activateTab(tabId);
        
        // 更新对应的导航链接激活状态
        const correspondingLink = document.querySelector(`.nav-link[data-tab="${tabId}"]`);
        if (correspondingLink) {
            this.updateNavActiveState(correspondingLink);
            console.log('activateTabFromHash: 更新导航链接激活状态', tabId);
        } else {
            console.warn('activateTabFromHash: 未找到对应的导航链接', tabId);
        }
    }
    
    /**
     * 更新导航链接激活状态
     * @param {HTMLElement} activeLink - 当前激活的链接元素
     */
    updateNavActiveState(activeLink) {
        // 移除所有链接的激活状态
        const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // 添加当前链接的激活状态
        activeLink.classList.add('active');
    }
    
    /**
     * 处理 AJAX 页面更新事件
     * @param {Event} event - ajax:page:updated 事件
     */
    handleAjaxPageUpdated(event) {
        console.log('UserProfile: 处理 ajax:page:updated 事件', event.detail);
        
        const page = event.detail?.page;
        if (page === 'user') {
            console.log('检测到用户页面 AJAX 更新，激活标签页');
            
            // 延迟执行，确保DOM完全更新
            setTimeout(() => {
                this.activateTabFromHash();
            }, 50);
        }
    }
    
    /**
     * 初始化按钮事件（使用事件委托）
     */
    initButtonEvents() {
        const userContent = document.querySelector('.user-content');
        if (!userContent) return;
        
        // 如果已经绑定了事件，先移除旧的事件监听器
        if (userContent.dataset.buttonEventsBound) {
            userContent.removeEventListener('click', this.handleUserContentClick);
        }
        
        // 使用事件委托处理用户内容区域的点击事件
        userContent.addEventListener('click', this.handleUserContentClick);
        userContent.dataset.buttonEventsBound = 'true';
    }
    
    /**
     * 处理用户内容区域点击事件
     */
    handleUserContentClick(e) {
        // 编辑资料按钮
        const editProfileBtn = e.target.closest('.profile-actions .btn-primary');
        if (editProfileBtn) {
            e.preventDefault();
            alert('编辑资料功能正在开发中，敬请期待！');
            return;
        }
        
        // 修改密码按钮
        const changePasswordBtn = e.target.closest('.profile-actions .btn-outline-secondary');
        if (changePasswordBtn) {
            e.preventDefault();
            alert('修改密码功能正在开发中，敬请期待！');
            return;
        }
        
        // 前往统计页面按钮
        const goToStatsBtn = e.target.closest('a[href*="statistics.show"]');
        if (goToStatsBtn) {
            // 如果是在AJAX导航中，可能需要特殊处理
            if (window.ajaxNavigator && window.ajaxNavigator.isActive()) {
                e.preventDefault();
                window.ajaxNavigator.navigateTo('/ajax/statistics');
            }
            // 否则正常跳转
            return;
        }
        
        // 前往收藏页面按钮
        const goToFavoritesBtn = e.target.closest('a[href*="favorites.show"]');
        if (goToFavoritesBtn) {
            // 如果是在AJAX导航中，可能需要特殊处理
            if (window.ajaxNavigator && window.ajaxNavigator.isActive()) {
                e.preventDefault();
                window.ajaxNavigator.navigateTo('/ajax/favorites');
            }
            // 否则正常跳转
            return;
        }
    }
    
    /**
     * 初始化个人资料标签页
     */
    initProfileTab() {
        // 个人资料标签页特定的初始化代码
        console.log('个人资料标签页已激活');
    }
    
    /**
     * 初始化我的回复标签页
     */
    initRepliesTab() {
        // 我的回复标签页特定的初始化代码
        console.log('我的回复标签页已激活');
    }
    
    /**
     * 初始化学习统计标签页
     */
    initStatisticsTab() {
        // 学习统计标签页特定的初始化代码
        console.log('学习统计标签页已激活');
    }
    
    /**
     * 初始化我的收藏标签页
     */
    initFavoritesTab() {
        // 我的收藏标签页特定的初始化代码
        console.log('我的收藏标签页已激活');
    }
    
    /**
     * 初始化我的错题标签页
     */
    initWrongTab() {
        // 我的错题标签页特定的初始化代码
        console.log('我的错题标签页已激活');
    }
    
    /**
     * 辅助函数：首字母大写
     */
    capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
}

// 全局初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM加载完成，初始化UserProfile');
    try {
        window.userProfile = new UserProfile();
        console.log('UserProfile 初始化成功');
    } catch (error) {
        console.error('UserProfile 初始化失败:', error);
    }
});

// 确保在AJAX导航器之后执行
if (document.readyState === 'loading') {
    console.log('文档仍在加载中，等待DOMContentLoaded事件');
} else {
    console.log('文档已准备就绪，立即初始化');
    try {
        window.userProfile = new UserProfile();
        console.log('UserProfile 立即初始化成功');
    } catch (error) {
        console.error('UserProfile 立即初始化失败:', error);
    }
}



// 导出全局访问
window.UserProfile = UserProfile;
console.log('user.js 加载完成 - 使用类模式');

// 监听 AJAX 页面更新事件，确保用户页面标签页正确激活
window.addEventListener('ajax:page:updated', function(event) {
    console.log('ajax:page:updated 事件触发，detail:', event.detail);
    
    const page = event.detail?.page;
    console.log('页面标识:', page);
    
    // 如果是用户页面
    if (page === 'user') {
        console.log('检测到用户页面更新，确保 UserProfile 正确初始化');
        
        // 确保 UserProfile 实例存在
        if (!window.userProfile) {
            console.log('UserProfile 实例不存在，创建新实例');
            try {
                window.userProfile = new UserProfile();
            } catch (error) {
                console.error('创建 UserProfile 实例失败:', error);
                return;
            }
        }
        
        // 检查是否在用户页面容器中
        const userProfileContainer = document.querySelector('.user-profile-container');
        if (!userProfileContainer) {
            console.log('用户页面容器未找到，可能不在用户页面');
            return;
        }
        
        // 检查 UserProfile 是否已初始化
        if (!window.userProfile.initialized) {
            console.log('UserProfile 未初始化，调用 init()');
            window.userProfile.init();
        }
        // 如果已初始化，确保事件监听器已设置
        else {
            console.log('UserProfile 已初始化');
        }
    }
});