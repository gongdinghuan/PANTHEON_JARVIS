#!/bin/bash
# 自动执行运维命令脚本
# 在登录后的SSH会话中复制粘贴此脚本

echo "================================"
echo "  服务器运维检查开始"
echo "================================"
echo ""

# 1. 系统基础信息
echo "=== 1. 系统信息 ==="
uname -a
cat /etc/os-release | head -3
echo ""

# 2. 运行时间和负载
echo "=== 2. 运行时间和负载 ==="
uptime
echo ""

# 3. CPU使用率
echo "=== 3. CPU信息 ==="
lscpu | grep -E "^CPU\(s\)|Model name|Thread"
echo ""

# 4. 内存使用
echo "=== 4. 内存使用 ==="
free -h
echo ""

# 5. 磁盘使用
echo "=== 5. 磁盘使用 ==="
df -h
echo ""

# 6. 系统负载
echo "=== 6. 系统负载 Top 15 ==="
top -bn1 | head -15
echo ""

# 7. 网络连接
echo "=== 7. 网络端口监听 ==="
ss -tulnp | head -20
echo ""

# 8. 运行中的服务
echo "=== 8. 运行中的服务 ==="
systemctl list-units --type=service --state=running | head -20
echo ""

# 9. SSH服务状态
echo "=== 9. SSH服务状态 ==="
systemctl status sshd | head -10
echo ""

# 10. 在线用户
echo "=== 10. 在线用户 ==="
who -a
echo ""

# 11. 登录历史
echo "=== 11. 最近登录 ==="
last -n 10 | head -10
echo ""

# 12. 防火墙状态
echo "=== 12. 防火墙状态 ==="
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --state 2>/dev/null || echo "firewalld 未运行"
    firewall-cmd --list-all 2>/dev/null | head -15 || echo "无法获取规则"
elif command -v ufw &> /dev/null; then
    ufw status
else
    iptables -L -n | head -20 2>/dev/null || echo "无法获取防火墙规则"
fi
echo ""

# 13. 系统错误日志
echo "=== 13. 最近的系统错误 ==="
journalctl -p err -n 20 --no-pager 2>/dev/null || dmesg | tail -20
echo ""

# 14. 安全检查
echo "=== 14. 安全检查 ==="
echo "最近失败的登录:"
lastb | head -10 2>/dev/null || echo "无法获取失败登录记录"
echo ""

# 15. 系统资源总结
echo "=== 15. 系统资源总结 ==="
echo "内存使用率:"
free | grep Mem | awk '{printf "%.2f%%\n", ($3/$2) * 100.0}'
echo "磁盘使用率:"
df -h | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $1 " " $5 " " $6 }'
echo ""

echo "================================"
echo "  运维检查完成"
echo "================================"
