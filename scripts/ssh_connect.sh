#!/bin/bash
# SSH 自动密码连接脚本
# 用于连接 47.97.113.144:222

SERVER="47.97.113.144"
PORT="222"
USER="root"
PASSWORD="zXc363324112"

echo "========================================"
echo "  SSH Connection to $SERVER"
echo "========================================"
echo ""
echo "Server: $SERVER:$PORT"
echo "User: $USER"
echo "Password: ********"
echo ""

# 检查sshpass（Linux/Mac）
if command -v sshpass &> /dev/null; then
    echo "Using sshpass with auto-password..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -p "$PORT" "$USER@$SERVER"
else
    echo "sshpass not found, trying manual password..."
    ssh -o StrictHostKeyChecking=no -p "$PORT" "$USER@$SERVER" << EOF
$PASSWORD
EOF
fi
