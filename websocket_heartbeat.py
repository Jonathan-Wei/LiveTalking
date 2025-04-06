import asyncio
import time
from logger import logger
from websocket_manager import active_connections, connection_stats, unregister_websocket

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 15
# 心跳检查间隔（秒）
HEARTBEAT_INTERVAL = 3

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
        # 添加更多信息到心跳消息中，便于调试
        await ws.send_json({
            "type": "heartbeat", 
            "timestamp": time.time(),
            "server_info": {
                "heartbeat_timeout": HEARTBEAT_TIMEOUT,
                "heartbeat_interval": HEARTBEAT_INTERVAL
            }
        })
        
        # 获取客户端信息用于日志
        ws_id = id(ws)
        client_info = "未知客户端"
        if session_id in connection_stats and ws_id in connection_stats[session_id]:
            client_info = connection_stats[session_id][ws_id]["remote"]
            # 更新最后活跃时间
            connection_stats[session_id][ws_id]["last_active_time"] = time.time()
            
        logger.debug(f"心跳消息已发送 [会话ID: {session_id}] [客户端: {client_info}]")
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
            logger.debug(f"开始检查WebSocket连接状态 [会话数: {len(sessions_to_check)}]")
            
            for session_id in sessions_to_check:
                if session_id not in active_connections:
                    continue
                    
                # 获取连接集合的副本
                connections = active_connections[session_id].copy()
                inactive_count = 0
                active_count = 0
                warning_count = 0
                
                for ws in connections:
                    ws_id = id(ws)
                    if session_id in connection_stats and ws_id in connection_stats[session_id]:
                        last_active_time = connection_stats[session_id][ws_id]["last_active_time"]
                        inactive_duration = current_time - last_active_time
                        client_info = connection_stats[session_id][ws_id]["remote"]
                        
                        # 记录连接状态日志
                        if inactive_duration < (HEARTBEAT_TIMEOUT / 3):
                            # 连接状态良好
                            active_count += 1
                            logger.debug(f"WebSocket连接状态良好 [会话ID: {session_id}] [客户端: {client_info}] [不活跃时长: {inactive_duration:.2f}秒]")
                        
                        # 如果连接超时，则关闭连接
                        elif inactive_duration > HEARTBEAT_TIMEOUT:
                            logger.warning(f"WebSocket连接超时 [会话ID: {session_id}] [客户端: {client_info}] [不活跃时长: {inactive_duration:.2f}秒]")
                            try:
                                await unregister_websocket(ws, session_id)
                                inactive_count += 1
                            except Exception as e:
                                logger.error(f"注销超时WebSocket连接失败 [会话ID: {session_id}] [客户端: {client_info}] [错误: {str(e)}]")
                        
                        # 如果连接接近超时，发送心跳
                        elif inactive_duration > (HEARTBEAT_TIMEOUT / 2):
                            logger.info(f"WebSocket连接接近超时，发送心跳 [会话ID: {session_id}] [客户端: {client_info}] [不活跃时长: {inactive_duration:.2f}秒]")
                            warning_count += 1
                            heartbeat_success = await send_heartbeat(ws, session_id)
                            if not heartbeat_success:
                                logger.warning(f"心跳发送失败，注销连接 [会话ID: {session_id}] [客户端: {client_info}]")
                                try:
                                    await unregister_websocket(ws, session_id)
                                    inactive_count += 1
                                except Exception as e:
                                    logger.error(f"注销WebSocket连接失败 [会话ID: {session_id}] [客户端: {client_info}] [错误: {str(e)}]")
                
                if inactive_count > 0:
                    logger.info(f"已清理 {inactive_count} 个不活跃的WebSocket连接 [会话ID: {session_id}]")
                
                logger.debug(f"会话连接状态 [会话ID: {session_id}] [良好: {active_count}] [警告: {warning_count}] [已清理: {inactive_count}]")
            
            # 输出当前连接状态统计
            total_connections = sum(len(conns) for conns in active_connections.values())
            if total_connections > 0:
                logger.info(f"WebSocket连接状态检查完成 [活跃会话数: {len(active_connections)}] [总连接数: {total_connections}]")
                
        except Exception as e:
            logger.error(f"WebSocket连接状态检查失败: {str(e)}")
            # 记录详细的异常信息以便调试
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
        
        # 等待下一次检查
        await asyncio.sleep(HEARTBEAT_INTERVAL)

async def start_heartbeat_service():
    """
    启动心跳服务
    """
    logger.info("WebSocket心跳服务已启动")
    await check_connections()