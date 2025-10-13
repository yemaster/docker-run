function formatTime(ms) {
    if (ms <= 0) return "已过期";

    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((ms % (1000 * 60)) / 1000);

    return `${hours}h ${minutes}m ${seconds}s`;
}

function formatSize(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}

function showToast(title, message, type = 'info', callback = null) {
    const toast = document.createElement('div');
    toast.className = `w-100 px-6 py-4 rounded-md shadow-lg transform transition-all duration-300 ease-in-out translate-x-full opacity-0 mb-3`;

    switch (type) {
        case 'success':
            toast.classList.add('bg-green-50', 'border-l-4', 'border-green-500');
            toast.innerHTML = `
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fa fa-check-circle text-green-500 text-lg"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">${title}</h3>
                        <div class="mt-1 text-sm text-green-700">${message}</div>
                    </div>
                </div>
            `;
            break;
        case 'error':
            toast.classList.add('bg-red-50', 'border-l-4', 'border-red-500');
            toast.innerHTML = `
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fa fa-exclamation-circle text-red-500 text-lg"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">${title}</h3>
                        <div class="mt-1 text-sm text-red-700">${message}</div>
                    </div>
                </div>
            `;
            break;
        case 'warning':
            toast.classList.add('bg-yellow-50', 'border-l-4', 'border-yellow-500');
            toast.innerHTML = `
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fa fa-exclamation-triangle text-yellow-500 text-lg"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-yellow-800">${title}</h3>
                        <div class="mt-1 text-sm text-yellow-700">${message}</div>
                    </div>
                </div>
            `;
            break;
        default: // info
            toast.classList.add('bg-blue-50', 'border-l-4', 'border-blue-500');
            toast.innerHTML = `
                <div class="flex">
                    <div class="flex-shrink-0">
                        <i class="fa fa-info-circle text-blue-500 text-lg"></i>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-blue-800">${title}</h3>
                        <div class="mt-1 text-sm text-blue-700">${message}</div>
                    </div>
                </div>
            `;
    }

    const container = document.getElementById('toastContainer');
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-x-full', 'opacity-0');
        toast.classList.add('translate-x-0', 'opacity-100');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('translate-x-0', 'opacity-100');
        toast.classList.add('translate-x-full', 'opacity-0');

        setTimeout(() => {
            container.removeChild(toast);
            if (typeof callback === 'function') {
                callback();
            }
        }, 300);
    }, 3000);

    return toast;
}

let confirmCallback = null;
let currentModalType = 'confirm';
const confirmModal = document.getElementById('confirmModal');
const confirmModalContent = document.getElementById('confirmModalContent');
const confirmModalTitle = document.getElementById('confirmModalTitle');
const confirmModalContentText = document.getElementById('confirmModalContentText');
const confirmModalConfirm = document.getElementById('confirmModalConfirm');
const confirmModalCancel = document.getElementById('confirmModalCancel');
const confirmMessageEl = document.querySelector('.confirm-message');
const confirmInputEl = document.querySelector('.confirm-input');
const confirmInputField = document.getElementById('confirmInputField');
const confirmInputLabel = document.getElementById('confirmInputLabel');

function showConfirm(title, content, callback) {
    currentModalType = 'confirm';
    confirmCallback = callback;

    confirmModalTitle.textContent = title || '确认操作';
    confirmModalContentText.textContent = content || '确认要执行此操作吗？';

    confirmMessageEl.classList.remove('hidden');
    confirmInputEl.classList.add('hidden');

    confirmModal.classList.remove('hidden');
    setTimeout(() => {
        confirmModalContent.classList.remove('scale-95', 'opacity-0');
        confirmModalContent.classList.add('scale-100', 'opacity-100');
    }, 50);
}

function showInputConfirm(title, label, callback) {
    currentModalType = 'input';
    confirmCallback = callback;

    confirmModalTitle.textContent = title || '输入确认';
    confirmInputLabel.textContent = label || '请输入：';

    confirmInputField.value = '';

    confirmMessageEl.classList.add('hidden');
    confirmInputEl.classList.remove('hidden');

    confirmModal.classList.remove('hidden');
    setTimeout(() => {
        confirmModalContent.classList.remove('scale-95', 'opacity-0');
        confirmModalContent.classList.add('scale-100', 'opacity-100');

        setTimeout(() => {
            confirmInputField.focus();
        }, 100);
    }, 50);
}

function hideConfirmModal() {
    confirmModalContent.classList.remove('scale-100', 'opacity-100');
    confirmModalContent.classList.add('scale-95', 'opacity-0');

    setTimeout(() => {
        confirmModal.classList.add('hidden');
        confirmCallback = null;
    }, 150);
}

confirmModalConfirm.addEventListener('click', function () {
    if (typeof confirmCallback === 'function') {
        if (currentModalType === 'input') {
            confirmCallback(true, confirmInputField.value.trim());
        } else {
            confirmCallback(true);
        }
    }
    hideConfirmModal();
});

confirmModalCancel.addEventListener('click', function () {
    if (typeof confirmCallback === 'function') {
        if (currentModalType === 'input') {
            confirmCallback(false, '');
        } else {
            confirmCallback(false);
        }
    }
    hideConfirmModal();
});

confirmModal.addEventListener('click', function (e) {
    if (e.target === confirmModal) {
        if (typeof confirmCallback === 'function') {
            if (currentModalType === 'input') {
                confirmCallback(false, '');
            } else {
                confirmCallback(false);
            }
        }
        hideConfirmModal();
    }
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !confirmModal.classList.contains('hidden')) {
        if (typeof confirmCallback === 'function') {
            if (currentModalType === 'input') {
                confirmCallback(false, '');
            } else {
                confirmCallback(false);
            }
        }
        hideConfirmModal();
    }
});

confirmInputField.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !confirmModal.classList.contains('hidden')) {
        e.preventDefault();
        if (typeof confirmCallback === 'function') {
            confirmCallback(true, confirmInputField.value.trim());
        }
        hideConfirmModal();
    }
});

const loaderOverlay = document.getElementById('loaderOverlay');
const loaderTitle = document.getElementById('loaderTitle');
const loaderContent = document.getElementById('loaderContent');

function showLoader(title = '正在处理', content = '请稍候...') {
    loaderTitle.textContent = title;
    loaderContent.textContent = content;
    loaderOverlay.classList.remove('hidden');

    setTimeout(() => {
        loaderOverlay.classList.remove('scale-95', 'opacity-0');
        loaderOverlay.classList.add('scale-100', 'opacity-100');
    }, 50);
}

function hideLoader() {
    loaderOverlay.classList.remove('scale-100', 'opacity-100');
    loaderOverlay.classList.add('scale-95', 'opacity-0');

    setTimeout(() => {
        loaderOverlay.classList.add('hidden');
    }, 150);
}