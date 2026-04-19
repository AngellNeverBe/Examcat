(function() {
    console.log('login.js 加载');
    
    let initialized = false;
    let currentButton = null;
    
    function initLoginForm() {
        if (initialized) {
            console.log('login.js: 已经初始化，跳过');
            return;
        }
        
        const loginForm = document.getElementById('loginForm');
        const loginButton = document.getElementById('loginButton');
        
        if (!loginForm || !loginButton) {
            console.log('login.js: 找不到表单或按钮，稍后重试');
            return;
        }
        
        console.log('login.js: 初始化登录表单');
        
        // 保存当前按钮引用
        currentButton = loginButton;
        
        // 确保按钮类型正确
        if (currentButton.type === 'submit') {
            currentButton.type = 'button';
        }
        
        // 移除旧事件监听器（如果存在）
        const newButton = currentButton.cloneNode(true);
        currentButton.parentNode.replaceChild(newButton, currentButton);
        currentButton = newButton;
        
        // 绑定点击事件
        currentButton.addEventListener('click', handleLoginSubmit, { once: false });
        
        // 绑定表单提交事件（备用）
        loginForm.addEventListener('submit', function(event) {
            event.preventDefault();
            handleLoginSubmit(event);
        });
        
        initialized = true;
    }
    
    function handleLoginSubmit(event) {
        event.preventDefault();
        event.stopPropagation();
        
        console.log('login.js: 处理登录提交');
        
        const form = document.getElementById('loginForm');
        const button = document.getElementById('loginButton');
        
        if (!form || !button) {
            console.error('login.js: 找不到表单或按钮');
            return;
        }
        
        const username = document.getElementById('username')?.value;
        const password = document.getElementById('password')?.value;
        
        // 简单验证
        if (!username || !password) {
            showAjaxMessage(false, '请输入用户名和密码');
            return;
        }
        
        // 显示加载状态
        button.disabled = true;
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';
        
        // 发送AJAX请求
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(handleFetchResponse)
        .then(data => {
            if (data) {
                showAjaxMessage(data.success, data.message);
                
                if (data.success) {
                    // 登录成功，跳转
                    setTimeout(() => {
                        window.location.href = data.redirect_url || '/';
                    }, 500);
                } else {
                    // 登录失败，恢复按钮
                    button.disabled = false;
                    button.innerHTML = originalHTML;
                }
            }
        })
        .catch(error => {
            console.error('登录请求出错:', error);
            showAjaxMessage(false, '网络错误，请稍后重试');
            button.disabled = false;
            button.innerHTML = originalHTML;
        });
    }
    
    function showAjaxMessage(success, message) {
        const ajaxMessages = document.getElementById('ajaxMessages');
        if (!ajaxMessages) return;
        
        ajaxMessages.innerHTML = '';
        
        const alertDiv = document.createElement('div');
        alertDiv.className = success ? 'alert alert-success' : 'alert alert-danger';
        alertDiv.style.cssText = 'animation: fadeIn 0.5s;';
        
        const icon = document.createElement('i');
        icon.className = success ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
        alertDiv.appendChild(icon);
        
        alertDiv.appendChild(document.createTextNode(' ' + message));
        
        ajaxMessages.appendChild(alertDiv);
        ajaxMessages.style.display = 'block';
        
        setTimeout(() => {
            ajaxMessages.style.display = 'none';
        }, 5000);
    }
    
    // 初始化函数
    function initialize() {
        console.log('login.js: 开始初始化');
        initLoginForm();
    }
    
    // 立即执行一次初始化
    setTimeout(initialize, 100);
    
    // 监听AJAX页面更新事件
    window.addEventListener('ajax:page:updated', function() {
        console.log('login.js: 收到页面更新事件');
        initialized = false; // 重置初始化状态
        setTimeout(initLoginForm, 150); // 延迟执行，确保DOM已更新
    });
    
    // 监听DOMContentLoaded（首次加载）
    document.addEventListener('DOMContentLoaded', function() {
        console.log('login.js: DOMContentLoaded');
        setTimeout(initLoginForm, 50);
    });
})();

