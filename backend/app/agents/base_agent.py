# app/agents/base_agent.py
"""
Base Agent class with API key rotation and rate limit handling
"""
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from ..core.config import settings


class RateLimitError(Exception):
    """Raised when API rate limit is hit"""
    pass


class BaseAgent(ABC):
    """Base class for all AI agents with API key rotation"""
    
    def __init__(self, name: str, temperature: float = 0.3):
        self.name = name
        self.temperature = temperature
        self._llm = None
        self._current_key = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM with current API key"""
        self._current_key = settings.get_api_key()
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self._current_key,
            temperature=self.temperature
        )
    
    def _rotate_and_retry(self):
        """Rotate API key and reinitialize LLM"""
        print(f"🔄 {self.name}: Rotating API key...")
        settings.rotate_api_key()
        self._init_llm()
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass
    
    def invoke(self, user_prompt: str, context: str = "", max_retries: int = 3) -> str:
        """
        Invoke the agent with automatic retry and key rotation
        """
        system_prompt = self.get_system_prompt()
        full_prompt = f"{system_prompt}\n\nContext:\n{context}\n\nTask:\n{user_prompt}"
        
        for attempt in range(max_retries):
            try:
                response = self._llm.invoke(full_prompt)
                return response.content
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for rate limit errors
                if "rate" in error_msg or "limit" in error_msg or "quota" in error_msg:
                    print(f"⚠️ {self.name}: Rate limit hit on attempt {attempt + 1}")
                    self._rotate_and_retry()
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Check for other retryable errors
                if "timeout" in error_msg or "connection" in error_msg:
                    print(f"⚠️ {self.name}: Connection error, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                
                # Non-retryable error
                print(f"❌ {self.name}: Error - {e}")
                raise
        
        raise RateLimitError(f"All API keys exhausted after {max_retries} attempts")
