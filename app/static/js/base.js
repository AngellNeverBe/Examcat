// base.js - Base template 功能

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有基础功能
    initMobileMenu();
    initFlashMessages();
    initTableFeatures();
    initDeviceDetection();
});

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