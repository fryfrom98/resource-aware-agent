#!/usr/bin/env python3
"""
Memory module for agent state persistence.
Stores agent state as JSON files on USB drive via symlink.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List


class AgentMemory:
    """Handles reading/writing agent state to JSON files."""
    
    def __init__(self, memory_dir: str = None):
        """
        Initialize memory with directory path.
        
        Args:
            memory_dir: Path to memory directory (defaults to ~/agent/memory)
        """
        if memory_dir is None:
            # Use ~/agent/memory (which should be symlinked to USB)
            self.memory_dir = Path.home() / "agent" / "memory"
        else:
            self.memory_dir = Path(memory_dir)
        
        # Resolve symlink to get actual path
        if self.memory_dir.is_symlink():
            self.memory_dir = self.memory_dir.resolve()
        
        # Create directory if it doesn't exist (on the USB drive)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Default state template
        self.default_state = {
            "agent_id": "celeron_agent_001",
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "state": "idle",  # idle | busy | error
            "tasks": [],
            "context": {},
            "stats": {
                "tasks_completed": 0,
                "errors": 0,
                "total_tasks": 0
            }
        }
    
    def _get_filepath(self, filename: str) -> Path:
        """Get full path for a memory file."""
        # Ensure filename ends with .json
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        return self.memory_dir / filename
    
    def save(self, filename: str, state: Dict[str, Any]) -> bool:
        """
        Save state to a JSON file.
        
        Args:
            filename: Name of the file (with or without .json)
            state: Dictionary containing agent state
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            filepath = self._get_filepath(filename)
            
            # Update last_active timestamp
            state["last_active"] = datetime.now().isoformat()
            
            # Write to a temporary file first, then rename for atomicity
            temp_file = filepath.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            # Atomic rename (on same filesystem)
            temp_file.replace(filepath)
            return True
            
        except Exception as e:
            print(f"Error saving state to {filename}: {e}")
            return False
    
    def load(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load state from a JSON file.
        
        Args:
            filename: Name of the file (with or without .json)
            
        Returns:
            dict: Agent state, or None if file doesn't exist or is corrupt
        """
        try:
            filepath = self._get_filepath(filename)
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            return state
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {filename}: {e}")
            return None
        except Exception as e:
            print(f"Error loading state from {filename}: {e}")
            return None
    
    def load_or_create(self, filename: str) -> Dict[str, Any]:
        """
        Load state, or create a new default state if file doesn't exist.
        
        Args:
            filename: Name of the file
            
        Returns:
            dict: Agent state (loaded or newly created)
        """
        state = self.load(filename)
        if state is None:
            # Create a fresh state with timestamp
            state = self.default_state.copy()
            state["created_at"] = datetime.now().isoformat()
            # Save it immediately
            self.save(filename, state)
        return state
    
    def update_key(self, filename: str, key: str, value: Any) -> bool:
        """
        Update a single key in the state and save.
        
        Args:
            filename: Name of the file
            key: Dot-notation key (e.g., "stats.tasks_completed")
            value: New value
            
        Returns:
            bool: True if successful, False otherwise
        """
        state = self.load(filename)
        if state is None:
            # Try to load or create
            state = self.load_or_create(filename)
        
        # Handle dot notation for nested keys
        keys = key.split('.')
        current = state
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        
        return self.save(filename, state)
    
    def get_key(self, filename: str, key: str, default: Any = None) -> Any:
        """
        Get a value from state by key (supports dot notation).
        
        Args:
            filename: Name of the file
            key: Dot-notation key (e.g., "stats.tasks_completed")
            default: Default value if key doesn't exist
            
        Returns:
            Value at key, or default if not found
        """
        state = self.load(filename)
        if state is None:
            return default
        
        # Handle dot notation
        keys = key.split('.')
        current = state
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current
    
    def list_files(self) -> List[str]:
        """List all JSON files in memory directory."""
        return [f.name for f in self.memory_dir.glob("*.json")]
    
    def delete(self, filename: str) -> bool:
        """
        Delete a state file.
        
        Args:
            filename: Name of the file
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            filepath = self._get_filepath(filename)
            if filepath.exists():
                filepath.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting {filename}: {e}")
            return False
    
    def append_task(self, filename: str, task: Dict[str, Any]) -> bool:
        """
        Append a task to the tasks list in state.
        
        Args:
            filename: Name of the file
            task: Task dictionary with at least 'description' and 'status'
            
        Returns:
            bool: True if successful
        """
        state = self.load_or_create(filename)
        
        # Ensure tasks list exists
        if "tasks" not in state:
            state["tasks"] = []
        
        # Add task with timestamp
        task["added_at"] = datetime.now().isoformat()
        task["id"] = len(state["tasks"]) + 1
        
        state["tasks"].append(task)
        state["stats"]["total_tasks"] += 1
        
        return self.save(filename, state)
    
    def get_pending_tasks(self, filename: str) -> List[Dict[str, Any]]:
        """
        Get all pending tasks from the state.
        
        Args:
            filename: Name of the file
            
        Returns:
            list: List of pending tasks (status: pending or in_progress)
        """
        state = self.load(filename)
        if state is None:
            return []
        
        tasks = state.get("tasks", [])
        return [t for t in tasks if t.get("status") in ["pending", "in_progress"]]


# Simple standalone usage example
if __name__ == "__main__":
    # Test the memory module
    memory = AgentMemory()
    
    # Test 1: Create and save state
    print("Testing memory module...")
    state = memory.load_or_create("agent_state.json")
    print(f"✓ Created/loaded state for agent: {state['agent_id']}")
    
    # Test 2: Update a key
    memory.update_key("agent_state.json", "state", "busy")
    print(f"✓ Updated state to: {memory.get_key('agent_state.json', 'state')}")
    
    # Test 3: Add a task
    task = {
        "description": "Test task",
        "status": "pending",
        "priority": 1
    }
    memory.append_task("agent_state.json", task)
    pending = memory.get_pending_tasks("agent_state.json")
    print(f"✓ Added task. Pending tasks: {len(pending)}")
    
    # Test 4: List files
    files = memory.list_files()
    print(f"✓ Memory files: {files}")
    
    print("\nMemory module test complete!")
