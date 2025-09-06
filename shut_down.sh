#!/bin/bash
# 文件名：kill_simulation.sh

echo "正在查找并杀死相关进程..."

# 杀死 python3 run.py 进程
echo "杀死 python3 run.py 进程..."
pkill -f "python3 run.py" || pkill -f "python run.py"

# 杀死 waf 相关进程
echo "杀死 waf 进程..."
pkill -f "waf"

# 杀死 network-load-balance 进程
echo "杀死 network-load-balance 进程..."
pkill -f "network-load-balance"

# 杀死 ns-3 相关进程
echo "杀死 ns-3 相关进程..."
pkill -f "ns3"

# 等待进程完全结束
sleep 2

# 强制杀死仍然存在的进程
echo "强制杀死残留进程..."
pkill -9 -f "python3 run.py" 2>/dev/null
pkill -9 -f "waf" 2>/dev/null
pkill -9 -f "network-load-balance" 2>/dev/null
pkill -9 -f "ns3" 2>/dev/null

echo "清理完成！"