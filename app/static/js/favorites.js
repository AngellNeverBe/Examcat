document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.update-tag-form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // 阻止表单默认提交

            const qid = form.getAttribute('data-qid');
            const formData = new FormData(form);

            fetch(form.getAttribute('action'), {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 使用alert-success显示成功消息
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success';
                    alertDiv.innerHTML = '<i class="fas fa-check-circle"></i> ' + data.msg;
                    
                    // 将消息插入表格上方
                    const cardTitle = document.querySelector('.card-title');
                    cardTitle.parentNode.insertBefore(alertDiv, cardTitle.nextSibling);
                    
                    // 5秒后消失
                    setTimeout(() => {
                        alertDiv.style.opacity = '0';
                        setTimeout(() => {
                            alertDiv.remove();
                        }, 500);
                    }, 5000);
                    
                    // 更新显示的标签
                    const tagCell = document.querySelector('#tag_display_' + qid);
                    if (tagCell) {
                        const newTag = formData.get('tag');
                        tagCell.textContent = newTag;
                    }
                } else {
                    // 使用alert-danger显示错误消息
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger';
                    alertDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> 标记更新失败：' + data.msg;
                    
                    // 将消息插入表格上方
                    const cardTitle = document.querySelector('.card-title');
                    cardTitle.parentNode.insertBefore(alertDiv, cardTitle.nextSibling);
                    
                    // 5秒后消失
                    setTimeout(() => {
                        alertDiv.style.opacity = '0';
                        setTimeout(() => {
                            alertDiv.remove();
                        }, 500);
                    }, 5000);
                }
            })
            .catch(err => {
                console.error("更新标记请求失败：", err);
                
                // 使用alert-danger显示错误消息
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger';
                alertDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> 更新标记请求失败，请稍后重试';
                
                // 将消息插入表格上方
                const cardTitle = document.querySelector('.card-title');
                cardTitle.parentNode.insertBefore(alertDiv, cardTitle.nextSibling);
                
                // 5秒后消失
                setTimeout(() => {
                    alertDiv.style.opacity = '0';
                    setTimeout(() => {
                        alertDiv.remove();
                    }, 500);
                }, 5000);
            });
        });
    });
});