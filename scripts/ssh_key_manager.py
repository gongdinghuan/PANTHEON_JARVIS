#!/usr/bin/env python3
"""
SSH密钥管理工具
- 生成密钥对
- 导出公钥
- 配置服务器
"""
import subprocess
import sys
import os

def generate_keypair():
    """生成SSH密钥对"""
    key_path = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa"
    
    print("🔑 正在生成SSH密钥对...")
    
    # 使用ssh-keygen生成密钥
    cmd = [
        "ssh-keygen",
        "-t", "rsa",
        "-b", "4096",
        "-f", key_path,
        "-N", "",  # 无密码
        "-C", "jarvis@pantheon"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ 密钥对已生成:")
        print(f"   私钥: {key_path}")
        print(f"   公钥: {key_path}.pub")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 生成密钥失败: {e.stderr}")
        return False

def export_public_key():
    """从私钥导出公钥"""
    key_path = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa"
    
    print("\n📤 正在从私钥导出公钥...")
    
    cmd = ["ssh-keygen", "-y", "-f", key_path]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        public_key = result.stdout.strip()
        
        # 保存公钥
        pub_key_path = f"{key_path}.pub"
        with open(pub_key_path, "w") as f:
            f.write(public_key)
        
        print(f"✅ 公钥已导出: {pub_key_path}")
        print(f"\n公钥内容:")
        print("=" * 60)
        print(public_key)
        print("=" * 60)
        
        return public_key
    except subprocess.CalledProcessError as e:
        print(f"❌ 导出公钥失败: {e.stderr}")
        return None

def setup_server_instructions(public_key):
    """显示服务器配置说明"""
    print("\n" + "=" * 60)
    print("📋 服务器配置步骤")
    print("=" * 60)
    print("\n1️⃣  先使用密码登录服务器:")
    print("   ssh -p 222 root@47.97.113.144")
    print("\n2️⃣  在服务器上执行以下命令:")
    print(f"   mkdir -p ~/.ssh")
    print(f"   chmod 700 ~/.ssh")
    print(f"   echo '{public_key}' >> ~/.ssh/authorized_keys")
    print(f"   chmod 600 ~/.ssh/authorized_keys")
    print(f"   systemctl restart sshd")
    print("\n3️⃣  测试密钥登录:")
    print("   ssh -i C:\\Users\\Administrator\\Desktop\\workspace\\PANTHEON_JARVIS\\scripts\\id_rsa -p 222 root@47.97.113.144")
    print("\n" + "=" * 60)

def main():
    print("=" * 60)
    print("🔐 SSH密钥管理工具")
    print("=" * 60)
    
    # 检查是否已有私钥
    key_path = r"C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa"
    
    if os.path.exists(key_path):
        print(f"\n✅ 检测到现有私钥: {key_path}")
        choice = input("是否使用现有密钥？(Y/n): ").strip().lower()
        
        if choice != 'n':
            public_key = export_public_key()
            if public_key:
                setup_server_instructions(public_key)
            return
    
    # 生成新密钥
    if generate_keypair():
        public_key = export_public_key()
        if public_key:
            setup_server_instructions(public_key)

if __name__ == "__main__":
    main()
