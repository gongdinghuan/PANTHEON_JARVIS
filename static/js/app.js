// JARVIS Web UI - 前端逻辑

class JarvisApp {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.heartbeatInterval = null;
        this.isProcessing = false;
        this.typewriterQueue = [];
        this.isTyping = false;

        this.currentConfirmationRequestId = null;
        this.confirmationTimer = null;
        this.confirmationTimeout = null;

        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.startHeartbeatPolling();
        this.addStartupMessage();
    }

    addStartupMessage() {
        const now = new Date();
        const hour = now.getHours();
        let greeting = '晚上好';

        if (hour >= 5 && hour < 12) greeting = '早上好';
        else if (hour >= 12 && hour < 18) greeting = '下午好';

        this.addSystemMessage(`${greeting}，Sir！JARVIS 已就绪。`);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket 连接已建立');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
            this.requestSystemStatus();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket 错误:', error);
            this.addSystemMessage('连接错误，正在尝试重新连接...', 'error');
        };

        this.ws.onclose = () => {
            console.log('WebSocket 连接已关闭');
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connectWebSocket();
            }, this.reconnectDelay);
        } else {
            console.error('达到最大重连次数，停止重连');
            this.addSystemMessage('无法连接到服务器，请刷新页面重试', 'error');
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'system':
                this.addSystemMessage(data.message);
                break;
            case 'chat':
                this.isProcessing = false;
                this.removeLoadingIndicator();
                this.isProcessing = false;
                this.removeLoadingIndicator();
                this.addJarvisMessage(data.response);
                break;
            case 'heartbeat':
                this.updateHeartbeatStatus(data.status);
                break;
            case 'status':
                this.updateSystemStatus(data.status);
                break;
            case 'error':
                this.isProcessing = false;
                this.removeLoadingIndicator();
                this.addSystemMessage(`错误: ${data.message}`, 'error');
                break;
            case 'thinking':
                this.showThinkingIndicator(data.message);
                break;
            case 'confirmation':
                this.showConfirmationDialog(data);
                break;
            case 'task_result':
                this.handleTaskResult(data);
                break;
        }
    }

    handleTaskResult(data) {
        const result = data.result;
        const status = result.success ? 'success' : 'error';
        const title = result.success ? '任务完成' : '任务失败';
        const message = `任务 ${data.task_id} 已完成`;

        // 显示系统消息
        this.addSystemMessage(`${title}: ${message}`, status);

        // 如果有离线标记，特别提示
        if (data.offline_completed) {
            this.addSystemMessage(`(此任务在您离线期间完成)`, 'info');
        }

        // 播放提示音 (可选)
        // this.playNotificationSound();

        // 添加到聊天界面
        if (result.output) {
            this.addJarvisMessage({
                content: `### 📋 任务报告: ${data.task_id}\n\n${typeof result.output === 'string' ? result.output : JSON.stringify(result.output, null, 2)}`,
                visualizations: result.visualizations || []
            });
        }
    }

    setupEventListeners() {
        const sendBtn = document.getElementById('sendBtn');
        const voiceBtn = document.getElementById('voiceBtn');
        const messageInput = document.getElementById('messageInput');
        const clearChatBtn = document.getElementById('clearChatBtn');
        const statusBtn = document.getElementById('statusBtn');

        sendBtn.addEventListener('click', () => this.sendMessage());

        voiceBtn.addEventListener('click', () => {
            this.addSystemMessage('语音功能开发中...', 'warning');
        });

        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        clearChatBtn.addEventListener('click', () => {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';
            this.addSystemMessage('对话已清空');
            this.addStartupMessage();
        });

        statusBtn.addEventListener('click', () => {
            this.requestSystemStatus();
            this.addSystemMessage('正在获取系统状态...', 'info');
        });
    }

    sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message || this.isProcessing) return;

        this.isProcessing = true;

        this.addUserMessage(message);
        input.value = '';

        this.showLoadingIndicator();

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                message: message
            }));
        } else {
            this.isProcessing = false;
            this.removeLoadingIndicator();
            this.addSystemMessage('未连接到服务器，无法发送消息', 'error');
        }
    }

    addUserMessage(content) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = content;

        const messageTime = document.createElement('span');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());

        messageContent.appendChild(messageText);
        messageContent.appendChild(messageTime);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    addJarvisMessage(response) {
        // 如果 response 是对象，提取内容；如果是字符串，直接使用
        let content = response;
        if (typeof response === 'object' && response !== null) {
            content = response.content || JSON.stringify(response);
        }

        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message jarvis-message';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>';

        const messageBody = document.createElement('div');
        messageBody.className = 'message-body';

        const messageText = document.createElement('div');
        messageText.className = 'message-text formatted-text';

        const messageTime = document.createElement('span');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());

        messageBody.appendChild(messageText);
        messageBody.appendChild(messageTime);
        messageContent.appendChild(avatar);
        messageContent.appendChild(messageBody);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);

        this.formatMessage(messageText, content);
        chatMessages.appendChild(messageDiv);

        // 处理可视化 (visualizations)
        if (response.visualizations && response.visualizations.length > 0) {
            response.visualizations.forEach(viz => {
                this.renderVisualization(messageBody, viz);
            });
        }

        // 处理文件附件 (attachments)
        if (response.attachments && response.attachments.length > 0) {
            response.attachments.forEach(attachment => {
                this.renderAttachment(messageBody, attachment);
            });
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    renderAttachment(container, attachment) {
        const attachmentCard = document.createElement('div');
        attachmentCard.className = 'attachment-card';
        attachmentCard.innerHTML = `
            <div class="attachment-icon">${attachment.icon || '📄'}</div>
            <div class="attachment-info">
                <div class="attachment-title">${attachment.title}</div>
                <div class="attachment-meta">
                    <span>${attachment.file_type.toUpperCase()}</span>
                    <span>${attachment.file_size_text}</span>
                    <span>${this.formatTime(new Date(attachment.created_at))}</span>
                </div>
            </div>
            <div class="attachment-actions">
                <button class="btn-preview" onclick="jarvisApp.previewReport('${attachment.id}')">
                    👁️ 预览
                </button>
                <a class="btn-download" href="${attachment.download_url}" download>
                    📥 下载
                </a>
            </div>
        `;
        container.appendChild(attachmentCard);
    }

    async previewReport(reportId) {
        try {
            const response = await fetch(`/api/reports/${reportId}/preview`);
            if (!response.ok) throw new Error('无法加载报告');

            const data = await response.json();
            this.showReportModal(data);
        } catch (error) {
            console.error('预览报告失败:', error);
            alert('预览失败: ' + error.message);
        }
    }

    showReportModal(report) {
        // 移除现有模态框
        const existing = document.querySelector('.report-modal-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.className = 'report-modal-overlay';
        overlay.onclick = (e) => {
            if (e.target === overlay) overlay.remove();
        };

        const modal = document.createElement('div');
        modal.className = 'report-modal';

        let contentHtml = '';
        if (report.file_type === 'html') {
            // HTML 报告使用 iframe 直接展示
            const blob = new Blob([report.content], { type: 'text/html' });
            const blobUrl = URL.createObjectURL(blob);
            contentHtml = `<iframe src="${blobUrl}" class="report-iframe"></iframe>`;
        } else if (report.file_type === 'md' && typeof marked !== 'undefined') {
            contentHtml = marked.parse(report.content);
        } else {
            contentHtml = `<pre>${this.escapeHtml(report.content)}</pre>`;
        }

        const newTabButton = report.file_type === 'html'
            ? `<button class="btn-newtab" onclick="jarvisApp.openReportNewTab('${report.id}')">🔗 新标签页打开</button>`
            : '';

        modal.innerHTML = `
            <div class="report-modal-header">
                <h2>${report.title}</h2>
                <button class="report-modal-close" onclick="this.closest('.report-modal-overlay').remove()">✕</button>
            </div>
            <div class="report-modal-content">${contentHtml}</div>
            <div class="report-modal-footer">
                ${newTabButton}
                <a href="/api/reports/${report.id}/download" class="btn-download-full" download>📥 下载报告</a>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);
    }

    async openReportNewTab(reportId) {
        try {
            const response = await fetch(`/api/reports/${reportId}/preview`);
            if (!response.ok) throw new Error('无法加载报告');

            const data = await response.json();
            if (data.file_type === 'html') {
                const blob = new Blob([data.content], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                window.open(url, '_blank');
            }
        } catch (error) {
            console.error('打开报告失败:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    renderVisualization(container, viz) {
        const vizContainer = document.createElement('div');
        vizContainer.className = 'visualization-container';
        vizContainer.style.width = '100%';
        vizContainer.style.height = '400px';
        vizContainer.style.marginTop = '15px';
        container.appendChild(vizContainer);

        if (viz.type === 'echarts' && viz.option) {
            // 确保 ECharts 已加载
            if (typeof echarts !== 'undefined') {
                const chart = echarts.init(vizContainer);
                // 使用深色主题配置
                const darkOption = {
                    ...viz.option,
                    backgroundColor: 'transparent',
                    textStyle: { color: 'rgba(255, 255, 255, 0.8)' },
                    title: {
                        ...viz.option.title,
                        textStyle: { color: '#00d4ff' }
                    }
                };
                chart.setOption(darkOption);

                // 窗口大小改变时重绘
                window.addEventListener('resize', () => chart.resize());
            } else {
                vizContainer.textContent = '图表加载失败: ECharts 库未找到';
            }
        } else if (viz.type === 'card' && viz.data) {
            vizContainer.style.height = 'auto'; // 卡片高度自适应
            vizContainer.innerHTML = `
                <div class="data-card" style="background: rgba(0, 212, 255, 0.05); border: 1px solid rgba(0, 212, 255, 0.2); border-radius: 8px; padding: 15px;">
                    <div style="font-size: 1.2em; color: #00d4ff; margin-bottom: 5px;">${viz.data.title}</div>
                    <div style="display: flex; align-items: baseline; margin-bottom: 15px;">
                        <span style="font-size: 2em; font-weight: bold;">${viz.data.value}</span>
                        <span style="margin-left: 10px; font-size: 0.8em; color: rgba(255,255,255,0.5);">${viz.data.sub_value}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        ${viz.data.details.map(item => `
                            <div>
                                <div style="font-size: 0.8em; color: rgba(255,255,255,0.5);">${item.label}</div>
                                <div>${item.value}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    }

    formatMessage(element, content) {
        if (typeof marked !== 'undefined' && marked.parse) {
            try {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    tables: true,
                    smartLists: true,
                    smartypants: false
                });

                element.innerHTML = marked.parse(content);
                this.highlightCode(element);
                this.enhanceTables(element);
            } catch (e) {
                element.textContent = content;
            }
        } else {
            element.innerHTML = this.simpleFormat(content);
        }
    }

    enhanceTables(element) {
        element.querySelectorAll('table').forEach(table => {
            table.classList.add('markdown-table');
        });
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            if (connected) {
                statusElement.classList.remove('disconnected');
                statusElement.querySelector('.status-text').textContent = '已连接';
            } else {
                statusElement.classList.add('disconnected');
                statusElement.querySelector('.status-text').textContent = '未连接';
            }
        }
    }

    simpleFormat(text) {
        return text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
    }

    highlightCode(element) {
        element.querySelectorAll('pre code').forEach((block) => {
            const language = block.className.match(/language-(\w+)/);
            if (language) {
                block.classList.add('highlighted');
            }
        });
    }

    showLoadingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message jarvis-message loading-message';
        loadingDiv.id = 'loadingIndicator';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar loading';

        const dots = document.createElement('div');
        dots.className = 'loading-dots';
        dots.innerHTML = '<span></span><span></span><span></span>';

        messageContent.appendChild(avatar);
        messageContent.appendChild(dots);
        loadingDiv.appendChild(messageContent);

        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    removeLoadingIndicator() {
        const loading = document.getElementById('loadingIndicator');
        if (loading) {
            loading.remove();
        }
    }

    showThinkingIndicator(message) {
        const thinking = document.getElementById('thinkingIndicator');
        if (!thinking) {
            const chatMessages = document.getElementById('chatMessages');
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'thinking-indicator';
            thinkingDiv.id = 'thinkingIndicator';
            thinkingDiv.innerHTML = `
                <div class="thinking-icon">💭</div>
                <div class="thinking-text">${this.escapeHtml(message)}</div>
            `;
            chatMessages.appendChild(thinkingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            setTimeout(() => {
                thinkingDiv.remove();
            }, 3000);
        }
    }

    addSystemMessage(message, type = 'info') {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message system-message ${type}-message`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const icon = document.createElement('span');
        icon.className = 'system-icon';

        switch (type) {
            case 'error':
                icon.textContent = '❌';
                break;
            case 'warning':
                icon.textContent = '⚠️';
                break;
            case 'success':
                icon.textContent = '✅';
                break;
            default:
                icon.textContent = 'ℹ️';
        }

        const messageText = document.createElement('span');
        messageText.className = 'system-text';
        messageText.textContent = message;

        const messageTime = document.createElement('span');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());

        messageContent.appendChild(icon);
        messageContent.appendChild(messageText);
        messageContent.appendChild(messageTime);
        messageDiv.appendChild(messageContent);

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    updateHeartbeatStatus(statusText) {
        const lines = statusText.split('\n');
        let uptime = '--';
        let requests = '--';
        let heartbeats = '--';
        let currentTime = '--';

        lines.forEach(line => {
            if (line.includes('运行时长')) {
                uptime = line.split(':').slice(1).join(':').trim() || '--';
            } else if (line.includes('会话请求')) {
                requests = line.split(':').slice(1).join(':').trim() || '--';
            } else if (line.includes('心跳次数')) {
                heartbeats = line.split(':').slice(1).join(':').trim() || '--';
            } else if (line.includes('当前时间')) {
                currentTime = line.split(':').slice(1).join(':').trim() || '--';
            }
        });

        document.getElementById('uptimeValue').textContent = uptime;
        document.getElementById('requestsValue').textContent = requests;
        document.getElementById('heartbeatValue').textContent = '60 BPM';

        if (currentTime !== '--') {
            document.getElementById('currentTimeValue')?.remove();
            const timeEl = document.createElement('div');
            timeEl.id = 'currentTimeValue';
            timeEl.className = 'current-time';
            timeEl.textContent = currentTime;
            document.querySelector('.status-panel .panel-content')?.prepend(timeEl);
        }
    }

    updateSystemStatus(status) {
        if (status.session) {
            const pendingTasks = status.session.pending_tasks || 0;
            const taskStatus = document.getElementById('taskStatus');
            const taskCount = document.getElementById('taskCount');

            if (pendingTasks > 0) {
                taskStatus.style.display = 'flex';
                taskCount.textContent = pendingTasks;
            } else {
                taskStatus.style.display = 'none';
            }
        }

        if (status.system) {
            this.updateSystemInfo(status.system);
        }

        if (status.time) {
            this.updateTimeInfo(status.time);
        }

        if (status.heartbeat) {
            document.getElementById('requestsValue').textContent = `${status.heartbeat.total_requests} 次`;

            if (status.heartbeat.current_time) {
                const time = status.heartbeat.current_time.time || '--';
                document.getElementById('heartbeatValue').textContent = time;
            }
        }

        if (status.memory) {
            const skillsEl = document.getElementById('skillsValue');
            if (skillsEl) {
                skillsEl.textContent = `${status.memory.short_term_turns || 0} 条`;
            }
        }

        if (status.resources) {
            this.updateResources(status.resources);
        }
    }

    updateSystemInfo(system) {
        const existingInfo = document.getElementById('systemInfoPanel');

        if (!existingInfo) {
            const statusSection = document.querySelector('.status-section');
            const infoPanel = document.createElement('div');
            infoPanel.className = 'status-panel system-info-panel';
            infoPanel.id = 'systemInfoPanel';
            infoPanel.innerHTML = `
                <div class="panel-header">
                    <h3>系统信息</h3>
                </div>
                <div class="panel-content">
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-label">系统</span>
                            <span class="info-value">${system.os || 'Unknown'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">平台</span>
                            <span class="info-value">${system.platform || 'Unknown'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">架构</span>
                            <span class="info-value">${system.arch || 'Unknown'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">主机</span>
                            <span class="info-value">${system.hostname || 'Unknown'}</span>
                        </div>
                    </div>
                </div>
            `;
            statusSection.insertBefore(infoPanel, statusSection.firstChild);
        }
    }

    updateTimeInfo(time) {
        const existingTime = document.getElementById('timeInfoPanel');

        if (!existingTime) {
            const statusSection = document.querySelector('.status-section');
            const timePanel = document.createElement('div');
            timePanel.className = 'status-panel time-info-panel';
            timePanel.id = 'timeInfoPanel';
            timePanel.innerHTML = `
                <div class="panel-header">
                    <h3>时间信息</h3>
                </div>
                <div class="panel-content">
                    <div class="time-grid">
                        <div class="time-item">
                            <span class="time-label">启动时间</span>
                            <span class="time-value">${time.start_time || '--'}</span>
                        </div>
                        <div class="time-item">
                            <span class="time-label">启动时段</span>
                            <span class="time-value">${time.start_period || '--'}</span>
                        </div>
                        <div class="time-item">
                            <span class="time-label">时区</span>
                            <span class="time-value">${time.timezone || '--'}</span>
                        </div>
                    </div>
                </div>
            `;
            statusSection.insertBefore(timePanel, statusSection.firstChild);
        }
    }

    updateResources(resources) {
        const existingRes = document.getElementById('resourcesPanel');

        if (!existingRes) {
            const statusSection = document.querySelector('.status-section');
            const resPanel = document.createElement('div');
            resPanel.className = 'status-panel resources-panel';
            resPanel.id = 'resourcesPanel';
            resPanel.innerHTML = `
                <div class="panel-header">
                    <h3>资源使用</h3>
                </div>
                <div class="panel-content">
                    <div class="resource-item">
                        <span class="resource-label">CPU</span>
                        <div class="resource-bar">
                            <div class="resource-fill cpu-fill" style="width: ${resources.cpu_percent || 0}%"></div>
                        </div>
                        <span class="resource-value">${(resources.cpu_percent || 0).toFixed(1)}%</span>
                    </div>
                    <div class="resource-item">
                        <span class="resource-label">内存</span>
                        <div class="resource-bar">
                            <div class="resource-fill memory-fill" style="width: ${resources.memory_percent || 0}%"></div>
                        </div>
                        <span class="resource-value">${(resources.memory_percent || 0).toFixed(1)}%</span>
                    </div>
                </div>
            `;
            statusSection.appendChild(resPanel);
        } else {
            existingRes.querySelector('.cpu-fill').style.width = `${resources.cpu_percent || 0}%`;
            existingRes.querySelector('.resource-value').textContent = `${(resources.cpu_percent || 0).toFixed(1)}%`;
        }
    }

    updateTasksList(tasks) {
        const tasksList = document.getElementById('tasksList');

        if (!tasks || Object.keys(tasks).length === 0) {
            tasksList.innerHTML = '<p class="empty-state">暂无后台任务</p>';
            return;
        }

        tasksList.innerHTML = '';
        Object.entries(tasks).forEach(([taskId, task]) => {
            const taskDiv = document.createElement('div');
            taskDiv.className = 'task-item';

            const taskInfo = document.createElement('div');
            taskInfo.className = 'task-info';

            const taskName = document.createElement('div');
            taskName.className = 'task-name';
            taskName.textContent = task.name || taskId;

            const taskIdSpan = document.createElement('span');
            taskIdSpan.className = 'task-id';
            taskIdSpan.textContent = taskId;

            const taskMeta = document.createElement('div');
            taskMeta.className = 'task-meta';

            const taskStatus = document.createElement('span');
            taskStatus.className = `task-status ${task.status}`;
            taskStatus.textContent = this.translateStatus(task.status);

            const taskProgress = document.createElement('div');
            taskProgress.className = 'task-progress';

            const progressBar = document.createElement('div');
            progressBar.className = 'progress-bar';

            const progressFill = document.createElement('div');
            progressFill.className = 'progress-fill';
            progressFill.style.width = `${(task.progress || 0) * 100}%`;

            progressBar.appendChild(progressFill);
            taskProgress.appendChild(progressBar);

            taskInfo.appendChild(taskName);
            taskInfo.appendChild(taskIdSpan);
            taskMeta.appendChild(taskStatus);
            taskMeta.appendChild(taskProgress);

            taskDiv.appendChild(taskInfo);
            taskDiv.appendChild(taskMeta);
            tasksList.appendChild(taskDiv);
        });
    }

    translateStatus(status) {
        const statusMap = {
            'pending': '等待中',
            'running': '运行中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消'
        };
        return statusMap[status] || status;
    }

    startHeartbeatPolling() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'heartbeat' }));
            }
        }, 30000);
    }

    requestSystemStatus() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'status' }));
        }
    }

    updateConnectionStatus(connected) {
        const statusIndicator = document.querySelector('.status-indicator');

        if (connected) {
            statusIndicator.classList.remove('offline');
            statusIndicator.classList.add('online');
        } else {
            statusIndicator.classList.remove('online');
            statusIndicator.classList.add('offline');
        }
    }

    formatTime(date) {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showConfirmationDialog(data) {
        const modal = document.getElementById('confirmationModal');
        const messageEl = document.getElementById('confirmationMessage');
        const detailsEl = document.getElementById('confirmationDetails');
        const btnConfirm = document.getElementById('btnConfirm');
        const btnReject = document.getElementById('btnReject');

        this.currentConfirmationRequestId = data.request_id;

        const actionText = this.getActionText(data.action);
        messageEl.textContent = `是否允许执行 '${data.action}' 操作？`;

        if (data.details && Object.keys(data.details).length > 0) {
            detailsEl.innerHTML = '<strong>参数：</strong><br>' +
                Object.entries(data.details)
                    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
                    .join('<br>');
        } else {
            detailsEl.textContent = '参数: {}';
        }

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';

        const timeout = data.timeout || 30;
        this.startConfirmationTimer(timeout);

        btnConfirm.onclick = () => {
            this.handleConfirmationResponse(true);
        };

        btnReject.onclick = () => {
            this.handleConfirmationResponse(false);
        };
    }

    getActionText(action) {
        const actionMap = {
            'terminal': '终端命令',
            'file_delete': '文件删除',
            'file_write': '文件写入',
            'system_control': '系统控制',
            'learn_command': '学习命令'
        };
        return actionMap[action] || action;
    }

    startConfirmationTimer(seconds) {
        const timerText = document.getElementById('timerText');
        const timerProgress = document.getElementById('timerProgress');
        let remaining = seconds;
        const circumference = 163.36;

        timerText.textContent = remaining;

        clearInterval(this.confirmationTimer);
        clearTimeout(this.confirmationTimeout);

        this.confirmationTimer = setInterval(() => {
            remaining--;
            timerText.textContent = remaining;

            const offset = circumference * (1 - remaining / seconds);
            timerProgress.style.strokeDashoffset = offset;

            if (remaining <= 0) {
                this.handleConfirmationResponse(false);
            }
        }, 1000);

        this.confirmationTimeout = setTimeout(() => {
            this.handleConfirmationResponse(false);
        }, seconds * 1000);
    }

    handleConfirmationResponse(confirmed) {
        clearInterval(this.confirmationTimer);
        clearTimeout(this.confirmationTimeout);

        const modal = document.getElementById('confirmationModal');
        modal.style.display = 'none';
        document.body.style.overflow = '';

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'confirm_response',
                request_id: this.currentConfirmationRequestId,
                action: confirmed ? 'confirm' : 'reject'
            }));
        }

        this.currentConfirmationRequestId = null;

        if (!confirmed) {
            this.addSystemMessage('操作已拒绝', 'warning');
        }
    }
}


