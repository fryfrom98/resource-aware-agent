#!/usr/bin/env python3
"""Resource-Aware AI Agent - Phase 3: Core loop with test tasks."""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.scheduler import Scheduler
from core.executor import Executor
from tools.registry import ToolRegistry

# --- Configuration ---
MEMORY_DIR = Path(os.environ.get("AGENT_MEMORY_DIR", Path.home() / "agent/memory"))
LOG_DIR = Path(os.environ.get("AGENT_LOG_DIR", Path.home() / "agent/logs"))
LOOP_INTERVAL = 5  # Seconds between loop iterations when idle

class Agent:
    """Main agent orchestrator."""
    
    def __init__(self):
        self.memory_dir = MEMORY_DIR
        self.log_dir = LOG_DIR
        self.scheduler = Scheduler(self.memory_dir)
        self.registry = ToolRegistry()
        self.executor = Executor(self.registry)
        self.running = False
        self.state = self._load_state()
        
        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> dict:
        """Load agent state from memory."""
        state_file = self.memory_dir / "state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return {"agent_version": "0.1.0", "phase": 3, "total_tasks_completed": 0}
    
    def _save_state(self):
        """Persist agent state."""
        state_file = self.memory_dir / "state.json"
        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log(self, message: str, level: str = "INFO"):
        """Write to log file and print."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        
        # Append to daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"agent_{today}.log"
        with open(log_file, 'a') as f:
            f.write(log_entry + "\n")
    
    def add_test_tasks(self):
        """Add sample tasks for testing the loop."""
        self._log("Adding test tasks...")
        
        self.scheduler.add_task(
            description="Echo a test message",
            priority=1,
            tool="echo",
            params={"message": "Hello from the agent loop!"}
        )
        
        self.scheduler.add_task(
            description="Add two numbers",
            priority=2,
            tool="add",
            params={"a": 42, "b": 8}
        )
        
        self.scheduler.add_task(
            description="Get current time",
            priority=0,
            tool="get_time",
            params={}
        )
        
        self.scheduler.add_task(
            description="This task should fail (testing error handling)",
            priority=3,
            tool="fail_test",
            params={}
        )
        
        self._log(f"Added {len(self.scheduler.tasks)} test tasks")
    
    def run_once(self):
        """Process one task from the queue."""
        task = self.scheduler.get_next_task()
        
        if task is None:
            self._log("No pending tasks. Idle.", level="DEBUG")
            return False  # Nothing to do
        
        self._log(f"Executing task: {task.description} (ID: {task.task_id})")
        
        # Mark as running
        self.scheduler.update_task(task.task_id, status="running")
        
        # Execute
        result = self.executor.execute_task(task)
        
        # Update task with result
        if result["success"]:
            self.scheduler.update_task(
                task.task_id,
                status="completed",
                completed_at=datetime.now().isoformat(),
                result=result["output"]
            )
            self.state["total_tasks_completed"] += 1
            self._log(f"✓ Task completed: {result['output']}")
        else:
            self.scheduler.update_task(
                task.task_id,
                status="failed",
                completed_at=datetime.now().isoformat(),
                error=result["error"]
            )
            self._log(f"✗ Task failed: {result['error']}", level="ERROR")
        
        self._save_state()
        return True  # Did work
    
    def run(self, max_iterations: int = None):
        """Run the agent loop continuously.
        
        Args:
            max_iterations: Stop after N iterations (None = run forever)
        """
        self.running = True
        iterations = 0
        
        self._log("=" * 50)
        self._log("Agent starting - Phase 3: Core Loop (No AI)")
        self._log(f"Memory dir: {self.memory_dir}")
        self._log(f"Log dir: {self.log_dir}")
        self._log(f"Available tools: {self.registry.list_tools()}")
        self._log(f"Tasks in queue: {len(self.scheduler.tasks)}")
        self._log("=" * 50)
        
        try:
            while self.running:
                if max_iterations and iterations >= max_iterations:
                    self._log(f"Reached max iterations ({max_iterations}). Stopping.")
                    break
                
                did_work = self.run_once()
                
                if not did_work:
                    # No tasks to process, wait before checking again
                    time.sleep(LOOP_INTERVAL)
                
                iterations += 1
                
        except KeyboardInterrupt:
            self._log("Received interrupt. Shutting down gracefully...")
        finally:
            self._log(f"Agent stopped. Total iterations: {iterations}, Tasks completed: {self.state['total_tasks_completed']}")
            self._save_state()
    
    def stop(self):
        """Stop the agent loop."""
        self.running = False


def main():
    """Entry point for testing."""
    agent = Agent()
    
    # Add test tasks for the first run
    if len(agent.scheduler.tasks) == 0:
        agent.add_test_tasks()
    
    # Run a few iterations for testing
    agent.run(max_iterations=10)


if __name__ == "__main__":
    main()
