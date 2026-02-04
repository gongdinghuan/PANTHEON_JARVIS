"""
JARVIS Web UI 服务器
FastAPI + WebSocket 实现 J.A.R.V.I.S. 风格的 Web 界面

Author: gngdingghuan
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import get_config
from utils.logger import log

# 创建 FastAPI 应用
app = FastAPI(title="JARVIS AI Assistant", version="1.0.0")

# 获取配置
config = get_config()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 全局 JARVIS 实例（将在 main.py 中设置）
jarvis_instance = None


def set_jarvis_instance(instance):
    """设置 JARVIS 实例"""
    global jarvis_instance
    jarvis_instance = instance
    log.info("JARVIS 实例已设置到服务器")


@app.get("/")
async def get_root():
    """返回主页面"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse("<h1>JARVIS Web UI</h1><p>请先运行 python build_ui.py 生成界面文件</p>")


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        heartbeat_stats = jarvis_instance.heartbeat.get_session_stats()
        memory_stats = jarvis_instance.memory.get_stats()
        evolution_stats = jarvis_instance.evolution_engine.get_evolution_stats()
        system_info = jarvis_instance.system_info.get_all_info()
        heartbeat_info = jarvis_instance.heartbeat.get_init_time_info()
        context = jarvis_instance.context.get_system_state()
        
        return {
            "status": "running",
            "system": {
                "os": system_info.get("os"),
                "platform": system_info.get("platform"),
                "arch": system_info.get("arch"),
                "hostname": system_info.get("hostname"),
                "user": system_info.get("user"),
                "is_admin": system_info.get("is_admin"),
                "python": system_info.get("python"),
            },
            "time": {
                "start_time": heartbeat_info.get("init_time_formatted"),
                "start_period": heartbeat_info.get("init_time_info", {}).get("period_cn"),
                "timezone": jarvis_instance.config.heartbeat.timezone,
                "current_time": heartbeat_stats.get("current_time"),
            },
            "heartbeat": {
                "running": jarvis_instance.heartbeat.is_running(),
                "uptime": heartbeat_stats.get("uptime"),
                "total_requests": heartbeat_stats.get("total_requests"),
                "total_heartbeats": heartbeat_stats.get("total_heartbeats"),
            },
            "memory": {
                "short_term_turns": memory_stats.get("short_term_turns"),
                "long_term_memories": memory_stats.get("long_term_count"),
            },
            "evolution": {
                "total_interactions": evolution_stats.get("total_interactions"),
                "learned_patterns": evolution_stats.get("learned_patterns"),
            },
            "resources": {
                "cpu_percent": context.get("cpu_percent"),
                "memory_percent": context.get("memory_percent"),
                "active_window": context.get("active_window"),
            },
        }
    except Exception as e:
        log.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/heartbeat")
