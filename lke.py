import time
import os
import json
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from basereal import BaseReal
from logger import logger
# 使用同步的WebSocket消息发送API
from websocket_api import send_message_sync

# 创建全局 Session 对象，用于复用 HTTP 连接
session = requests.Session()

# 配置重试策略
retries = Retry(
    total=3,  # 最大重试次数
    backoff_factor=0.5,  # 重试等待时间: 0.5s, 1s, 2s
    status_forcelist=[500, 502, 503, 504]  # 遇到这些状态码时重试
)

# 为 session 配置 HTTP 和 HTTPS 适配器
session.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=100))
session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=100))

def lke_response(opt, message, nerfreal: BaseReal):
    """
    通过Dify知识库API接口获取响应，并使用SSE方式处理流式响应
    
    Args:
        opt: 配置选项
        message: 用户输入的消息
        nerfreal: BaseReal对象，用于处理输出
    """
    start = time.perf_counter()
    
    sessionId = opt.sessionid
    # 记录sessionId信息，用于调试
    logger.info(f"lke_response - opt.sessionid: {opt.sessionid}, nerfreal.sessionid: {nerfreal.sessionid}")
    # 从opt中获取dialogId
    dialogId = opt.dialogId
    # Dify API的基础URL
    base_url = opt.LKE_SERVER
    if not base_url:
        logger.error("未设置LKE_SERVER环境变量")
        nerfreal.put_msg_txt("抱歉，系统未配置知识库服务器地址，无法回答您的问题。")
        return
    
    api_key = opt.LKE_API_KEY
    if not api_key:
        logger.error("未设置LKE_API_KEY环境变量")
        nerfreal.put_msg_txt("抱歉，系统未配置知识库API密钥，无法回答您的问题。")
        return
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 请求体
    data = {
        "inputs": {},
        "query": message,
        "response_mode": "streaming",
        "conversation_id": "",
        "user": f"user-{int(time.time())}"
    }
    
    end = time.perf_counter()
    logger.info(f"knowledge Time init: {end-start}s")
    
    try:
        # 使用 session 发送请求并获取流式响应
        response = session.post(base_url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        result = ""
        first = True
        
        # 处理SSE流式响应
        for line in response.iter_lines():
            if not line:
                continue
                
            # SSE格式的行以"data: "开头
            if line.startswith(b"data: "):
                json_str = line[6:].decode('utf-8')  # 去掉"data: "前缀
                
                try:
                    data = json.loads(json_str)
                    event = data.get("event")
                    
                    # 处理消息事件
                    if event == "message":
                        if first:
                            end = time.perf_counter()
                            logger.info(f"knowledge Time to first chunk: {end-start}s")
                            first = False
                            
                        msg = data.get("answer", "")
                        lastpos = 0
                        send_message_sync(sessionId, msg, dialogId,port=opt.listenport)
                        
                        # 按标点符号分段输出
                        for i, char in enumerate(msg):
                            if char in ",.!;:，。！？：；":
                                result = result + msg[lastpos:i+1]
                                lastpos = i+1
                                if len(result) > 10:
                                    nerfreal.put_msg_txt(result)
                                    # 通过WebSocket API推送消息到前端
                                    # 使用同步函数发送消息，避免跨线程调用异步函数
                                    # 使用固定的session_id为0，确保与前端WebSocket连接一致
                                    # send_message_sync(0, result, dialogId,port=opt.listenport)
                                    result = ""
                        
                        result = result + msg[lastpos:]
                    
                    # 处理消息结束事件
                    elif event == "message_end":
                        # 处理最后剩余的文本
                        if result:
                            nerfreal.put_msg_txt(result)
                            # 通过WebSocket API推送最后的消息
                            # 使用同步函数发送消息，避免跨线程调用异步函数
                            # 使用固定的session_id为0，确保与前端WebSocket连接一致
                            # send_message_sync(0, result, dialogId, port=opt.listenport)
                            result = ""
                        
                        # 记录使用情况
                        if "metadata" in data and "usage" in data["metadata"]:
                            usage = data["metadata"]["usage"]
                            logger.info(f"知识库API使用情况: {usage}")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
        
        end = time.perf_counter()
        logger.info(f"knowledge Time to last chunk: {end-start}s")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"请求错误: {e}")
        nerfreal.put_msg_txt(f"抱歉，连接知识库时出现错误: {str(e)}")
    
    # 确保最后的文本也被发送
    if result:
        nerfreal.put_msg_txt(result)
        # 通过WebSocket API推送最后的消息
        # 使用同步函数发送消息，避免跨线程调用异步函数
        # 使用固定的session_id为0，确保与前端WebSocket连接一致
        # send_message_sync(0, result, dialogId,port=opt.listenport)

# 注意：不要在这里调用 session.close()，保持连接池开放以供后续请求使用
# 如果应用程序退出前需要清理资源，可以在适当的地方调用 session.close()