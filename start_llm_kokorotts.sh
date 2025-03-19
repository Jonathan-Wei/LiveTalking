#!/bin/bash

# 设置DASHSCOPE_API_KEY环境变量
export DASHSCOPE_API_KEY=""

# 启动Python应用程序
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1 --tts kokoro-tts --TTS_SERVER http://127.0.0.1:8880 --max_session 20

# 如果程序异常退出，等待用户按键
echo "按任意键继续..."
read -n 1