"""
JARVIS 依赖注入容器
简单的 DI 容器，管理模块生命周期

Author: gngdingghuan
"""

import asyncio
from typing import Dict, Any, Optional, Type, Callable, TypeVar
from utils.logger import log

T = TypeVar('T')


class Container:
    """
    简单的依赖注入容器
    
    用法:
        container = Container()
        container.register("brain", LLMBrain, provider=LLMProvider.DEEPSEEK)
        container.register("memory", MemoryManager)
        
        brain = container.get("brain")
        memory = container.get("memory")
        
        await container.initialize_all()
        await container.shutdown_all()
    """
    
    def __init__(self):
        self._factories: Dict[str, tuple] = {}   # name -> (factory, args, kwargs)
        self._instances: Dict[str, Any] = {}      # name -> instance
        self._init_order: list = []               # 初始化顺序
        self._shutdown_order: list = []           # 关闭顺序 (反序)
    
    def register(
        self,
        name: str,
        factory: Callable,
        *args,
        singleton: bool = True,
        init_priority: int = 50,
        **kwargs,
    ):
        """
        注册一个组件
        
        Args:
            name: 组件名称
            factory: 工厂函数或类
            *args: 构造参数
            singleton: 是否单例
            init_priority: 初始化优先级 (0=最先, 100=最后)
            **kwargs: 构造参数
        """
        self._factories[name] = (factory, args, kwargs, singleton, init_priority)
        log.debug(f"容器注册: {name} (优先级: {init_priority})")
    
    def register_instance(self, name: str, instance: Any):
        """
        直接注册一个已创建的实例
        
        Args:
            name: 组件名称
            instance: 组件实例
        """
        self._instances[name] = instance
        log.debug(f"容器注册实例: {name} ({type(instance).__name__})")
    
    def get(self, name: str) -> Any:
        """
        获取组件实例
        
        Args:
            name: 组件名称
            
        Returns:
            组件实例
            
        Raises:
            KeyError: 组件未注册
        """
        # 已有实例
        if name in self._instances:
            return self._instances[name]
        
        # 创建实例
        if name in self._factories:
            factory, args, kwargs, singleton, _ = self._factories[name]
            instance = factory(*args, **kwargs)
            
            if singleton:
                self._instances[name] = instance
            
            return instance
        
        raise KeyError(f"组件未注册: {name}")
    
    def has(self, name: str) -> bool:
        """检查组件是否已注册"""
        return name in self._instances or name in self._factories
    
    async def initialize_all(self):
        """
        按优先级初始化所有组件
        """
        # 按优先级排序
        sorted_factories = sorted(
            self._factories.items(),
            key=lambda x: x[1][4]  # init_priority
        )
        
        for name, (factory, args, kwargs, singleton, priority) in sorted_factories:
            if name in self._instances:
                continue
            
            try:
                instance = factory(*args, **kwargs)
                
                if singleton:
                    self._instances[name] = instance
                
                # 如果有 async initialize 方法，调用它
                if hasattr(instance, 'initialize') and asyncio.iscoroutinefunction(instance.initialize):
                    await instance.initialize()
                
                self._init_order.append(name)
                log.debug(f"容器初始化: {name}")
            
            except Exception as e:
                log.error(f"容器初始化 {name} 失败: {e}")
                raise
        
        log.info(f"容器初始化完成: {len(self._instances)} 个组件")
    
    async def shutdown_all(self):
        """
        按反序关闭所有组件
        """
        for name in reversed(self._init_order):
            instance = self._instances.get(name)
            if instance is None:
                continue
            
            try:
                # 优先调用 close()，其次 shutdown()，最后 stop()
                if hasattr(instance, 'close') and asyncio.iscoroutinefunction(instance.close):
                    await instance.close()
                elif hasattr(instance, 'shutdown') and asyncio.iscoroutinefunction(instance.shutdown):
                    await instance.shutdown()
                elif hasattr(instance, 'stop') and asyncio.iscoroutinefunction(instance.stop):
                    await instance.stop()
                
                log.debug(f"容器关闭: {name}")
            except Exception as e:
                log.warning(f"容器关闭 {name} 失败: {e}")
        
        self._instances.clear()
        self._init_order.clear()
        log.info("容器已全部关闭")
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有实例"""
        return dict(self._instances)
    
    @property
    def component_count(self) -> int:
        """已注册的组件数量"""
        return len(self._instances)


# 全局容器单例
_global_container: Optional[Container] = None


def get_container() -> Container:
    """获取全局容器"""
    global _global_container
    if _global_container is None:
        _global_container = Container()
    return _global_container
