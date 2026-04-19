// base.js - Base template 功能

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有基础功能
    initAjax();
    initMobileMenu();
    initFlashMessages();
    initNotransFlashMessages();
    initTableFeatures();
    initDeviceDetection();
    initNav();
    initUserBar();
});
/**
 * 初始化Ajax管理内容区域
 */
function initAjax() {
    window.ajaxNavigator = new AjaxNavigator();
}

/**
 * 初始化移动端菜单功能
 */
function initMobileMenu() {
    const menuToggle = document.getElementById('menuToggle');
    const navLinks = document.getElementById('navLinks');
    const menuBackdrop = document.getElementById('menuBackdrop');
    const body = document.body;
    
    if (!menuToggle || !navLinks || !menuBackdrop) return;
    
    // 移动端菜单切换
    menuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleMobileMenu();
    });
    
    // 点击背景遮罩关闭菜单
    menuBackdrop.addEventListener('click', closeMobileMenu);
    
    // 点击其他区域关闭菜单
    document.addEventListener('click', function(e) {
        if (navLinks.classList.contains('mobile-active') && 
            !navLinks.contains(e.target) && 
            e.target !== menuToggle &&
            !menuBackdrop.contains(e.target)) {
            closeMobileMenu();
        }
    });
    
    // ESC键关闭菜单
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && navLinks.classList.contains('mobile-active')) {
            closeMobileMenu();
        }
    });
    
    // 监听窗口大小变化
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && navLinks.classList.contains('mobile-active')) {
            closeMobileMenu();
        }
    });
    
    // 菜单切换函数
    function toggleMobileMenu() {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            const isActive = navLinks.classList.toggle('mobile-active');
            updateMenuIcon(isActive);
            
            if (isActive) {
                menuBackdrop.classList.add('active');
                body.style.overflow = 'hidden';
            } else {
                menuBackdrop.classList.remove('active');
                body.style.overflow = '';
            }
        }
    }
    
    // 关闭菜单函数
    function closeMobileMenu() {
        navLinks.classList.remove('mobile-active');
        menuBackdrop.classList.remove('active');
        updateMenuIcon(false);
        body.style.overflow = '';
    }
    
    // 更新菜单图标
    function updateMenuIcon(isActive) {
        const icon = menuToggle.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-bars', !isActive);
            icon.classList.toggle('fa-times', isActive);
        }
    }
    
    // 点击菜单项关闭菜单（移动端）
    const navLinksItems = document.querySelectorAll('.nav-link');
    navLinksItems.forEach(item => {
        item.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeMobileMenu();
            }
        });
    });
}

/**
 * 切换菜单状态
 */
function toggleMenu(navLinks, menuToggle, menuBackdrop, body) {
    const isActive = navLinks.classList.toggle('active');
    updateMenuIcon(menuToggle, isActive);
    
    if (isActive) {
        menuBackdrop.classList.add('active');
        if (window.innerWidth <= 768) {
            body.style.overflow = 'hidden';
        }
    } else {
        menuBackdrop.classList.remove('active');
        body.style.overflow = '';
    }
}

/**
 * 关闭菜单
 */
function closeMenu(navLinks, menuToggle, menuBackdrop, body) {
    navLinks.classList.remove('active');
    menuBackdrop.classList.remove('active');
    updateMenuIcon(menuToggle, false);
    body.style.overflow = '';
}

/**
 * 更新菜单图标
 */
function updateMenuIcon(menuToggle, isActive) {
    const icon = menuToggle.querySelector('i');
    if (icon) {
        if (isActive) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
        } else {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    }
}

/**
 * 初始化滑动支持
 */
function initSwipeSupport(navLinks, menuToggle, menuBackdrop, body) {
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, false);
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe(navLinks, menuToggle, menuBackdrop, body);
    }, false);
    
    function handleSwipe() {
        const swipeThreshold = 100;
        
        if (window.innerWidth <= 768) {
            // 从左往右滑动，打开菜单
            if (touchEndX - touchStartX > swipeThreshold) {
                if (!navLinks.classList.contains('active')) {
                    toggleMenu(navLinks, menuToggle, menuBackdrop, body);
                }
            }
            
            // 从右往左滑动，关闭菜单
            if (touchStartX - touchEndX > swipeThreshold) {
                if (navLinks.classList.contains('active')) {
                    closeMenu(navLinks, menuToggle, menuBackdrop, body);
                }
            }
        }
    }
}

/**
 * 初始化Flash消息功能
 */
function initFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // 添加关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.className = 'alert-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.setAttribute('aria-label', '关闭消息');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            margin-left: auto;
            color: inherit;
            opacity: 0.7;
        `;
        
        closeBtn.addEventListener('click', function() {
            fadeOutAlert(alert);
        });
        
        alert.appendChild(closeBtn);
        
        // 5秒后自动消失
        setTimeout(() => {
            fadeOutAlert(alert);
        }, 5000);
    });
}

function initNotransFlashMessages() {
    const alerts = document.querySelectorAll('.alert-notrans');
    alerts.forEach(alert => {
        // 添加关闭按钮
        const closeBtn = document.createElement('button');
        closeBtn.className = 'alert-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.setAttribute('aria-label', '关闭消息');
        closeBtn.style.cssText = `
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            margin-left: auto;
            color: inherit;
            opacity: 0.7;
        `;
        
        closeBtn.addEventListener('click', function() {
            fadeOutAlert(alert);
        });
        
        alert.appendChild(closeBtn);
    });
}

/**
 * 淡出警告消息
 */
function fadeOutAlert(alert) {
    alert.style.opacity = '0';
    alert.style.transition = 'opacity 0.5s ease';
    
    setTimeout(() => {
        alert.style.display = 'none';
    }, 500);
}

/**
 * 初始化设备检测
 */
function initDeviceDetection() {
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile) {
        document.body.classList.add('mobile-device');
    }
}

/**
 * 初始化表格功能
 */
function initTableFeatures() {
    const tableContainers = document.querySelectorAll('.table-container');
    
    tableContainers.forEach(container => {
        // 添加移动端滚动提示
        if (window.innerWidth <= 768 && !container.querySelector('.table-scroll-hint')) {
            const hint = document.createElement('div');
            hint.className = 'table-scroll-hint';
            hint.innerHTML = '<i class="fas fa-arrows-left-right"></i> 左右滑动查看更多';
            container.insertBefore(hint, container.firstChild);
        }
        
        // 检查表格是否可滚动
        function checkScrollable() {
            if (container.scrollWidth > container.clientWidth) {
                container.classList.add('is-scrollable');
            } else {
                container.classList.remove('is-scrollable');
            }
        }
        
        // 初始检查
        checkScrollable();
        
        // 监听窗口大小变化
        window.addEventListener('resize', checkScrollable);
        
        // 处理滚动指示器
        container.addEventListener('scroll', function() {
            const scrollLeft = container.scrollLeft;
            const maxScroll = container.scrollWidth - container.clientWidth;
            
            if (scrollLeft >= maxScroll - 5) {
                container.classList.add('scrolled-end');
            } else {
                container.classList.remove('scrolled-end');
            }
        });
    });
    
    // 处理卡片式移动表格
    const cardTables = document.querySelectorAll('.table.table-card-mobile');
    cardTables.forEach(table => {
        // 获取表头内容
        const headerCells = table.querySelectorAll('thead th');
        const headerTexts = Array.from(headerCells).map(cell => cell.textContent.trim());
        
        // 为数据单元格添加data-label属性
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index < headerTexts.length) {
                    cell.setAttribute('data-label', headerTexts[index]);
                }
            });
        });
    });
}

function initNav() {
    // ======== 导航栏 ========
    const nav = document.querySelector('nav');
  
    // 滚动相关变量
    let lastScrollTop = 0;
    let isScrollingDown = false;
    let scrollTimeout;
    const SCROLL_THRESHOLD = 30; // 滚动阈值，避免微小滚动触发
    const TOP_THRESHOLD = 10; // 页面顶部阈值
    
    // 节流函数，优化滚动性能
    function throttle(func, wait) {
        let timeout = null;
        let previous = 0;
        
        return function() {
        const now = Date.now();
        const remaining = wait - (now - previous);
        const context = this;
        const args = arguments;
        
        if (remaining <= 0 || remaining > wait) {
            if (timeout) {
            clearTimeout(timeout);
            timeout = null;
            }
            previous = now;
            func.apply(context, args);
        } else if (!timeout) {
            timeout = setTimeout(function() {
            previous = Date.now();
            timeout = null;
            func.apply(context, args);
            }, remaining);
        }
        };
    }
    
    // 更新导航栏状态
    function updateNavbar() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const isAtTop = scrollTop <= TOP_THRESHOLD;
        
        // 判断滚动方向
        isScrollingDown = scrollTop > lastScrollTop;
        lastScrollTop = scrollTop;
        
        // 清除之前的定时器
        clearTimeout(scrollTimeout);
        
        // 如果在页面顶部
        if (isAtTop) {
        nav.classList.add('nav-transparent');
        nav.classList.remove('nav-solid', 'nav-hidden');
        return;
        }
        
        // 不在页面顶部
        nav.classList.remove('nav-transparent');
        nav.classList.add('nav-solid');
        
        // 向下滚动：隐藏导航栏
        if (isScrollingDown && scrollTop > SCROLL_THRESHOLD) {
        nav.classList.add('nav-hidden');
        nav.classList.remove('nav-visible');
        }
        // 向上滚动：显示导航栏
        else {
        nav.classList.remove('nav-hidden');
        nav.classList.add('nav-visible');
        }
        
        // 设置定时器，当停止滚动一段时间后，确保导航栏保持显示
        scrollTimeout = setTimeout(function() {
        if (!isScrollingDown && !isAtTop) {
            nav.classList.remove('nav-hidden');
            nav.classList.add('nav-visible');
        }
        }, 150);
    }
    
    // 添加滚动监听（使用节流优化）
    window.addEventListener('scroll', throttle(updateNavbar, 100));
    
    // 初始加载时更新一次状态
    updateNavbar();
    
    // 页面加载时添加过渡类（避免初始加载时的动画）
    setTimeout(function() {
        nav.style.transition = 'all 0.3s ease';
    }, 100);
    
    // 窗口大小变化时重新计算
    window.addEventListener('resize', function() {
        lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        updateNavbar();
    });
}

function initUserBar() {
    let hoverTimeout = null;
    let isHoverEnabled = true; // 控制悬停功能是否启用
    let isFixed = false; // 记录菜单是否被点击固定
    let isMouseInDropdown = false; // 记录鼠标是否在下拉菜单内
    
    // 检查下拉菜单是否可见
    function isDropdownVisible() {
        const dropdownContent = document.querySelector('.dropdown-content');
        return dropdownContent && dropdownContent.style.opacity === '1';
    }
    
    // 显示下拉菜单
    function showDropdown() {
        const dropdownContent = document.querySelector('.dropdown-content');
        const userTrigger = document.querySelector('.user-trigger');
        
        if (!dropdownContent || !userTrigger) return;
        
        dropdownContent.style.opacity = '1';
        dropdownContent.style.visibility = 'visible';
        dropdownContent.style.transform = 'translateY(0)';
        userTrigger.setAttribute('aria-expanded', 'true');
        
        // 聚焦到第一个可聚焦元素
        const firstItem = dropdownContent.querySelector('.dropdown-item');
        if (firstItem) {
            setTimeout(() => firstItem.focus(), 100);
        }
    }
    
    // 隐藏下拉菜单
    function hideDropdown() {
        const dropdownContent = document.querySelector('.dropdown-content');
        const userTrigger = document.querySelector('.user-trigger');
        
        if (!dropdownContent || !userTrigger) return;
        
        dropdownContent.style.opacity = '0';
        dropdownContent.style.visibility = 'hidden';
        dropdownContent.style.transform = 'translateY(-10px)';
        userTrigger.setAttribute('aria-expanded', 'false');
        userTrigger.focus();
    }
    
    // 点击按钮：切换固定状态
    document.addEventListener('click', function(e) {
        const userTrigger = e.target.closest('.user-trigger');
        const dropdownContent = document.querySelector('.dropdown-content');
        
        if (userTrigger) {
            e.preventDefault();
            e.stopPropagation();
            
            if (isFixed) {
                // 如果已经固定，取消固定并隐藏
                hideDropdown();
                isFixed = false;
                isHoverEnabled = true; // 立即恢复悬停功能
                clearTimeout(hoverTimeout);
            } else {
                // 如果未固定，固定菜单
                if (!isDropdownVisible()) {
                    showDropdown(); // 如果菜单不可见，先显示
                } else {
                    // 如果菜单已经显示（可能是悬停显示的），确保它完全显示
                    showDropdown();
                }
                
                isFixed = true;
                isHoverEnabled = false; // 点击固定后暂时禁用悬停
                
                // 5秒后恢复悬停功能
                setTimeout(() => {
                    if (isFixed) { // 检查是否仍然固定
                        isHoverEnabled = true;
                    }
                }, 5000);
            }
        }
        // 点击下拉菜单内部：保持显示
        else if (e.target.closest('.dropdown-content')) {
            // 点击菜单内部，保持显示状态
            isMouseInDropdown = true;
            return;
        }
        // 点击其他地方：关闭下拉菜单并取消固定
        else {
            if (isDropdownVisible()) {
                hideDropdown();
                isFixed = false;
                isHoverEnabled = true; // 恢复悬停功能
                clearTimeout(hoverTimeout);
            }
            isMouseInDropdown = false;
        }
    });
    
    // 鼠标悬停事件
    document.addEventListener('mouseover', function(e) {
        if (!isHoverEnabled || isFixed) return;
        
        const userTrigger = e.target.closest('.user-trigger');
        const dropdownContent = document.querySelector('.dropdown-content');
        
        if (userTrigger) {
            // 鼠标进入按钮，显示下拉菜单
            clearTimeout(hoverTimeout);
            hoverTimeout = setTimeout(() => {
                if (!isDropdownVisible() && !isFixed) {
                    showDropdown();
                }
            }, 150);
        }
        // 鼠标进入下拉菜单本身
        else if (e.target.closest('.dropdown-content')) {
            clearTimeout(hoverTimeout);
            isMouseInDropdown = true;
        }
    });
    
    // 鼠标离开事件
    document.addEventListener('mouseout', function(e) {
        if (!isHoverEnabled || isFixed) return;
        
        const userTrigger = e.target.closest('.user-trigger');
        const dropdownContent = document.querySelector('.dropdown-content');
        const relatedTarget = e.relatedTarget;
        
        // 检查鼠标是否真的离开了用户菜单区域
        const leftUserArea = !userTrigger && 
                            (!relatedTarget || 
                             (!relatedTarget.closest('.user-trigger') && 
                              !relatedTarget.closest('.dropdown-content')));
        
        const leftDropdownArea = e.target.closest('.dropdown-content') && 
                                (!relatedTarget || 
                                 (!relatedTarget.closest('.user-trigger') && 
                                  !relatedTarget.closest('.dropdown-content')));
        
        if (leftUserArea || leftDropdownArea) {
            isMouseInDropdown = false;
            clearTimeout(hoverTimeout);
            hoverTimeout = setTimeout(() => {
                if (isDropdownVisible() && !isFixed && !isMouseInDropdown) {
                    hideDropdown();
                }
            }, 150);
        }
    });
    
    // 键盘导航支持
    document.addEventListener('keydown', function(e) {
        const userTrigger = document.querySelector('.user-trigger');
        const dropdownContent = document.querySelector('.dropdown-content');
        
        if (!userTrigger || !dropdownContent) return;
        
        // 只有当用户触发按钮聚焦时才处理键盘事件
        if (document.activeElement === userTrigger || userTrigger.contains(document.activeElement)) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                
                if (isFixed) {
                    hideDropdown();
                    isFixed = false;
                    isHoverEnabled = true;
                } else {
                    if (!isDropdownVisible()) {
                        showDropdown();
                    }
                    isFixed = true;
                    isHoverEnabled = false;
                    
                    setTimeout(() => {
                        if (isFixed) {
                            isHoverEnabled = true;
                        }
                    }, 5000);
                }
            } else if (e.key === 'Escape') {
                hideDropdown();
                isFixed = false;
                isHoverEnabled = true;
            }
        }
        
        // 下拉菜单内的键盘导航
        if (dropdownContent.style.opacity === '1') {
            const items = dropdownContent.querySelectorAll('.dropdown-item');
            const currentIndex = Array.from(items).indexOf(document.activeElement);
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = (currentIndex + 1) % items.length;
                if (items[nextIndex]) {
                    items[nextIndex].focus();
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = (currentIndex - 1 + items.length) % items.length;
                if (items[prevIndex]) {
                    items[prevIndex].focus();
                }
            }
        }
    });
    
    // 无障碍性改进
    function setupAccessibility() {
        const userTrigger = document.querySelector('.user-trigger');
        const dropdownContent = document.querySelector('.dropdown-content');
        
        if (userTrigger) {
            userTrigger.setAttribute('role', 'button');
            userTrigger.setAttribute('aria-haspopup', 'true');
            userTrigger.setAttribute('aria-expanded', 'false');
            userTrigger.setAttribute('tabindex', '0');
        }
        
        if (dropdownContent) {
            dropdownContent.setAttribute('role', 'menu');
            dropdownContent.querySelectorAll('.dropdown-item').forEach(item => {
                item.setAttribute('role', 'menuitem');
                item.setAttribute('tabindex', '-1');
            });
        }
    }
    
    // 初始设置无障碍性
    setupAccessibility();
    
    // 监听AJAX页面更新事件
    window.addEventListener('ajax:page:updated', function() {
        // 重置状态
        isFixed = false;
        isHoverEnabled = true;
        isMouseInDropdown = false;
        clearTimeout(hoverTimeout);
        
        // 重新设置无障碍性
        setTimeout(setupAccessibility, 100);
    });
}