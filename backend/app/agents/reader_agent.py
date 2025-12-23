# app/agents/reader_agent.py
"""
Base Reader Agent with RAG integration
Used as parent class for Predator, Guardian, and Strategist
"""
import time
from typing import List, Dict, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from ..core.config import settings


class ReaderAgent:
    """Agent that reads books and debates from a specific perspective"""
    
    def __init__(
        self, 
        name: str,
        perspective: str,
        system_prompt: str,
        rag
    ):
        self.name = name
        self.perspective = perspective
        self.system_prompt = system_prompt
        self.rag = rag
        self._llm = None
        self._init_llm()
    
    def _init_llm(self):
        api_key = settings.get_api_key()
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
    
    def _refresh_key(self):
        """Refresh API key if rate limited"""
        settings.rotate_api_key() # FORCE ROTATION
        api_key = settings.get_api_key()
        print(f"    🔄 Rotated Key for {self.name} (Index: {settings.api_key_manager.current_index})")
        
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
    
    def respond(
        self, 
        topic: str, 
        conversation_history: List[Dict],
        max_retries: int = 3
    ) -> str:
        """Generate a response based on topic, book knowledge, and conversation"""
        
        # Get relevant book content
        relevant_content = self.rag.search(topic, top_k=3)
        book_context = "\n\n".join([
            f"📚 จาก {r['book']}:\n{r['content']}"
            for r in relevant_content
        ]) if relevant_content else "ไม่พบข้อมูลที่เกี่ยวข้องโดยตรง"
        
        # Format conversation history
        conv_text = "\n".join([
            f"{msg['agent']}: {msg['content']}"
            for msg in conversation_history[-4:]  # Last 4 messages
        ]) if conversation_history else "เริ่มการถกเถียงใหม่"
        
        prompt = PromptTemplate(
            template="""
{system_prompt}

หัวข้อถกเถียง: {topic}

📚 ข้อมูลจากหนังสือ:
{book_context}

💬 ประวัติการสนทนา:
{conversation}

ตอบในมุมมองของ {perspective}:
- อ้างอิงข้อมูลจากหนังสือ
- โต้แย้งหรือเสริมจากบทสนทนาก่อนหน้า
- ตอบกระชับได้ใจความ 2-3 ย่อหน้า
""",
            input_variables=["system_prompt", "topic", "book_context", "conversation", "perspective"]
        )
        
        for attempt in range(max_retries):
            try:
                formatted = prompt.format(
                    system_prompt=self.system_prompt,
                    topic=topic,
                    book_context=book_context,
                    conversation=conv_text,
                    perspective=self.perspective
                )
                response = self._llm.invoke(formatted)
                return response.content
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print(f"    ⚠️ Rate limit, switching key...")
                    self._refresh_key()
                    time.sleep(2)
                else:
                    raise e
        
        return f"[{self.name} ไม่สามารถตอบได้]"
