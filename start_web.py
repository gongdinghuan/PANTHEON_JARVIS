"""
简化版 Web UI 启动脚本
用于快速启动 Web UI 而不加载完整的 JARVIS 功能
"""

import uvicorn
from config import get_config

def main():
    config = get_config()
    print("启动 JARVIS Web UI...")
    print(f"访问地址: http://{config.server.host}:{config.server.port}")
    print("按 Ctrl+C 停止服务器")
    
    uvicorn.run(
        "server:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
