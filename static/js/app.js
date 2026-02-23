// JARVIS Premium UI - Core Logic
class JarvisApp {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isProcessing = false;
        this.pendingImages = [];  // [{path, url, name}]

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
            taskName: document.getElementById('currentTaskName'),
            uploadBtn: document.getElementById('uploadBtn'),
            imageFileInput: document.getElementById('imageFileInput'),
            imagePreviewStrip: document.getElementById('imagePreviewStrip'),
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
                // Remove stream bubble if exists
                const streamBubble = document.getElementById('streamBubble');
                if (streamBubble) streamBubble.remove();
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
            case 'thinking':
                this.updateOrCreateStreamBubble('thinking', data.content || data.message || '');
                this.logSystem('THINK', (data.content || '').substring(0, 60), 'info');
                break;
            case 'tool_start':
                this.addSystemMessage(`🔧 Executing: <b>${data.name}</b>`, 'info');
                this.logSystem('TOOL', `Start: ${data.name}`, 'info');
                break;
            case 'tool_result':
                const icon = data.success ? '✅' : '❌';
                this.logSystem('TOOL', `${icon} ${data.name}: ${data.output_preview || (data.success ? 'OK' : 'Failed')}`, data.success ? 'success' : 'error');
                break;
            case 'planning':
                this.logSystem('PLAN', `Complexity: ${data.complexity}`, 'info');
                break;
            case 'step_start':
                this.logSystem('STEP', `▶ ${data.desc || data.id}`, 'info');
                break;
            case 'step_complete':
                this.logSystem('STEP', `✓ ${data.id} (${data.duration || 0}s)`, 'success');
                break;
            case 'log':
                this.logSystem(data.level || 'SYS', data.message, data.level?.toLowerCase() || 'info');
                break;
        }
    }

    sendMessage() {
        const message = this.els.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        this.isProcessing = true;
        this.addUserMessage(message, this.pendingImages);
        this.els.messageInput.value = '';
        this.showLoadingIndicator();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const payload = { type: 'chat', message: message };
            // Attach image paths if any
            if (this.pendingImages.length > 0) {
                payload.images = this.pendingImages.map(img => img.path);
            }
            this.ws.send(JSON.stringify(payload));
            this.logSystem('USER', `Sent: ${message.substring(0, 20)}...${this.pendingImages.length ? ` +${this.pendingImages.length} img` : ''}`, 'info');
            // Clear pending images
            this.pendingImages = [];
            this.updateImagePreview();
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
    addUserMessage(content, images = []) {
        const div = document.createElement('div');
        div.className = 'message user-message';
        div.textContent = content;
        // Show uploaded image thumbnails in user message
        if (images && images.length > 0) {
            const strip = document.createElement('div');
            strip.className = 'user-images-strip';
            images.forEach(img => {
                const thumb = document.createElement('img');
                thumb.src = img.url;
                thumb.alt = img.name || 'Image';
                thumb.className = 'user-msg-thumb';
                strip.appendChild(thumb);
            });
            div.appendChild(strip);
        }
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

                // Wrapper for styles
                const contentDiv = document.createElement('div');
                contentDiv.className = 'markdown-content';
                contentDiv.innerHTML = marked.parse(content, { renderer: renderer });
                div.appendChild(contentDiv);

                // Fallback: If renderer fails, do post-processing for safety
                contentDiv.querySelectorAll('a').forEach(a => {
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

        // Process attachments if any
        if (response.attachments) {
            const attachmentContainer = document.createElement('div');
            attachmentContainer.className = 'attachment-container';
            attachmentContainer.style.marginTop = '10px';
            attachmentContainer.style.display = 'flex';
            attachmentContainer.style.flexWrap = 'wrap';
            attachmentContainer.style.gap = '10px';

            response.attachments.forEach(att => {
                if (att.type === 'image') {
                    // Extract filename from path (handle both Windows and Unix separators)
                    const filename = att.path.split(/[/\\]/).pop();
                    const imageUrl = `/images/${filename}`;

                    const imgContainer = document.createElement('div');
                    imgContainer.className = 'image-attachment';

                    const img = document.createElement('img');
                    img.src = imageUrl;
                    img.alt = att.title || 'Screenshot';
                    img.style.maxWidth = '100%';
                    img.style.maxHeight = '300px';
                    img.style.borderRadius = '8px';
                    img.style.border = '1px solid #333';
                    img.style.cursor = 'pointer';
                    img.onclick = () => window.open(imageUrl, '_blank');

                    imgContainer.appendChild(img);
                    attachmentContainer.appendChild(imgContainer);
                }
            });

            if (attachmentContainer.children.length > 0) {
                div.appendChild(attachmentContainer);
            }
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

        // [NEW] Image Upload
        this.els.uploadBtn?.addEventListener('click', () => {
            this.els.imageFileInput?.click();
        });
        this.els.imageFileInput?.addEventListener('change', (e) => {
            this.handleImageUpload(e.target.files);
            e.target.value = ''; // Reset so same file can be re-selected
        });

        // [NEW] Drag & Drop on chat area
        this.els.chatMessages?.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.add('drag-over');
        });
        this.els.chatMessages?.addEventListener('dragleave', (e) => {
            e.currentTarget.classList.remove('drag-over');
        });
        this.els.chatMessages?.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
            if (files.length > 0) this.handleImageUpload(files);
        });

        // [NEW] Paste image from clipboard
        document.addEventListener('paste', (e) => {
            const items = Array.from(e.clipboardData?.items || []);
            const imageItems = items.filter(item => item.type.startsWith('image/'));
            if (imageItems.length > 0) {
                const files = imageItems.map(item => item.getAsFile()).filter(Boolean);
                this.handleImageUpload(files);
            }
        });

        // Polling
        setInterval(() => this.requestSystemStatus(), 5000);
    }

    /* --- [NEW] Image Upload (Mobile-compatible) --- */
    async handleImageUpload(files) {
        const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB limit
        const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif'];

        for (const file of files) {
            // iOS Safari may report empty type for HEIC — check extension as fallback
            const ext = (file.name || '').toLowerCase().split('.').pop();
            const isImage = file.type.startsWith('image/') || IMAGE_EXTENSIONS.includes('.' + ext);
            if (!isImage) continue;

            // File size check
            if (file.size > MAX_FILE_SIZE) {
                this.logSystem('UPLOAD', `File too large: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB, max 10MB)`, 'error');
                continue;
            }

            try {
                const formData = new FormData();
                formData.append('file', file);

                const resp = await fetch('/api/upload', { method: 'POST', body: formData });
                if (!resp.ok) {
                    this.logSystem('UPLOAD', `Server error: ${resp.status}`, 'error');
                    continue;
                }
                const data = await resp.json();

                if (data.success) {
                    this.pendingImages.push({
                        path: data.path,
                        url: data.url,
                        name: data.original_name || file.name,
                    });
                    this.updateImagePreview();
                    this.logSystem('UPLOAD', `Image uploaded: ${file.name}`, 'success');
                } else {
                    this.logSystem('UPLOAD', `Failed: ${data.error || 'Unknown'}`, 'error');
                }
            } catch (err) {
                this.logSystem('UPLOAD', `Error: ${err.message}`, 'error');
            }
        }
    }

    updateImagePreview() {
        const strip = this.els.imagePreviewStrip;
        if (!strip) return;

        strip.innerHTML = '';
        if (this.pendingImages.length === 0) {
            strip.style.display = 'none';
            return;
        }

        strip.style.display = 'flex';
        this.pendingImages.forEach((img, idx) => {
            const item = document.createElement('div');
            item.className = 'preview-item';

            const thumb = document.createElement('img');
            thumb.src = img.url;
            thumb.alt = img.name;

            const removeBtn = document.createElement('button');
            removeBtn.className = 'preview-remove';
            removeBtn.textContent = '×';
            removeBtn.onclick = () => {
                this.pendingImages.splice(idx, 1);
                this.updateImagePreview();
            };

            item.appendChild(thumb);
            item.appendChild(removeBtn);
            strip.appendChild(item);
        });
    }

    updateOrCreateStreamBubble(type, content) {
        let bubble = document.getElementById('streamBubble');
        if (!bubble) {
            bubble = document.createElement('div');
            bubble.id = 'streamBubble';
            bubble.className = 'message system-message stream-bubble';
            bubble.innerHTML = '<div class="stream-label">💭 Thinking...</div><div class="stream-content"></div>';
            this.els.chatMessages.appendChild(bubble);
        }
        const contentEl = bubble.querySelector('.stream-content');
        if (contentEl) {
            contentEl.textContent = content.substring(0, 300) + (content.length > 300 ? '...' : '');
        }
        this.scrollToBottom();
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