async def get_heartbeat():
    """获取心跳状态"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        status = jarvis_instance.heartbeat.get_heartbeat_status()
        return {
            "status_text": status,
            "running": jarvis_instance.heartbeat.is_running(),
            "current_time": jarvis_instance.heartbeat.get_current_time(),
            "uptime": jarvis_instance.heartbeat.get_uptime(),
            "greeting": jarvis_instance.heartbeat.get_greeting(),
        }
    except Exception as e:
        log.error(f"获取心跳状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills")
async def get_skills():
    """获取技能列表"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        skills = []
        for name, skill in jarvis_instance.skills.items():
            skills.append({
                "name": name,
                "description": skill.description,
                "permission_level": str(skill.permission_level),
            })
        return {"skills": skills}
    except Exception as e:
        log.error(f"获取技能列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_tasks():
    """获取任务列表"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        task_manager = jarvis_instance.planner.get_task_manager()
        tasks = task_manager.get_all_tasks()
        return {"tasks": tasks}
    except Exception as e:
        log.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: Dict[str, Any]):
    """发送聊天消息"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        message = request.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")
        
        # 处理消息
        response = await jarvis_instance.process(message)
        
        return {
            "message": message,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        log.error(f"处理聊天消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confirm/{request_id}")
async def confirm_request(request_id: str, action: str):
    """处理确认请求响应"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        confirmation_handler = jarvis_instance.confirmation_handler
        
        if action == "confirm":
            success = confirmation_handler.confirm(request_id)
        elif action == "reject":
            success = confirmation_handler.reject(request_id)
        else:
            raise HTTPException(status_code=400, detail="无效的确认操作")
        
        if success:
            return {
                "success": True,
                "request_id": request_id,
                "action": action,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "请求不存在或已过期",
                "request_id": request_id,
            }
    except Exception as e:
        log.error(f"处理确认响应失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending-confirmations")
async def get_pending_confirmations():
    """获取待处理的确认请求列表"""
    if not jarvis_instance:
        return {"error": "JARVIS 未初始化"}
    
    try:
        confirmation_handler = jarvis_instance.confirmation_handler
        pending = confirmation_handler.get_pending_requests()
        
        return {
            "pending_requests": pending,
            "count": len(pending),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        log.error(f"获取待处理确认列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def mask_key(key: str) -> str:
    """脱敏 API Key"""
    if not key or len(key) < 8:
        return ""
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@app.get("/api/config/llm")
async def get_llm_config():
    """获取当前 LLM 配置（脱敏）"""
    from config import get_config
    config = get_config().llm
    
    return {
        "provider": config.provider.value,
        "openai_api_key": mask_key(config.openai_api_key),
        "openai_base_url": config.openai_base_url,
        "openai_model": config.openai_model,
        "deepseek_api_key": mask_key(config.deepseek_api_key),
        "deepseek_base_url": config.deepseek_base_url,
        "deepseek_model": config.deepseek_model,
        "ollama_base_url": config.ollama_base_url,
        "ollama_model": config.ollama_model,
        "nvidia_api_key": mask_key(config.nvidia_api_key),
        "nvidia_base_url": config.nvidia_base_url,
        "nvidia_model": config.nvidia_model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }


@app.post("/api/config/llm")
async def update_llm_config(config_data: Dict[str, Any]):
    """更新 LLM 配置"""
    if not jarvis_instance:
        raise HTTPException(status_code=500, detail="JARVIS 未初始化")
    
    try:
        from config import update_env_file, get_config, LLMProvider
        
        provider = config_data.get("provider", "deepseek")
        
        # 准备环境变量更新
        env_updates = {
            f"{provider.upper()}_API_KEY": config_data.get(f"{provider}_api_key", ""),
            f"{provider.upper()}_BASE_URL": config_data.get(f"{provider}_base_url", ""),
            f"{provider.upper()}_MODEL": config_data.get(f"{provider}_model", ""),
        }
        
        # 更新 .env 文件
        if not update_env_file(env_updates):
            raise HTTPException(status_code=500, detail="更新 .env 文件失败")
        
        # 更新配置对象
        jarvis_config = get_config()
        jarvis_config.llm.provider = LLMProvider[provider.upper()]
        
        if provider == "openai":
            jarvis_config.llm.openai_api_key = config_data.get("openai_api_key", "")
            jarvis_config.llm.openai_base_url = config_data.get("openai_base_url", "")
            jarvis_config.llm.openai_model = config_data.get("openai_model", "")
        elif provider == "deepseek":
            jarvis_config.llm.deepseek_api_key = config_data.get("deepseek_api_key", "")
            jarvis_config.llm.deepseek_base_url = config_data.get("deepseek_base_url", "")
            jarvis_config.llm.deepseek_model = config_data.get("deepseek_model", "")
        elif provider == "ollama":
            jarvis_config.llm.ollama_base_url = config_data.get("ollama_base_url", "")
            jarvis_config.llm.ollama_model = config_data.get("ollama_model", "")
        elif provider == "nvidia":
            jarvis_config.llm.nvidia_api_key = config_data.get("nvidia_api_key", "")
            jarvis_config.llm.nvidia_base_url = config_data.get("nvidia_base_url", "")
            jarvis_config.llm.nvidia_model = config_data.get("nvidia_model", "")
        
        # 更新通用参数
        jarvis_config.llm.temperature = config_data.get("temperature", 0.7)
        jarvis_config.llm.max_tokens = config_data.get("max_tokens", 8096)
        
        # 重新初始化 LLM Brain
        await jarvis_instance.brain.reinitialize()
        
        log.info(f"LLM 配置已更新: {provider}")
        
        return {"success": True, "message": "配置已更新，LLM 已重新初始化"}
    except Exception as e:
        log.error(f"更新 LLM 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/llm/test")
async def test_llm_connection(test_config: Dict[str, Any]):
    """测试 LLM 连接"""
    try:
        from openai import AsyncOpenAI
        import httpx
        
        provider = test_config.get("provider", "deepseek")
        api_key = test_config.get(f"{provider}_api_key", "")
        base_url = test_config.get(f"{provider}_base_url", "")
        model = test_config.get(f"{provider}_model", "")
        
        if not api_key and provider != "ollama":
            return {"success": False, "error": "API Key 不能为空"}
        
        # 创建测试客户端
        client = AsyncOpenAI(
            api_key=api_key if provider != "ollama" else "ollama",
            base_url=base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
        
        # 发送测试请求
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )
        
        await client.close()
        
        return {
            "success": True,
            "message": "连接成功",
            "model": model,
            "response": response.choices[0].message.content if response.choices else None,
        }
    except Exception as e:
        log.error(f"测试 LLM 连接失败: {e}")
        return {"success": False, "error": str(e)}


@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭时的清理"""
    global jarvis_instance
    if jarvis_instance:
        try:
            # 停止持续进化
            if hasattr(jarvis_instance, 'continuous_evolution'):
                await jarvis_instance.continuous_evolution.stop()
            
            # 停止心跳
            if hasattr(jarvis_instance, 'heartbeat'):
                await jarvis_instance.heartbeat.stop()
            
            # 关闭任务管理器
            if hasattr(jarvis_instance, 'planner'):
                task_manager = jarvis_instance.planner.get_task_manager()
                await task_manager.shutdown(wait=True)
            
            # 关闭 LLM Brain
            if hasattr(jarvis_instance, 'brain'):
                await jarvis_instance.brain.close()
            
            log.info("JARVIS 已优雅关闭")
        except Exception as e:
            log.warning(f"关闭时出错: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点 - 实时通信"""
    await websocket.accept()
    log.info("WebSocket 连接已建立")
    
    # 将 WebSocket 连接设置到 ConfirmationHandler
    if jarvis_instance:
        jarvis_instance.confirmation_handler.set_websocket(websocket)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "system",
            "message": "已连接到 JARVIS",
            "timestamp": datetime.now().isoformat(),
        })
        
        # 接收消息循环
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                # 处理聊天消息
                message = data.get("message", "")
                if message and jarvis_instance:
                    try:
                        response = await jarvis_instance.process(message)
                        await websocket.send_json({
                            "type": "chat",
                            "message": message,
                            "response": response,
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        })
            
            elif data.get("type") == "heartbeat":
                # 发送心跳状态
                if jarvis_instance:
                    try:
                        heartbeat_status = jarvis_instance.heartbeat.get_heartbeat_status()
                        await websocket.send_json({
                            "type": "heartbeat",
                            "status": heartbeat_status,
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        })
            
            elif data.get("type") == "status":
                # 发送系统状态
                if jarvis_instance:
                    try:
                        status = await get_status()
                        await websocket.send_json({
                            "type": "status",
                            "status": status,
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        })
            
            elif data.get("type") == "confirm_response":
                # 处理确认响应
                if jarvis_instance:
                    try:
                        request_id = data.get("request_id")
                        action = data.get("action")  # "confirm" or "reject"
                        
                        if request_id and action:
                            confirmation_handler = jarvis_instance.confirmation_handler
                            
                            if action == "confirm":
                                success = confirmation_handler.confirm(request_id)
                            elif action == "reject":
                                success = confirmation_handler.reject(request_id)
                            else:
                                success = False
                            
                            if success:
                                await websocket.send_json({
                                    "type": "system",
                                    "message": f"已{('确认' if action == 'confirm' else '拒绝')}操作",
                                    "request_id": request_id,
                                    "timestamp": datetime.now().isoformat(),
                                })
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "请求不存在或已过期",
                                    "request_id": request_id,
                                    "timestamp": datetime.now().isoformat(),
                                })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat(),
                        })
    
    except WebSocketDisconnect:
        log.info("WebSocket 连接已断开")
    except Exception as e:
        log.error(f"WebSocket 错误: {e}")
        try:
            await websocket.close()
        except:
            pass


def run_server():
    """运行服务器"""
    import uvicorn
    
    log.info(f"启动 JARVIS Web UI 服务器: http://{config.server.host}:{config.server.port}")
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
