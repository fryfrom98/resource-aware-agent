"""Simple tool registry - map tool names to functions."""
from typing import Callable, Optional
from datetime import datetime

class ToolRegistry:
    """Register and retrieve tool functions by name."""
    
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        """Register fake/test tools for Phase 3 testing."""
        self.register("echo", self._tool_echo)
        self.register("add", self._tool_add)
        self.register("get_time", self._tool_get_time)
        self.register("fail_test", self._tool_fail_test)
    
    def register(self, name: str, func: Callable):
        """Register a new tool."""
        self._tools[name] = func
    
    def get(self, name: str) -> Optional[Callable]:
        """Get a tool function by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    @staticmethod
    def _tool_echo(message: str = "Hello"):
        """Echo back the message."""
        return f"Echo: {message}"
    
    @staticmethod
    def _tool_add(a: float, b: float):
        """Add two numbers."""
        return a + b
    
    @staticmethod
    def _tool_get_time():
        """Return current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    @staticmethod
    def _tool_fail_test():
        """Deliberately raise an error for testing error handling."""
        raise RuntimeError("This tool always fails (for testing)")
