#!/bin/bash
# 设置DASHSCOPE_API_KEY环境变量
export DASHSCOPE_API_KEY="sk-59054652ce1c4745a92db14dfee3e7dc"

# 启动Python应用程序
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1

# 如果程序异常退出，等待用户按键继续
read -p "按任意键继续..."