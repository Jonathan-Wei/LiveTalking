import asyncio
import time
from logger import logger
from websocket_manager import active_connections, connection_stats, unregister_websocket

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 50
# 心跳检查间隔（秒）
HEARTBEAT_INTERVAL = 30

async def send_heartbeat(ws, session_id):
    """
    向指定的WebSocket连接发送心跳消息
    
    Args:
        ws: WebSocket连接对象
        session_id: 会话ID
    
    Returns:
        bool: 心跳是否成功发送
    """
    try:
        await ws.send_json({"type": "heartbeat", "timestamp": time.time()})
        logger.debug(f"心跳消息已发送 [会话ID: {session_id}] [客户端: {id(ws)}]")
        return True
    except Exception as e:
        ws_id = id(ws)
        client_info = "未知客户端"
        if session_id in connection_stats and ws_id in connection_stats[session_id]:
            client_info = connection_stats[session_id][ws_id]["remote"]
        
        logger.warning(f"心跳消息发送失败 [会话ID: {session_id}] [客户端: {client_info}] [错误: {str(e)}]")
        return False

async def check_connections():
    """
    定期检查所有WebSocket连接的状态，移除超时的连接
    """
    while True:
        try:
            current_time = time.time()
            sessions_to_check = list(active_connections.keys())
            
            for session_id in sessions_to_check:
                if session_id not in active_connections:
                    continue
                    
                # 获取连接集合的副本
                connections = active_connections[session_id].copy()
                inactive_count = 0
                
                for ws in connections:
                    ws_id = id(ws)
                    if session_id in connection_stats and ws_id in connection_stats[session_id]:
                        last_active_time = connection_stats[session_id][ws_id]["last_active_time"]
                        inactive_duration = current_time - last_active_time
                        
                        # 如果连接超时，则关闭连接
                        if inactive_duration > HEARTBEAT_TIMEOUT:
                            client_info = connection_stats[session_id][ws_id]["remote"]
                            logger.warning(f"WebSocket连接超时 [会话ID: {session_id}] [客户端: {client_info}] [不活跃时长: {inactive_duration:.2f}秒]")
                            await unregister_websocket(ws, session_id)
                            inactive_count += 1
                        # 如果连接接近超时，发送心跳
                        elif inactive_duration > (HEARTBEAT_TIMEOUT / 2):
                            heartbeat_success = await send_heartbeat(ws, session_id)
                            if not heartbeat_success:
                                await unregister_websocket(ws, session_id)
                                inactive_count += 1
                
                if inactive_count > 0:
                    logger.info(f"已清理 {inactive_count} 个不活跃的WebSocket连接 [会话ID: {session_id}]")
            
            # 输出当前连接状态统计
            total_connections = sum(len(conns) for conns in active_connections.values())
            if total_connections > 0:
                logger.info(f"WebSocket连接状态检查完成 [活跃会话数: {len(active_connections)}] [总连接数: {total_connections}]")
                
        except Exception as e:
            logger.error(f"WebSocket连接状态检查失败: {str(e)}")
        
        # 等待下一次检查
        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def start_heartbeat_service():
    """
    启动心跳服务
    """
    logger.info("WebSocket心跳服务已启动")
    await check_connections()