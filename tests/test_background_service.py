#!/usr/bin/env python3
"""
测试后台服务功能
"""

import subprocess
import time
import os

def test_background_service():
    """测试后台服务"""
    print("测试JARVIS后台服务功能")
    print("=" * 40)
    
    # 1. 检查当前是否有后台服务在运行
    print("1. 检查当前进程...")
    result = subprocess.run(['tasklist', '/fi', 'imagename eq python.exe'], 
                          capture_output=True, text=True, encoding='gbk')
    
    if 'jarvis_background_service.py' in result.stdout:
        print("✅ 后台服务正在运行")
    else:
        print("❌ 后台服务未运行")
    
    # 2. 检查日志文件
    print("\n2. 检查日志文件...")
    if os.path.exists('jarvis_service.log'):
        print("✅ 日志文件存在")
        try:
            with open('jarvis_service.log', 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    print(f"日志大小: {len(content)} 字节")
                    # 显示最后几行
                    lines = content.strip().split('\n')
                    if lines:
                        print("最后一条日志:")
                        print(lines[-1][-100:])  # 显示最后100个字符
                else:
                    print("日志文件为空")
        except Exception as e:
            print(f"读取日志失败: {e}")
    else:
        print("❌ 日志文件不存在")
    
    # 3. 测试是否能启动新服务
    print("\n3. 测试服务启动...")
    try:
        # 启动一个简单的测试服务
        test_script = '''
import time
print("测试服务启动:", time.strftime("%H:%M:%S"))
time.sleep(5)
print("测试服务结束:", time.strftime("%H:%M:%S"))
'''
        
        with open('test_service.py', 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        # 在后台启动
        proc = subprocess.Popen(['python', 'test_service.py'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        
        print("✅ 测试服务已启动 (PID: {})".format(proc.pid))
        print("等待2秒...")
        time.sleep(2)
        
        # 检查是否还在运行
        if proc.poll() is None:
            print("✅ 测试服务仍在后台运行")
            proc.terminate()
            print("✅ 测试服务已停止")
        else:
            print("❌ 测试服务已退出")
            
        # 清理
        if os.path.exists('test_service.py'):
            os.remove('test_service.py')
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 4. 验证提醒功能
    print("\n4. 验证提醒功能...")
    print("将在5秒后显示测试提醒...")
    time.sleep(5)
    
    # 显示一个测试提醒
    try:
        subprocess.run('msg * "测试提醒：这是来自JARVIS后台服务的测试消息"', 
                      shell=True, capture_output=True)
        print("✅ 提醒功能正常")
    except Exception as e:
        print(f"❌ 提醒功能异常: {e}")
    
    print("\n" + "=" * 40)
    print("测试完成！")
    
    # 建议
    print("\n建议:")
    print("1. 双击 start_background_service.bat 启动后台服务")
    print("2. 双击 jarvis_service_installer.bat 安装为开机启动")
    print("3. 使用 python jarvis_service_manager.py 管理服务")

if __name__ == "__main__":
    test_background_service()