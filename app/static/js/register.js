(function() {
    console.log('register.js 加载');
    
    let initialized = false;
    let currentButton = null;
    
    function initRegisterForm() {
        if (initialized) {
            console.log('register.js: 已经初始化，跳过');
            return;
        }
        
        const registerForm = document.getElementById('registerForm');
        const registerButton = document.getElementById('registerButton');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        
        if (!registerForm || !registerButton) {
            console.log('register.js: 找不到表单或按钮，稍后重试');
            return;
        }
        
        console.log('register.js: 初始化注册表单');
        
        // 保存当前按钮引用
        currentButton = registerButton;
        
        // 确保按钮类型正确
        if (currentButton.type === 'submit') {
            currentButton.type = 'button';
        }
        
        // 移除旧事件监听器（如果存在）
        const newButton = currentButton.cloneNode(true);
        currentButton.parentNode.replaceChild(newButton, currentButton);
        currentButton = newButton;
        
        // 绑定点击事件
        currentButton.addEventListener('click', handleRegisterSubmit, { once: false });
        
        // 绑定表单提交事件（备用）
        registerForm.addEventListener('submit', function(event) {
            event.preventDefault();
            handleRegisterSubmit(event);
        });
        
        // 密码强度检测
        if (passwordInput) {
            passwordInput.addEventListener('input', function() {
                const password = this.value;
                let strengthIndicator = this.parentElement.querySelector('.password-strength');
                
                if (!strengthIndicator) {
                    strengthIndicator = document.createElement('div');
                    strengthIndicator.className = 'password-strength';
                    this.parentElement.appendChild(strengthIndicator);
                }
                
                const strength = checkPasswordStrength(password);
                
                strengthIndicator.className = 'password-strength';
                if (password.length === 0) {
                    strengthIndicator.style.display = 'none';
                } else {
                    strengthIndicator.style.display = 'block';
                    
                    if (strength === 'weak') {
                        strengthIndicator.classList.add('strength-weak');
                    } else if (strength === 'medium') {
                        strengthIndicator.classList.add('strength-medium');
                    } else {
                        strengthIndicator.classList.add('strength-strong');
                    }
                }
            });
        }
        
        initialized = true;
    }
    
    function handleRegisterSubmit(event) {
        event.preventDefault();
        event.stopPropagation();
        
        console.log('register.js: 处理注册提交');
        
        if (!validateForm()) {
            return;
        }
        
        const form = document.getElementById('registerForm');
        const button = document.getElementById('registerButton');
        
        if (!form || !button) {
            console.error('register.js: 找不到表单或按钮');
            return;
        }
        
        // 显示"处理中"状态
        button.disabled = true;
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 注册中...';
        
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
                    // 注册成功，跳转到登录页
                    setTimeout(() => {
                        if (window.ajaxNavigator && data.redirect_url) {
                            window.ajaxNavigator.navigateTo(data.redirect_url, 'login');
                        } else {
                            window.location.href = data.redirect_url || '/login';
                        }
                    }, 500);
                } else {
                    // 注册失败，恢复按钮
                    button.disabled = false;
                    button.innerHTML = originalHTML;
                }
            }
        })
        .catch(error => {
            console.error('注册请求出错:', error);
            showAjaxMessage(false, '网络错误，请稍后重试');
            button.disabled = false;
            button.innerHTML = originalHTML;
        });
    }
    
    function validateForm() {
        let isValid = true;
        
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        
        if (usernameInput && (!usernameInput.value.trim() || usernameInput.value.length < 3)) {
            isValid = false;
            showError(usernameInput, '用户名至少需要3个字符');
        } else if (usernameInput) {
            removeError(usernameInput);
        }
        
        if (passwordInput && (!passwordInput.value.trim() || passwordInput.value.length < 6)) {
            isValid = false;
            showError(passwordInput, '密码至少需要6个字符');
        } else if (passwordInput) {
            removeError(passwordInput);
        }
        
        if (confirmPasswordInput && passwordInput && 
            passwordInput.value !== confirmPasswordInput.value) {
            isValid = false;
            showError(confirmPasswordInput, '两次输入的密码不一致');
        } else if (confirmPasswordInput && confirmPasswordInput.value.trim()) {
            removeError(confirmPasswordInput);
        }
        
        return isValid;
    }
    
    function checkPasswordStrength(password) {
        if (password.length < 6) {
            return 'weak';
        }
        
        let strength = 0;
        
        if (/\d/.test(password)) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        if (password.length >= 8) strength++;
        
        if (strength <= 2) return 'weak';
        if (strength <= 4) return 'medium';
        return 'strong';
    }
    
    function showError(input, message) {
        const formGroup = input.closest('.form-group');
        const error = formGroup.querySelector('.error-message') || document.createElement('div');
        
        error.className = 'error-message';
        error.textContent = message;
        error.style.color = 'var(--danger-color)';
        error.style.fontSize = '0.875rem';
        error.style.marginTop = '0.25rem';
        
        if (!formGroup.querySelector('.error-message')) {
            formGroup.appendChild(error);
        }
        
        input.style.borderColor = 'var(--danger-color)';
    }
    
    function removeError(input) {
        const formGroup = input.closest('.form-group');
        const error = formGroup.querySelector('.error-message');
        
        if (error) {
            formGroup.removeChild(error);
        }
        
        input.style.borderColor = '';
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
        console.log('register.js: 开始初始化');
        initRegisterForm();
    }
    
    // 立即执行一次初始化
    setTimeout(initialize, 100);
    
    // 监听AJAX页面更新事件
    window.addEventListener('ajax:page:updated', function() {
        console.log('register.js: 收到页面更新事件');
        initialized = false; // 重置初始化状态
        setTimeout(initRegisterForm, 150); // 延迟执行，确保DOM已更新
    });
    
    // 监听DOMContentLoaded（首次加载）
    document.addEventListener('DOMContentLoaded', function() {
        console.log('register.js: DOMContentLoaded');
        setTimeout(initRegisterForm, 50);
    });
})();