class SettingsManager {
    constructor() {
        this.modal = document.getElementById('settingsModal');
        this.setupEventListeners();
        this.loadCurrentConfig();
    }

    setupEventListeners() {
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.show());
        }

        const closeBtn = document.getElementById('closeSettingsBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        const providerSelect = document.getElementById('providerSelect');
        if (providerSelect) {
            providerSelect.addEventListener('change', (e) => {
                this.onProviderChange(e.target.value);
            });
        }

        const temperatureInput = document.getElementById('temperatureInput');
        if (temperatureInput) {
            temperatureInput.addEventListener('input', (e) => {
                document.getElementById('temperatureValue').textContent = e.target.value;
            });
        }

        const testBtn = document.getElementById('testBtn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testConnection());
        }

        const saveBtn = document.getElementById('saveConfigBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveConfig());
        }

        this.modal.querySelector('.settings-overlay').addEventListener('click', () => this.hide());
    }

    async loadCurrentConfig() {
        try {
            const response = await fetch('/api/config/llm');
            if (response.ok) {
                const config = await response.json();
                this.populateForm(config);
            }
        } catch (e) {
            console.error('加载配置失败:', e);
        }
    }

    populateForm(config) {
        const providerSelect = document.getElementById('providerSelect');
        providerSelect.value = config.provider || 'deepseek';

        this.onProviderChange(config.provider);

        document.getElementById('apiKeyInput').value = config[`${config.provider}_api_key`] || '';
        document.getElementById('baseUrlInput').value = config[`${config.provider}_base_url`] || '';
        document.getElementById('modelInput').value = config[`${config.provider}_model`] || '';
        document.getElementById('temperatureInput').value = config.temperature || 0.7;
        document.getElementById('temperatureValue').textContent = config.temperature || 0.7;
        document.getElementById('maxTokensInput').value = config.max_tokens || 8096;
    }

    onProviderChange(provider) {
        const defaults = {
            nvidia: {
                baseUrl: 'https://integrate.api.nvidia.com/v1',
                model: 'minimaxai/minimax-m2.1'
            },
            deepseek: {
                baseUrl: 'https://api.deepseek.com',
                model: 'deepseek-chat'
            },
            ollama: {
                baseUrl: 'http://localhost:11434',
                model: 'llama3'
            },
            openai: {
                baseUrl: 'https://api.openai.com/v1',
                model: 'gpt-4o'
            }
        };

        const config = defaults[provider];
        if (config) {
            document.getElementById('baseUrlInput').value = config.baseUrl;
            document.getElementById('modelInput').value = config.model;
        }
    }

    getFormConfig() {
        const provider = document.getElementById('providerSelect').value;
        return {
            provider: provider,
            [`${provider}_api_key`]: document.getElementById('apiKeyInput').value,
            [`${provider}_base_url`]: document.getElementById('baseUrlInput').value,
            [`${provider}_model`]: document.getElementById('modelInput').value,
            temperature: parseFloat(document.getElementById('temperatureInput').value),
            max_tokens: parseInt(document.getElementById('maxTokensInput').value),
        };
    }

    async testConnection() {
        const config = this.getFormConfig();
        const testBtn = document.getElementById('testBtn');
        const originalText = testBtn.textContent;

        try {
            testBtn.textContent = '测试中...';
            testBtn.disabled = true;

            const response = await fetch('/api/config/llm/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            const result = await response.json();

            if (result.success) {
                alert('✓ 连接成功！\n响应: ' + (result.response || 'OK'));
            } else {
                alert('✕ 连接失败：' + result.error);
            }
        } catch (e) {
            alert('✕ 连接失败：' + e.message);
        } finally {
            testBtn.textContent = originalText;
            testBtn.disabled = false;
        }
    }

    async saveConfig() {
        const config = this.getFormConfig();
        const saveBtn = document.getElementById('saveConfigBtn');
        const originalText = saveBtn.textContent;

        try {
            saveBtn.textContent = '保存中...';
            saveBtn.disabled = true;

            const response = await fetch('/api/config/llm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                alert('✓ 配置已保存，LLM 已重新初始化');
                this.hide();
            } else {
                const error = await response.json();
                alert('✕ 保存失败：' + (error.detail || '未知错误'));
            }
        } catch (e) {
            alert('✕ 保存失败：' + e.message);
        } finally {
            saveBtn.textContent = originalText;
            saveBtn.disabled = false;
        }
    }

    show() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    hide() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.jarvisApp = new JarvisApp();
    window.settingsManager = new SettingsManager();
});
