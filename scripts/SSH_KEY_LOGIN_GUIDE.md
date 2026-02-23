# 🔑 SSH密钥登录服务器指南

## 📋 快速配置步骤

### 第一步：配置服务器

**使用密码登录服务器，然后执行以下命令：**

```bash
# 1. 创建SSH目录（如果不存在）
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 2. 从Windows复制公钥到服务器
# 方法A：手动复制（推荐）
# 在Windows上显示公钥内容：
ssh-keygen -y -f C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa

# 将显示的公钥复制，然后在服务器上执行：
echo "ssh-rsa AAAA...（公钥内容）" >> ~/.ssh/authorized_keys

# 方法B：使用ssh-copy-id（如果已安装）
ssh-copy-id -i C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa.pub -p 222 root@47.97.113.144

# 3. 设置正确的权限
chmod 600 ~/.ssh/authorized_keys

# 4. 重启SSH服务
systemctl restart sshd

# 5. 确保SSH配置允许密钥认证
grep -E "^PubkeyAuthentication|^PasswordAuthentication" /etc/ssh/sshd_config
# 应该显示：
# PubkeyAuthentication yes
# PasswordAuthentication yes（可选，保留密码作为备用）
```

### 第二步：测试密钥登录

**在Windows PowerShell中执行：**

```powershell
ssh -i C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa -p 222 root@47.97.113.144
```

### 第三步：执行运维

**方法1：交互式登录**
```cmd
C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\ssh_key_login_47.bat
```

**方法2：自动化执行**
```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\ssh_key_ops_47.ps1
```

---

## 🛠️ 可用工具

| 工具 | 功能 | 命令 |
|:-----|:-----|:-----|
| **ssh_key_login_47.bat** | 交互式登录 | 双击运行 |
| **ssh_key_ops_47.ps1** | 自动化运维 | PowerShell运行 |
| **ssh_key_manager.py** | 密钥管理 | Python运行 |

---

## ❓ 常见问题

### Q: 密钥认证失败
```
A: 检查以下项：
1. 服务器上~/.ssh/authorized_keys文件权限是否为600
2. 公钥是否正确添加
3. SSH配置是否开启PubkeyAuthentication
```

### Q: 权限错误
```
A: 执行：
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### Q: 仍需输入密码
```
A: 检查SSH配置：
vi /etc/ssh/sshd_config
确保：
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
```

---

**Stark先生，配置完成后即可使用密钥登录！** 🚀
