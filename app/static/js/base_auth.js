// base_auth.js

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有基础功能
    initFlashMessages();
});

/**
 * 初始化Flash消息功能
 */
function initFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
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
