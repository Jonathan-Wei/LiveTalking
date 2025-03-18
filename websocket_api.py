import requests
import json
from logger import logger

def send_message_sync(session_id, message,dialogId, message_type="ai_message",server_url="http://localhost", port=8080):
    """
    通过HTTP请求向WebSocket服务器发送消息，用于替代异步的send_message函数
    
    Args:
        session_id: 会话ID
        message: 要发送的消息内容
        message_type: 消息类型，默认为ai_message
        server_url: 服务器URL，默认为http://localhost
        port: 服务器端口，默认为8080
    
    Returns:
        bool: 消息是否成功发送
    """
    try:
        # 确保session_id是整数类型
        try:
            session_id = int(session_id)
        except (ValueError, TypeError):
            logger.warning(f"无效的session_id格式: {session_id}，将使用默认值0")
            session_id = 0
        
        # 记录详细的会话ID信息，便于调试
        logger.info(f"准备发送消息到会话ID: {session_id} [类型: {message_type}]")
        
        # 构建请求URL
        url = f"{server_url}:{port}/api/websocket/send"
        
        # 构建请求数据
        data = {
            "session_id": session_id,
            "message": message,
            "message_type": message_type,
            "dialogId": dialogId
        }
        
        # 发送HTTP POST请求
        response = requests.post(url, json=data, timeout=3)
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"消息发送成功 [会话ID: {session_id}] [类型: {message_type}]")
                return True
            else:
                logger.warning(f"消息发送失败 [会话ID: {session_id}] [错误: {result.get('message', '未知错误')}]")
        else:
            logger.warning(f"消息发送请求失败 [会话ID: {session_id}] [状态码: {response.status_code}]")
        
        return False
    except Exception as e:
        logger.error(f"发送消息时发生异常 [会话ID: {session_id}] [错误: {str(e)}]")
        return False