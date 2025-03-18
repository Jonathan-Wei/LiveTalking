import json
import time
from typing import Dict, Set, List
from logger import logger

# 存储所有活跃的WebSocket连接
active_connections: Dict[int, Set] = {}
# 存储连接状态信息
connection_stats: Dict[int, Dict] = {}

async def register_websocket(ws, session_id: int):
    """
    注册一个新的WebSocket连接
    
    Args:
        ws: WebSocket连接对象
        session_id: 会话ID
    """
    # 记录客户端信息
    client_info = {
        "remote": str(ws._req.remote) if hasattr(ws, "_req") and hasattr(ws._req, "remote") else "未知",
        "headers": dict(ws._req.headers) if hasattr(ws, "_req") and hasattr(ws._req, "headers") else {},
        "connect_time": time.time(),
        "last_active_time": time.time(),
        "message_count": 0,
        "error_count": 0
    }
    
    if session_id not in active_connections:
        active_connections[session_id] = set()
        connection_stats[session_id] = {}
    
    active_connections[session_id].add(ws)
    connection_stats[session_id][id(ws)] = client_info
    
    logger.info(f"WebSocket连接已注册 [会话ID: {session_id}] [客户端: {client_info['remote']}] [连接数: {len(active_connections[session_id])}]")
    logger.debug(f"WebSocket连接详情 [会话ID: {session_id}] [UA: {client_info['headers'].get('User-Agent', '未知')}]")

async def unregister_websocket(ws, session_id: int):
    """
    注销一个WebSocket连接
    
    Args:
        ws: WebSocket连接对象
        session_id: 会话ID
    """
    if session_id in active_connections:
        # 获取连接时长信息
        ws_id = id(ws)
        connection_info = ""
        if session_id in connection_stats and ws_id in connection_stats[session_id]:
            client_info = connection_stats[session_id][ws_id]
            duration = time.time() - client_info["connect_time"]
            connection_info = f"[客户端: {client_info['remote']}] [连接时长: {duration:.2f}秒] [消息数: {client_info['message_count']}]"
            # 清理连接状态信息
            del connection_stats[session_id][ws_id]
        
        # 移除连接
        active_connections[session_id].discard(ws)
        if len(active_connections[session_id]) == 0:
            del active_connections[session_id]
            if session_id in connection_stats:
                del connection_stats[session_id]
            logger.info(f"WebSocket会话已完全关闭 [会话ID: {session_id}] {connection_info}")
        else:
            logger.info(f"WebSocket连接已注销 [会话ID: {session_id}] [剩余连接数: {len(active_connections[session_id])}] {connection_info}")

async def send_message(session_id: int, message: str, dialogId: str, message_type: str = "ai_message"):
    """
    向指定会话ID的所有WebSocket连接发送消息
    
    Args:
        session_id: 会话ID
        message: 要发送的消息内容
        message_type: 消息类型，默认为ai_message
    """

    logger.info(f"send_message: {session_id} {message} {dialogId} {message_type}")
    # 确保session_id是整数类型
    try:
        session_id = int(session_id)
    except (ValueError, TypeError):
        logger.error(f"无效的会话ID: {session_id}，必须为整数")
        return
    # 如果会话ID不存在，创建一个空的连接集合，以便后续连接可以加入
    if session_id not in active_connections:
        active_connections[session_id] = set()
        connection_stats[session_id] = {}
        logger.info(f"为会话ID {session_id} 创建了新的连接集合")
        
    if len(active_connections[session_id]) > 0:
        data = json.dumps({
            "type": message_type,
            "content": message,
            "dialogId": dialogId
        })
        
        # 获取连接集合的副本，以避免在迭代过程中修改集合
        connections = active_connections[session_id].copy()
        message_preview = message[:50] + "..." if len(message) > 50 else message
        logger.info(f"准备发送消息 [会话ID: {session_id}] [连接数: {len(connections)}] [类型: {message_type}] [内容预览: {message_preview}]")
        
        success_count = 0
        error_count = 0
        
        for ws in connections:
            try:
                await ws.send_str(data)
                success_count += 1
                
                # 更新连接状态
                ws_id = id(ws)
                if session_id in connection_stats and ws_id in connection_stats[session_id]:
                    connection_stats[session_id][ws_id]["last_active_time"] = time.time()
                    connection_stats[session_id][ws_id]["message_count"] += 1
                
            except Exception as e:
                error_count += 1
                ws_id = id(ws)
                client_info = "未知客户端"
                if session_id in connection_stats and ws_id in connection_stats[session_id]:
                    client_info = connection_stats[session_id][ws_id]["remote"]
                    connection_stats[session_id][ws_id]["error_count"] += 1
                
                logger.error(f"发送WebSocket消息失败 [会话ID: {session_id}] [客户端: {client_info}] [错误: {str(e)}]")
                # 如果发送失败，可能是连接已关闭，尝试注销该连接
                await unregister_websocket(ws, session_id)
        
        logger.info(f"消息发送完成 [会话ID: {session_id}] [成功: {success_count}] [失败: {error_count}]")
    else:
        logger.warning(f"尝试向不存在的会话 {session_id} 发送消息，但该会话不存在或没有活跃连接")