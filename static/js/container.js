function confirmDelete(containerId, containerName) {
    showConfirm('确认删除', `确定要删除容器 ${containerName} 吗？此操作不可撤销。`, function (confirmed) {
        if (!confirmed) return;
        showLoader();
        fetch(`/container/${containerId}/manage/remove`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('操作成功', '容器已删除', 'success', function () {
                        window.location.href = '/containers';
                    });
                } else {
                    showToast('出错啦', data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error deleting container:', error);
                showToast('出错啦', '请求失败，请稍后重试', 'error');
            }).finally(() => {
                hideLoader();
            });
    });
}

// 访问容器函数
function visitContainer(port) {
    const url = `http://${host_ip}:${port}`;
    window.open(url, '_blank');
}

function copyAddress(port) {
    const address = `${host_ip}:${port}`;
    navigator.clipboard.writeText(address).then(() => {
        showToast('已复制', `地址 ${address} 已复制到剪贴板`, 'success');
    }).catch(err => {
        console.error('无法复制地址: ', err);
        showToast('出错啦', '无法复制地址，请手动复制', 'error');
    });
}

function extendExpiry(containerId, containerName) {
    showConfirm('确认延期', `确定要将容器 ${containerName} 的到期时间延长1小时吗？`, function (confirmed) {
        if (!confirmed) return;
        showLoader();
        fetch(`/container/${containerId}/manage/extend`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('操作成功', '容器已延期1小时', 'success');
                    // 更新剩余时间显示
                    const expiryEl = document.querySelector('.container-expiry');
                    expiryEl.setAttribute('data-expiry', data.new_destroy_time);
                    updateAllExpiry();
                } else {
                    showToast('出错啦', data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error extending container expiry:', error);
                showToast('出错啦', '请求失败，请稍后重试', 'error');
            }).finally(() => {
                hideLoader();
            });
    });
}

function updateAllExpiry() {
    const now = new Date().getTime();
    const totalDuration = 2 * 60 * 60 * 1000; // 2小时的总毫秒数

    document.querySelectorAll('.container-expiry').forEach(el => {
        const expiryTime = new Date(el.getAttribute('data-expiry')).getTime();
        const remaining = expiryTime - now;
        el.textContent = formatTime(remaining);
    });

    document.querySelectorAll('.container-progress').forEach(el => {
        const expiryTime = new Date(el.getAttribute('data-expiry')).getTime();
        const createdAt = new Date(expiryTime - totalDuration).getTime();
        const remaining = expiryTime - now;
        const elapsed = now - createdAt;

        let percentage = (remaining / totalDuration) * 100;
        percentage = Math.max(0, Math.min(100, percentage));

        el.style.width = `${percentage}%`;

        if (percentage < 20) {
            el.style.backgroundColor = '#EF4444';
        } else if (percentage < 50) {
            el.style.backgroundColor = '#F59E0B';
        } else {
            el.style.backgroundColor = '#4B5563';
        }
    });
}

updateAllExpiry();

setInterval(updateAllExpiry, 1000);