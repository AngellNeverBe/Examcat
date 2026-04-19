/* 
 * 更新导航高亮状态
*/
function setActiveNavByPage(pageName) {
    const navLinks = document.querySelectorAll('.nav-link');
    let found = false;
    
    // 先清除所有高亮
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // 如果没有pageName或者pageName是"question"或"exam"，直接返回（不设置任何高亮）
    if (!pageName || pageName === 'question' || pageName === 'exam') {
        return;
    }
    
    // 正常查找对应的导航项
    navLinks.forEach(link => {
        const dataPage = link.getAttribute('data-page');
        if (dataPage === pageName) {
            link.classList.add('active');
            found = true;
        }
    });
    
    if (!found) {
        console.warn('未找到对应页面标识的导航链接:', pageName);
    }
}

// 页面首次加载时，从某个地方获取当前页面标识
document.addEventListener('DOMContentLoaded', function() {
    if (window.currentPage) {
        setActiveNavByPage(window.currentPage);
    }
});

// 监听 AJAX 页面切换完成事件
window.addEventListener('ajax:page:updated', function(event) {
    const page = event.detail?.page;
    // 即使page是undefined也调用，这样会清除所有高亮
    setActiveNavByPage(page);
});