// Toast Notification System
class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', duration = 4000) {
        const toastId = 'toast-' + Date.now() + Math.random().toString(36).substr(2, 9);
        
        // Create toast element
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast toast-${type}`;
        
        // Get title based on type
        const titles = {
            success: 'Succès',
            error: 'Erreur',
            info: 'Information',
            warning: 'Attention',
            debug: 'Debug'
        };
        
        const title = titles[type] || 'Notification';
        
        toast.innerHTML = `
            <div class="toast-header">
                <div class="toast-icon"></div>
                <h4 class="toast-title">${title}</h4>
                <button class="toast-close" onclick="toastManager.hide('${toastId}')">&times;</button>
            </div>
            <p class="toast-message">${message}</p>
            <div class="toast-progress" style="width: 100%;"></div>
        `;
        
        // Add to container
        this.container.appendChild(toast);
        
        // Trigger show animation
        setTimeout(() => toast.classList.add('show'), 10);
        
        // Start progress bar animation
        const progressBar = toast.querySelector('.toast-progress');
        setTimeout(() => {
            progressBar.style.transitionDuration = duration + 'ms';
            progressBar.style.width = '0%';
        }, 100);
        
        // Store toast reference
        this.toasts.set(toastId, {
            element: toast,
            timer: setTimeout(() => this.hide(toastId), duration)
        });
        
        // Auto-hide after duration
        return toastId;
    }

    hide(toastId) {
        const toastData = this.toasts.get(toastId);
        if (!toastData) return;
        
        const { element, timer } = toastData;
        
        // Clear timer
        clearTimeout(timer);
        
        // Hide animation
        element.classList.remove('show');
        element.classList.add('hide');
        
        // Remove from DOM after animation
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.toasts.delete(toastId);
        }, 300);
    }

    clear() {
        this.toasts.forEach((_, toastId) => this.hide(toastId));
    }

    // Convenience methods
    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    debug(message, duration) {
        return this.show(message, 'debug', duration);
    }
}

// Initialize global toast manager
const toastManager = new ToastManager();

// Function to show Django messages as toasts
function showDjangoMessages() {
    const messages = window.djangoMessages || [];
    messages.forEach(message => {
        const type = message.tags.includes('error') ? 'error' :
                    message.tags.includes('warning') ? 'warning' :
                    message.tags.includes('success') ? 'success' :
                    message.tags.includes('info') ? 'info' :
                    message.tags.includes('debug') ? 'debug' : 'info';
        
        toastManager.show(message.message, type);
    });
}

// Auto-show messages when page loads
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(showDjangoMessages, 100);
});

// Export for global use
window.toastManager = toastManager;
window.showDjangoMessages = showDjangoMessages;