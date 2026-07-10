"""Task queue with simple priority. No external dependencies."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path(os.environ.get("AGENT_MEMORY_DIR", Path.home() / "agent/memory"))

class Task:
    def __init__(self, task_id: str, description: str, priority: int = 0, 
                 tool: str = None, params: dict = None):
        self.task_id = task_id
        self.description = description
        self.priority = priority
        self.tool = tool
        self.params = params or {}
        self.status = "pending"
        self.created_at = datetime.now().isoformat()
        self.completed_at = None
        self.result = None
        self.error = None
    
    def to_dict(self):
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data):
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            priority=data.get("priority", 0),
            tool=data.get("tool"),
            params=data.get("params", {})
        )
        task.status = data.get("status", "pending")
        task.created_at = data.get("created_at")
        task.completed_at = data.get("completed_at")
        task.result = data.get("result")
        task.error = data.get("error")
        return task

class Scheduler:
    """Manages task queue in memory and persists to JSON."""
    
    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.memory_dir = memory_dir
        self.tasks_file = memory_dir / "tasks.json"
        self.tasks: list[Task] = []
        self._load_tasks()
    
    def _load_tasks(self):
        """Load existing tasks from disk."""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
                self.tasks = [Task.from_dict(t) for t in data]
    
    def _save_tasks(self):
        """Persist tasks to disk (on USB via symlink)."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, 'w') as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)
    
    def add_task(self, description: str, priority: int = 0, 
                 tool: str = None, params: dict = None) -> Task:
        """Add a new task to the queue."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        task = Task(task_id, description, priority, tool, params)
        self.tasks.append(task)
        self._save_tasks()
        return task
    
    def get_next_task(self) -> Optional[Task]:
        """Get highest priority pending task."""
        pending = [t for t in self.tasks if t.status == "pending"]
        if not pending:
            return None
        pending.sort(key=lambda t: (-t.priority, t.created_at))
        return pending[0]
    
    def update_task(self, task_id: str, **kwargs):
        """Update task fields and persist."""
        for task in self.tasks:
            if task.task_id == task_id:
                for key, value in kwargs.items():
                    setattr(task, key, value)
                self._save_tasks()
                return task
        return None
