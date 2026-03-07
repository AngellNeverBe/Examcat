document.addEventListener('DOMContentLoaded', function() {
    const examForm = document.getElementById('examForm');
    examForm.addEventListener('submit', function(e) {
        e.preventDefault(); // 阻止表单默认提交行为

        // 使用FormData获取用户选择的答案
        const formData = new FormData(examForm);

        // 使用fetch以POST方式提交到后端submit_exam路由
        fetch(examForm.getAttribute('action'), {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 显示考试结果在当前页面
                const resultDiv = document.getElementById('examResult');
                const correctCount = data.correct_count;
                const total = data.total;
                const score = data.score.toFixed(2);
                
                // 使用标准样式显示结果
                resultDiv.innerHTML = `
                <div class="alert ${score >= 60 ? 'alert-success' : 'alert-danger'}">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <h3 class="mb-0">考试结束</h3>
                        <span class="badge ${score >= 60 ? 'badge-success' : 'badge-danger'}">${score}%</span>
                    </div>
                    <div class="progress-container mb-2">
                        <div class="progress-header">
                            <span class="progress-title">得分情况</span>
                            <span class="progress-value">${correctCount}/${total}</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${score}%"></div>
                        </div>
                    </div>
                    <p class="mb-0">你已完成本次模拟考试，可以查看<a href="${data.result_url || '#'}">详细结果</a>。</p>
                </div>`;
            } else {
                // 显示标准错误消息
                const resultDiv = document.getElementById('examResult');
                resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> 提交失败，请重试。
                </div>`;
            }
        })
        .catch(err => {
            console.error("提交考试请求失败:", err);
            // 显示标准错误消息
            const resultDiv = document.getElementById('examResult');
            resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i> 提交考试请求失败，请稍后再试。
            </div>`;
        });
    });
});