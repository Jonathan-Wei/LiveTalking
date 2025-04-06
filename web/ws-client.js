/**
 * WebSocket客户端
 * 用于处理与服务器的WebSocket连接和消息接收
 * 包含心跳机制和连接状态监控
 */

class WebSocketClient {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10; // 增加最大重连次数
        this.reconnectInterval = 2000; // 初始重连间隔为2秒
        this.reconnectBackoffFactor = 1.5; // 指数退避因子
        this.maxReconnectInterval = 30000; // 最大重连间隔为30秒
        this.messageHandlers = [];
        this.heartbeatInterval = null;
        this.heartbeatTimeout = null;
        this.lastHeartbeatTime = 0;
        this.connectionStartTime = 0;
        this.connectionId = Math.random().toString(36).substring(2, 10); // 生成唯一连接ID用于日志
        
        // 设置页面卸载事件处理
        this.setupPageUnloadHandler();
    }

    /**
     * 连接到WebSocket服务器
     */
    connect() {
        // 如果已经连接，则不再重复连接
        if (this.isConnected) return;

        // 构建WebSocket URL，包含会话ID和连接ID
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws?sessionid=${this.sessionId}&connid=${this.connectionId}`;

        console.log(`正在连接WebSocket: ${wsUrl} (尝试: ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.connectionStartTime = Date.now();
        } catch (error) {
            console.error('创建WebSocket连接失败:', error);
            this.reconnect();
            return;
        }

        // 连接建立时的处理
        this.socket.onopen = () => {
            console.log('WebSocket连接已建立');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            // 启动心跳
            this.startHeartbeat();
        };

        // 接收消息的处理
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('收到WebSocket消息:', data);
                
                // 处理心跳响应
                if (data.type === 'heartbeat_response') {
                    this.lastHeartbeatTime = Date.now();
                    console.log('收到心跳响应');
                    return;
                }
                
                // 处理连接状态消息
                if (data.type === 'connection_status') {
                    console.log('连接状态更新:', data.status);
                    return;
                }
                
                // 调用所有注册的消息处理函数
                this.messageHandlers.forEach(handler => handler(data));
                
                // 如果是AI消息，添加到聊天容器
                if (data.type === 'ai_message') {
                    this.addMessageToChat(data.content, data.dialogId,'ai');
                }
            } catch (error) {
                console.error('解析WebSocket消息失败:', error);
            }
        };

        // 连接关闭时的处理
        this.socket.onclose = (event) => {
            const duration = (Date.now() - this.connectionStartTime) / 1000;
            console.log(`WebSocket连接已关闭 [代码: ${event.code}] [原因: ${event.reason || '未知'}] [连接时长: ${duration.toFixed(2)}秒]`);
            this.isConnected = false;
            this.stopHeartbeat();
            this.reconnect();
        };

        // 连接错误时的处理
        this.socket.onerror = (error) => {
            console.error('WebSocket连接错误:', error);
            this.isConnected = false;
            this.stopHeartbeat();
        };
    }

    /**
     * 重新连接WebSocket
     */
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log(`达到最大重连次数(${this.maxReconnectAttempts})，停止重连`);
            // 通知用户连接已断开
            this.notifyConnectionLost();
            return;
        }

        this.reconnectAttempts++;
        
        // 使用指数退避策略计算下一次重连间隔
        const currentInterval = Math.min(
            this.reconnectInterval * Math.pow(this.reconnectBackoffFactor, this.reconnectAttempts - 1),
            this.maxReconnectInterval
        );
        
        console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，等待时间: ${(currentInterval/1000).toFixed(1)}秒`);
        
        setTimeout(() => {
            console.log(`开始第${this.reconnectAttempts}次重连...`);
            this.connect();
        }, currentInterval);
    }

    /**
     * 关闭WebSocket连接
     */
    disconnect() {
        if (this.socket) {
            this.stopHeartbeat();
            this.socket.close();
            this.socket = null;
            this.isConnected = false;
        }
    }
    
    /**
     * 启动心跳机制
     */
    startHeartbeat() {
        // 清除可能存在的旧心跳
        this.stopHeartbeat();
        
        // 初始化最后心跳时间为当前时间
        this.lastHeartbeatTime = Date.now();
        
        // 每10秒发送一次心跳（确保在服务器15秒超时前发送）
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected && this.socket && this.socket.readyState === WebSocket.OPEN) {
                try {
                    // 检查上次心跳是否超时（如果上次心跳已经超过30秒没有响应）
                    const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeatTime;
                    if (timeSinceLastHeartbeat > 30000) {
                        console.warn(`心跳长时间无响应 (${(timeSinceLastHeartbeat/1000).toFixed(1)}秒)，重新连接...`);
                        this.disconnect();
                        setTimeout(() => this.connect(), 1000);
                        return;
                    }
                    
                    // 发送心跳消息
                    const heartbeatData = {
                        type: 'heartbeat',
                        timestamp: Date.now(),
                        client_info: {
                            reconnect_attempts: this.reconnectAttempts,
                            connection_time: (Date.now() - this.connectionStartTime) / 1000
                        }
                    };
                    
                    this.socket.send(JSON.stringify(heartbeatData));
                    console.log('发送心跳消息', heartbeatData.timestamp);
                    
                    // 设置心跳超时检测
                    if (this.heartbeatTimeout) {
                        clearTimeout(this.heartbeatTimeout);
                    }
                    
                    this.heartbeatTimeout = setTimeout(() => {
                        const responseTime = Date.now() - heartbeatData.timestamp;
                        console.warn(`心跳响应超时 (${(responseTime/1000).toFixed(1)}秒)，连接可能已断开`);
                        
                        // 如果超过15秒没有收到响应，认为连接已断开（增加超时时间，避免频繁断开重连）
                        if (Date.now() - this.lastHeartbeatTime > 15000) {
                            console.error('心跳无响应，尝试重新连接');
                            this.disconnect();
                            setTimeout(() => this.connect(), 1000);
                        }
                    }, 3000);
                } catch (error) {
                    console.error('发送心跳消息失败:', error);
                    // 发送失败也可能是连接问题，尝试重连
                    this.disconnect();
                    setTimeout(() => this.connect(), 2000);
                }
            }
        }, 20000);
    }
    
    /**
     * 停止心跳机制
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        if (this.heartbeatTimeout) {
            clearTimeout(this.heartbeatTimeout);
            this.heartbeatTimeout = null;
        }
    }

    /**
     * 注册消息处理函数
     * @param {Function} handler - 消息处理函数
     */
    onMessage(handler) {
        if (typeof handler === 'function') {
            this.messageHandlers.push(handler);
        }
    }

    /**
     * 添加消息到聊天容器
     * @param {string} message - 消息内容
     * @param {string} sender - 发送者类型（'user'或'ai'）
     */
    addMessageToChat(message,dialogId, sender='user') {
        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;

        // 检查是否已经有相同内容的最后一条消息
        const lastMessage = chatContainer.lastElementChild;
        if (lastMessage && lastMessage.classList.contains(sender + '-message') && lastMessage.id.includes(dialogId+'-message')) {
            // 获取ai-message元素的内容，并将新消息追加到末尾
            // document.getElementById('ai-message').textContent += message;
            // 如果最后一条消息是同一发送者的，则追加内容而不是创建新消息

            lastMessage.textContent += message;
        } else {
            // 创建新的消息元素
            const messageElement = document.createElement('div');
            messageElement.classList.add('chat-message');
            messageElement.classList.add(sender + '-message');
            messageElement.style.whiteSpace = 'pre-line';
            messageElement.id = dialogId + '-message';
            messageElement.textContent = message;
            chatContainer.appendChild(messageElement);
        }

        // 滚动到底部
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    /**
     * 设置页面卸载事件处理
     * 在页面刷新或关闭前正确关闭WebSocket连接
     */
    setupPageUnloadHandler() {
        const handleUnload = () => {
            console.log('页面即将卸载，正在关闭WebSocket连接...');
            // 使用同步方式关闭连接，确保在页面卸载前完成
            if (this.socket && this.isConnected) {
                // 停止心跳检测
                this.stopHeartbeat();
                
                // 关闭WebSocket连接
                // 使用同步方式关闭，不使用reconnect机制
                this.socket.onclose = null; // 移除onclose处理器，避免触发重连
                this.socket.close(1000, "页面卸载");
                this.socket = null;
                this.isConnected = false;
                
                console.log('WebSocket连接已在页面卸载前关闭');
            }
        };
        
        // 监听页面卸载事件
        window.addEventListener('beforeunload', handleUnload);
        window.addEventListener('unload', handleUnload);
    }
    
    /**
     * 通知用户连接已断开
     */
    notifyConnectionLost() {
        console.warn('WebSocket连接已断开，请刷新页面重试');
        // 可以在这里添加UI通知
    }
}

// 导出WebSocketClient类
window.WebSocketClient = WebSocketClient;
