from aiohttp import web
import json
from websocket_manager import register_websocket, unregister_websocket
from logger import logger

async def websocket_handler(request):
    """
    处理WebSocket连接请求
    
    Args:
        request: 请求对象
    """
    # 记录连接请求信息
    remote_addr = request.remote
    headers = dict(request.headers)
    user_agent = headers.get('User-Agent', '未知')
    logger.info(f"收到WebSocket连接请求 [客户端: {remote_addr}] [UA: {user_agent[:50]}...]")
    
    # 获取会话ID
    try:
        session_id = int(request.rel_url.query.get('sessionid', 0))
        logger.info(f"WebSocket连接会话ID: {session_id}")
    except ValueError as e:
        logger.error(f"无效的会话ID参数: {request.rel_url.query.get('sessionid')} [错误: {str(e)}]")
        session_id = 0
    
    # 创建WebSocket响应
    try:
        ws = web.WebSocketResponse(heartbeat=5)  # 启用心跳，5秒间隔，确保在客户端8秒超时前响应
        await ws.prepare(request)
        logger.info(f"WebSocket握手成功 [客户端: {remote_addr}] [会话ID: {session_id}]")
    except Exception as e:
        logger.error(f"WebSocket握手失败 [客户端: {remote_addr}] [错误: {str(e)}]")
        return web.Response(status=400, text=f"WebSocket握手失败: {str(e)}")
    
    # 注册WebSocket连接
    await register_websocket(ws, session_id)
    
    try:
        # 发送连接成功消息
        await ws.send_json({
            "type": "connection_status",
            "status": "connected",
            "session_id": session_id
        })
        
        # 保持连接直到客户端关闭
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    # 尝试解析JSON消息
                    data = json.loads(msg.data)
                    msg_type = data.get('type', 'unknown')
                    logger.debug(f"收到WebSocket消息 [会话ID: {session_id}] [类型: {msg_type}]")
                    
                    # 处理心跳消息
                    if msg_type == 'heartbeat':
                        # 更新连接状态
                        ws_id = id(ws)
                        if session_id in connection_stats and ws_id in connection_stats[session_id]:
                            connection_stats[session_id][ws_id]["last_active_time"] = time.time()
                        
                        # 立即回复心跳响应
                        await ws.send_json({
                            "type": "heartbeat_response",
                            "timestamp": data.get('timestamp')
                        })
                        logger.debug(f"心跳响应已发送 [会话ID: {session_id}] [客户端: {ws._req.remote if hasattr(ws, '_req') else '未知'}]")
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的JSON消息 [会话ID: {session_id}] [内容: {msg.data[:50]}...]")
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket连接错误 [会话ID: {session_id}] [错误: {ws.exception()}]")
            elif msg.type == web.WSMsgType.CLOSE:
                logger.info(f"收到WebSocket关闭请求 [会话ID: {session_id}]")
    except Exception as e:
        logger.error(f"WebSocket处理异常 [会话ID: {session_id}] [错误: {str(e)}]")
    finally:
        # 连接关闭时注销WebSocket
        await unregister_websocket(ws, session_id)
    
    return ws