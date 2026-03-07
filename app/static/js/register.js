document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    // 密码强度检测
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
    
    // 表单提交验证
    registerForm.addEventListener('submit', function(event) {
        let isValid = true;
        
        // 用户名验证
        if (!usernameInput.value.trim() || usernameInput.value.length < 3) {
            isValid = false;
            showError(usernameInput, '用户名至少需要3个字符');
        } else {
            removeError(usernameInput);
        }
        
        // 密码验证
        if (!passwordInput.value.trim() || passwordInput.value.length < 6) {
            isValid = false;
            showError(passwordInput, '密码至少需要6个字符');
        } else {
            removeError(passwordInput);
        }
        
        // 确认密码验证
        if (passwordInput.value !== confirmPasswordInput.value) {
            isValid = false;
            showError(confirmPasswordInput, '两次输入的密码不一致');
        } else if (confirmPasswordInput.value.trim()) {
            removeError(confirmPasswordInput);
        }
        
        if (!isValid) {
            event.preventDefault();
        }
    });
    
    function checkPasswordStrength(password) {
        if (password.length < 6) {
            return 'weak';
        }
        
        let strength = 0;
        
        // 包含数字
        if (/\d/.test(password)) strength++;
        // 包含小写字母
        if (/[a-z]/.test(password)) strength++;
        // 包含大写字母
        if (/[A-Z]/.test(password)) strength++;
        // 包含特殊字符
        if (/[^a-zA-Z0-9]/.test(password)) strength++;
        // 长度超过8
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
});

