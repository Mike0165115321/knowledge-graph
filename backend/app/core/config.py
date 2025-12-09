# app/core/config.py
"""
Configuration management with API key rotation support
"""
import os
from dotenv import load_dotenv
from typing import List
import random

load_dotenv()

class APIKeyManager:
    """Manages multiple API keys with rotation on rate limit"""
    
    def __init__(self, keys_string: str):
        self.keys: List[str] = [k.strip() for k in keys_string.split(',') if k.strip()]
        self.current_index = 0
        self.failed_keys: set = set()
    
    def get_key(self) -> str:
        """Get current API key"""
        if not self.keys:
            raise ValueError("No API keys configured!")
        
        available_keys = [k for k in self.keys if k not in self.failed_keys]
        if not available_keys:
            # Reset failed keys and try again
            self.failed_keys.clear()
            available_keys = self.keys
        
        return available_keys[self.current_index % len(available_keys)]
    
    def rotate(self):
        """Rotate to next key (call when rate limited)"""
        self.current_index += 1
    
    def mark_failed(self, key: str):
        """Mark a key as temporarily failed"""
        self.failed_keys.add(key)
        self.rotate()
    
    def get_random_key(self) -> str:
        """Get a random key (for parallel processing)"""
        available = [k for k in self.keys if k not in self.failed_keys]
        return random.choice(available) if available else self.keys[0]
    
    @property
    def total_keys(self) -> int:
        return len(self.keys)


class Settings:
    """Application settings"""
    
    # API Keys
    GOOGLE_API_KEYS: str = os.getenv("GOOGLE_API_KEYS", "")
    
    # Neo4j
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Paths
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "../../data")
    
    # Processing
    BATCH_SIZE: int = 10
    DEBATE_TOP_N: int = 25  # Number of topics for auto-debate
    
    def __init__(self):
        self.api_key_manager = APIKeyManager(self.GOOGLE_API_KEYS)
    
    def get_api_key(self) -> str:
        """Get an API key from the rotation pool"""
        return self.api_key_manager.get_key()
    
    def rotate_api_key(self):
        """Rotate to next API key"""
        self.api_key_manager.rotate()


settings = Settings()