// JARVIS Premium UI - Core Logic
class JarvisApp {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isProcessing = false;

        // DOM Elements cache
        this.els = {
            chatMessages: document.getElementById('chatMessages'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            telemetryStream: document.getElementById('telemetryStream'),
            connectionDot: document.querySelector('.connection-state .dot'),
            connectionText: document.querySelector('.connection-state .text'),
            cpuBar: document.querySelector('.cpu-bar'),
            memBar: document.querySelector('.mem-bar'),
            taskStatus: document.getElementById('taskStatus'),
            taskName: document.getElementById('currentTaskName')
        };

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.setupMobileOptimization(); // New mobile handlers
        this.logSystem('SYSTEM', 'Neural Interface Initialized.', 'info');
        this.addSystemMessage("Systems Online. Waiting for operator input.");
    }

    /* --- Mobile & Network Opt --- */
    setupMobileOptimization() {
        // Force reconnect when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
                    this.logSystem('NET', 'Resuming session...', 'info');
                    this.connectWebSocket();
                }
            }
        });

        // Handle network status changes
        window.addEventListener('online', () => {
            this.logSystem('NET', 'Network detected. Reconnecting...', 'success');
            this.connectWebSocket();
        });

        window.addEventListener('offline', () => {
            this.logSystem('NET', 'Network lost.', 'error');
            this.updateConnectionstate(false);
        });
    }

    /* --- WebSocket & Connection --- */
    connectWebSocket() {
        if (this.ws) {
            this.ws.close(); // Ensure clean slate
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.logSystem('NET', 'Uplink Established.', 'success');
            this.reconnectAttempts = 0;
            this.updateConnectionstate(true);
            this.startHeartbeat();
            this.requestSystemStatus();
        };

        this.ws.onmessage = (event) => {
            try {
                this.handleMessage(JSON.parse(event.data));
            } catch (e) {
                console.error("Invalid JSON:", event.data);
            }
        };

        this.ws.onerror = (error) => {
            // Error will trigger onclose usually
            console.error("WS Error:", error);
            this.updateConnectionstate(false);
        };

        this.ws.onclose = () => {
            this.logSystem('NET', 'Uplink Lost. Retrying...', 'warn');
            this.updateConnectionstate(false);
            this.stopHeartbeat();
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        // Infinite reconnect with backoff
        // Cap backoff at 10 seconds
        const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);

        this.reconnectAttempts++;
        this.logSystem('NET', `Reconnecting in ${delay / 1000}s... (Attempt ${this.reconnectAttempts})`, 'warn');

        setTimeout(() => this.connectWebSocket(), delay);
    }

    /* --- Heartbeat System --- */
    startHeartbeat() {
        this.stopHeartbeat(); // Clear existing

        // Send ping every 30s to keep connection alive at network layer
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, 30000);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
    }

    // resetWatchdog removed as per user request (no auto-disconnect/reconnect on timeout)

    updateConnectionstate(online) {
        if (this.els.connectionDot && this.els.connectionText) {
            this.els.connectionDot.style.background = online ? 'var(--neon-green)' : 'var(--neon-red)';
            this.els.connectionDot.style.boxShadow = online ? '0 0 5px var(--neon-green)' : 'none';
            this.els.connectionText.textContent = online ? 'ONLINE' : 'OFFLINE';
            this.els.connectionText.style.color = online ? 'var(--neon-green)' : 'var(--neon-red)';
        }
    }

    /* --- Message Handling --- */
    handleMessage(data) {

        switch (data.type) {
            case 'heartbeat':
                // Just for keep-alive, no action needed
                break;
            case 'system':
                this.addSystemMessage(data.message);
                this.logSystem('SYS', data.message, 'info');
                break;
            case 'chat':
                this.isProcessing = false;
                this.removeLoadingIndicator();
                this.addJarvisMessage(data.response);
                break;
            case 'status':
                this.updateSystemStatus(data.status);
                break;
            case 'error':
                this.isProcessing = false;
                this.removeLoadingIndicator();
                this.addSystemMessage(`ERROR: ${data.message}`, 'error');
                this.logSystem('ERR', data.message, 'error');
                break;
            case 'thinking': // Optional: Log thought process
                this.logSystem('THOUGHT', data.message, 'info');
                break;
        }
    }

    sendMessage() {
        const message = this.els.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        this.isProcessing = true;
        this.addUserMessage(message);
        this.els.messageInput.value = '';
        this.showLoadingIndicator();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'chat', message: message }));
            this.logSystem('USER', `Sent: ${message.substring(0, 20)}...`, 'info');
        } else {
            this.isProcessing = false;
            this.removeLoadingIndicator();
            this.addSystemMessage('Uplink Offline. Message queued.', 'error');
        }
    }

    /* --- UI Updates --- */
    updateSystemStatus(status) {
        // CPU/Mem Bars
        if (status.resources) {
            const cpu = status.resources.cpu_percent || 0;
            const mem = status.resources.memory_percent || 0;

            if (this.els.cpuBar) this.els.cpuBar.style.width = `${cpu}%`;
            if (this.els.memBar) this.els.memBar.style.width = `${mem}%`;
        }

        // Task Status logic (if any)
        if (status.session && status.session.pending_tasks > 0) {
            this.els.taskStatus.style.display = 'flex';
            this.els.taskName.textContent = `${status.session.pending_tasks} Pending Tasks`;
        } else {
            this.els.taskStatus.style.display = 'none';
        }
    }

    /* --- Renderers --- */
    addUserMessage(content) {
        const div = document.createElement('div');
        div.className = 'message user-message';
        div.textContent = content; // Text only for user to prevent XSS
        this.els.chatMessages.appendChild(div);
        this.scrollToBottom();
    }

    addJarvisMessage(response) {
        const content = (typeof response === 'object' && response !== null) ? (response.content || JSON.stringify(response)) : response;

        const div = document.createElement('div');
        div.className = 'message system-message';

        // Use marked.js with improved options (CDN version)
        if (typeof marked !== 'undefined') {
            try {
                // Configure marked options
                marked.setOptions({
                    breaks: true,
                    gfm: true
                });

                // Custom Renderer for Links
                const renderer = new marked.Renderer();
                renderer.link = function (href, title, text) {
                    const cleanHref = href || '#';
                    const cleanTitle = title || '';
                    const cleanText = text || cleanHref;
                    return `<a href="${cleanHref}" title="${cleanTitle}" target="_blank" rel="noopener noreferrer">${cleanText}</a>`;
                };

                // Parse
                div.innerHTML = marked.parse(content, { renderer: renderer });

                // Fallback: If renderer fails, do post-processing for safety
                div.querySelectorAll('a').forEach(a => {
                    if (!a.getAttribute('target')) {
                        a.setAttribute('target', '_blank');
                        a.setAttribute('rel', 'noopener noreferrer');
                    }
                });

            } catch (e) {
                div.textContent = content;
                console.error("Markdown parse error:", e);
            }
        } else {
            console.error("marked.js library not loaded from CDN!");
            div.textContent = content;
        }

        // Add markdown styling class
        div.classList.add('markdown-content');

        this.els.chatMessages.appendChild(div);

        // Highlight code blocks (placeholder for future syntax highlighter)
        div.querySelectorAll('pre code').forEach(block => {
            block.style.background = 'rgba(0,0,0,0.3)';
            block.style.display = 'block';
            block.style.padding = '10px';
            block.style.borderRadius = '4px';
        });

        // Process visualizations if any
        if (response.visualizations) {
            response.visualizations.forEach(viz => this.renderViz(div, viz));
        }

        this.scrollToBottom();
    }

    addSystemMessage(msg, type = 'info') {
        const div = document.createElement('div');
        div.className = `message system-message`;
        div.style.fontStyle = 'italic';
        div.style.opacity = '0.7';
        div.innerHTML = `<span style="color:var(--neon-cyan)">[SYSTEM]</span> ${msg}`;
        this.els.chatMessages.appendChild(div);
        this.scrollToBottom();
    }

    logSystem(source, msg, level = 'info') {
        if (!this.els.telemetryStream) return;

        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        entry.textContent = `[${time}] [${source}] ${msg}`;

        this.els.telemetryStream.appendChild(entry);
        this.els.telemetryStream.scrollTop = this.els.telemetryStream.scrollHeight;
    }

    showLoadingIndicator() {
        const div = document.createElement('div');
        div.id = 'loadingIndicator';
        div.className = 'message system-message';
        div.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
        this.els.chatMessages.appendChild(div);
        this.scrollToBottom();
    }

    removeLoadingIndicator() {
        const el = document.getElementById('loadingIndicator');
        if (el) el.remove();
    }

    scrollToBottom() {
        this.els.chatMessages.scrollTop = this.els.chatMessages.scrollHeight;
    }

    requestSystemStatus() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'status' }));
        }
    }

    setupEventListeners() {
        // Send
        this.els.sendBtn?.addEventListener('click', () => this.sendMessage());
        this.els.messageInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Active state toggle
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const target = btn.dataset.target;
                if (target === 'settings-section') {
                    document.getElementById('settingsModal').style.display = 'flex';
                }
                // Handle others if implemented
            });
        });

        // Modal Close
        document.getElementById('closeSettingsBtn')?.addEventListener('click', () => {
            document.getElementById('settingsModal').style.display = 'none';
        });

        // Clear Chat
        document.getElementById('clearChatBtn')?.addEventListener('click', () => {
            this.els.chatMessages.innerHTML = '';
            this.addSystemMessage("Buffer Purged.");
        });

        // Polling
        setInterval(() => this.requestSystemStatus(), 5000);
    }

    renderViz(container, viz) {
        if (viz.type === 'echarts' && typeof echarts !== 'undefined') {
            const chartDiv = document.createElement('div');
            chartDiv.style.width = '100%';
            chartDiv.style.height = '300px';
            chartDiv.style.marginTop = '10px';
            container.appendChild(chartDiv);

            const chart = echarts.init(chartDiv, null, { renderer: 'svg' });
            // Force dark theme overrides
            const option = viz.option;
            if (option) {
                option.backgroundColor = 'transparent';
                option.textStyle = { color: '#abcdef' };
            }
            chart.setOption(option);
            window.addEventListener('resize', () => chart.resize());
        }
    }
}

// Initialize
const jarvisApp = new JarvisApp();
