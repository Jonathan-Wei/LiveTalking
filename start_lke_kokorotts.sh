#!/bin/bash

# 启动Python应用程序
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts kokoro-tts --tts kokoro-tts --TTS_SERVER http://127.0.0.1:8880 --chat_engine lke --LKE_SERVER https://127.0.0.1/v1/chat-messages --LKE_API_KEY app-WKpRtHLFlRexxqirWL8B2K9P --max_session 20

# 如果程序异常退出，等待用户按键继续
read -p "按任意键继续..."