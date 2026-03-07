// 简单的表单验证
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.querySelector('.auth-form');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    loginForm.addEventListener('submit', function(event) {
        let isValid = true;
        
        if (!usernameInput.value.trim()) {
            isValid = false;
            showError(usernameInput, '请输入用户名');
        } else {
            removeError(usernameInput);
        }
        
        if (!passwordInput.value.trim()) {
            isValid = false;
            showError(passwordInput, '请输入密码');
        } else {
            removeError(passwordInput);
        }
        
        if (!isValid) {
            event.preventDefault();
        }
    });
    
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

