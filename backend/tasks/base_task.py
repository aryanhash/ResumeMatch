"""
Base Task Runner - Common utilities for Kestra pipeline tasks

Provides:
- Logging setup
- Error handling
- File I/O with validation
- Status reporting
"""
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, Type
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

T = TypeVar('T', bound=BaseModel)


class TaskResult:
    """Result of a task execution"""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.success = False
        self.error: Optional[str] = None
        self.duration: float = 0.0
        self.output: Optional[Dict] = None
        self.warnings: list = []


class BaseTask:
    """
    Base class for all pipeline tasks.
    
    Provides:
    - Automatic logging
    - Error handling
    - File I/O with validation
    - Status tracking
    """
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.logger = logging.getLogger(task_name)
        self.start_time: Optional[datetime] = None
        self.result = TaskResult(task_name)
    
    def start(self):
        """Mark task as started"""
        self.start_time = datetime.now()
        self.logger.info(f"🚀 Starting {self.task_name}")
    
    def complete(self, success: bool = True, message: str = ""):
        """Mark task as completed"""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        self.result.duration = duration
        self.result.success = success
        
        if success:
            self.logger.info(f"✅ {self.task_name} completed in {duration:.2f}s {message}")
        else:
            self.logger.error(f"❌ {self.task_name} failed after {duration:.2f}s: {message}")
    
    def load_json(self, filepath: str, model_class: Optional[Type[T]] = None) -> Any:
        """Load JSON file with validation"""
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Required file not found: {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.logger.debug(f"Loaded: {filepath}")
            
            if model_class:
                return model_class(**data)
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
    
    def save_json(self, data: Any, filepath: str):
        """Save data to JSON file"""
        
        try:
            if hasattr(data, 'model_dump_json'):
                content = data.model_dump_json(indent=2)
            elif hasattr(data, 'model_dump'):
                content = json.dumps(data.model_dump(), indent=2)
            else:
                content = json.dumps(data, indent=2)
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            self.logger.info(f"💾 Saved: {filepath}")
            
        except Exception as e:
            raise IOError(f"Failed to save {filepath}: {e}")
    
    def validate_input(self, data: Dict, required_fields: list) -> list:
        """Validate that required fields exist in data"""
        
        missing = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing.append(field)
        
        if missing:
            self.result.warnings.append(f"Missing fields: {missing}")
            self.logger.warning(f"⚠️ Missing fields: {missing}")
        
        return missing
    
    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable with logging"""
        value = os.getenv(key, default)
        if not value and not default:
            self.logger.warning(f"⚠️ Environment variable {key} not set")
        return value
    
    def run_with_error_handling(self, func, *args, **kwargs):
        """Run function with comprehensive error handling"""
        
        self.start()
        
        try:
            result = func(*args, **kwargs)
            self.complete(success=True)
            return result
            
        except FileNotFoundError as e:
            self.result.error = str(e)
            self.complete(success=False, message=str(e))
            raise
            
        except ValueError as e:
            self.result.error = str(e)
            self.complete(success=False, message=f"Validation error: {e}")
            raise
            
        except Exception as e:
            self.result.error = str(e)
            self.complete(success=False, message=f"Unexpected error: {e}")
            self.logger.exception("Full traceback:")
            raise


def validate_text_input(text: str, name: str, min_length: int = 50, max_length: int = 100000) -> str:
    """Validate text input meets requirements"""
    
    if not text or not text.strip():
        raise ValueError(f"{name} is empty")
    
    text = text.strip()
    
    if len(text) < min_length:
        raise ValueError(f"{name} too short ({len(text)} chars, min {min_length})")
    
    if len(text) > max_length:
        raise ValueError(f"{name} too long ({len(text)} chars, max {max_length})")
    
    # Check for binary content
    if text.startswith(('%PDF', 'PK', '\x00')):
        raise ValueError(f"{name} appears to be binary, not text")
    
    return text

