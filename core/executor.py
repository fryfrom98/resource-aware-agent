"""Task executor - reads task, invokes tool, returns result."""
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.registry import ToolRegistry

class Executor:
    """Executes tasks by looking up tools in registry."""
    
    def __init__(self, registry: ToolRegistry = None):
        self.registry = registry or ToolRegistry()
    
    def execute_task(self, task):
        """Execute a task and return result dict. Does NOT update task status."""
        if not task.tool:
            return {
                "success": False,
                "error": "No tool specified for task",
                "output": None
            }
        
        tool_func = self.registry.get(task.tool)
        if tool_func is None:
            return {
                "success": False,
                "error": f"Tool '{task.tool}' not found in registry",
                "output": None
            }
        
        try:
            output = tool_func(**task.params)
            return {
                "success": True,
                "error": None,
                "output": output
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": None
            }
