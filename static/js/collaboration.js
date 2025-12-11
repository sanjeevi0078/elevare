/**
 * Real-time Collaboration Client
 * Handles WebSocket connections for team chat and live updates.
 */

class CollaborationClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.teamId = localStorage.getItem('elevare_team_id') || 'default-team';
        this.listeners = new Set();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const token = localStorage.getItem('access_token');
        
        // If no token, we can't connect securely
        if (!token) {
            console.warn('⚠️ No access token found. WebSocket connection skipped.');
            return;
        }

        const wsUrl = `${protocol}//${window.location.host}/api/v1/collaboration/ws/team/${this.teamId}?token=${token}`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('✅ Connected to Real-time Collaboration Server');
            this.reconnectAttempts = 0;
            this.notifyListeners({ type: 'system', message: 'Connected to live updates' });
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        this.socket.onclose = (event) => {
            console.log('🔌 Disconnected from Real-time Server', event.code);
            if (event.code !== 1000 && event.code !== 1008) {
                this.attemptReconnect();
            }
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
            console.log(`Reconnecting in ${delay}ms... (Attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('Max reconnect attempts reached.');
        }
    }

    handleMessage(data) {
        // Dispatch to all registered listeners
        this.listeners.forEach(listener => listener(data));

        // Handle specific system events
        if (data.type === 'agent_notification') {
            this.showNotification(data.message);
        }
    }

    sendMessage(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'chat',
                message: message
            }));
        } else {
            console.warn('WebSocket is not connected.');
        }
    }

    subscribe(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    showNotification(message) {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-indigo-600 text-white px-6 py-3 rounded-lg shadow-lg transform transition-all duration-500 translate-y-full z-50';
        toast.innerHTML = `<i class="fas fa-robot mr-2"></i> ${message}`;
        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-full');
        });

        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.add('translate-y-full');
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }
}

// Export singleton instance
const collaborationClient = new CollaborationClient();
window.collaborationClient = collaborationClient;
