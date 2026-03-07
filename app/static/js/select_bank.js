// File input display
document.getElementById('bank_file').addEventListener('change', function(e) {
    const fileName = e.target.files[0] ? e.target.files[0].name : '未选择文件';
    this.nextElementSibling.textContent = `已选择: ${fileName}`;
});

// Confirm delete
document.querySelectorAll('.btn-danger').forEach(btn => {
    btn.addEventListener('click', function(e) {
        if (!confirm('确定要删除这个题库吗？此操作不可撤销。')) {
            e.preventDefault();
        }
    });
});