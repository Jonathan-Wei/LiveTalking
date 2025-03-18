from aiohttp import web
import json
from websocket_manager import send_message
from logger import logger

async def websocket_send_handler(request):
    """
    处理WebSocket消息发送API请求
    
    Args:
        request: 请求对象
    
    Returns:
        web.Response: JSON响应
    """
    try:
        # 解析请求数据
        data = await request.json()
        
        # 获取必要参数
        session_id = data.get('session_id', 0)  # 默认使用0作为session_id
        message = data.get('message')
        dialogId = data.get('dialogId')
        message_type = data.get('message_type', 'ai_message')
        
        # 确保session_id是整数类型
        try:
            session_id = int(session_id)
        except (ValueError, TypeError):
            logger.warning(f"无效的session_id格式: {session_id}，将使用默认值0")
            session_id = 0
        
        # 参数验证
        if message is None:
            return web.Response(
                status=400,
                content_type='application/json',
                text=json.dumps({
                    "code": 1,
                    "message": "缺少必要参数: message"
                })
            )
        
        # 发送WebSocket消息
        await send_message(session_id, message, dialogId,message_type)
        
        # 返回成功响应
        return web.Response(
            content_type='application/json',
            text=json.dumps({
                "code": 0,
                "message": "消息发送成功"
            })
        )
        
    except Exception as e:
        logger.error(f"处理WebSocket消息发送API请求时出错: {str(e)}")
        return web.Response(
            status=500,
            content_type='application/json',
            text=json.dumps({
                "code": 2,
                "message": f"服务器内部错误: {str(e)}"
            })
        )