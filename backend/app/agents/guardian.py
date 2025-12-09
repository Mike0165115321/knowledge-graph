# app/agents/guardian.py
"""
Agent B: The Guardian (ผู้พิทักษ์)
Analyzes defensive techniques, risk awareness, and protection strategies
"""
from .base_agent import BaseAgent


class GuardianAgent(BaseAgent):
    """
    The Guardian - Defensive Analysis Agent
    Focuses on: Protection strategies, risk identification, warning signs
    """
    
    def __init__(self):
        super().__init__(name="Guardian", temperature=0.3)
    
    def get_system_prompt(self) -> str:
        return """คุณคือ "The Guardian" (ผู้พิทักษ์) - ผู้เชี่ยวชาญด้านการป้องกันและความปลอดภัยทางจิตใจ

บทบาทของคุณ:
- วิเคราะห์ความเสี่ยงและอันตรายจากการถูกบงการ
- ระบุสัญญาณเตือนภัยว่ากำลังถูกโน้มน้าว/หลอกลวง
- เสนอแนะวิธีการป้องกันตนเองและสร้างภูมิคุ้มกัน
- โต้แย้งมุมมองที่เน้นการโจมตีด้วยมุมมองเชิงจริยธรรม

สไตล์การพูด:
- สุขุม รอบคอบ
- เน้นความปลอดภัยและผลกระทบระยะยาว
- อ้างอิงแนวคิดจากเนื้อหาที่ให้มา
- เตือนสติถึงด้านมืดของการใช้เทคนิคเหล่านี้

จุดยืน:
- สนับสนุนการเรียนรู้เพื่อป้องกัน ไม่ใช่เพื่อหลอกลวง
- เชื่อว่าความรู้คือพลังในการปกป้องตนเอง"""
    
    def analyze_defensive(self, content: str, topic: str) -> str:
        """Analyze defensive aspects of a topic"""
        prompt = f"""
วิเคราะห์วิธีการป้องกันตนเองจากหัวข้อ: {topic}

จงตอบโดย:
1. ระบุสัญญาณเตือนว่ากำลังถูกใช้เทคนิคนี้
2. อธิบายวิธีการป้องกันหรือตอบโต้
3. บอกผลกระทบระยะยาวหากไม่ป้องกัน
4. เสนอแนะการสร้างภูมิคุ้มกันทางจิตใจ

ตอบกระชับ ไม่เกิน 300 คำ
"""
        return self.invoke(prompt, context=content)
    
    def counter_argument(self, predator_analysis: str, topic: str) -> str:
        """Provide counter-argument to Predator's analysis"""
        prompt = f"""
หัวข้อ: {topic}

การวิเคราะห์จาก The Predator:
{predator_analysis}

ในฐานะ The Guardian จงโต้แย้งโดย:
1. ชี้ให้เห็นความเสี่ยงที่ถูกมองข้าม
2. เตือนถึงผลเสียของการใช้เทคนิคเหล่านี้
3. เสนอทางเลือกที่มีจริยธรรมมากกว่า
4. สรุปบทเรียนสำหรับการป้องกันตนเอง

ตอบกระชับ ไม่เกิน 250 คำ
"""
        return self.invoke(prompt, context="")
    
    def identify_protection(self, content: str) -> str:
        """Identify protection methods"""
        prompt = """
จากเนื้อหาที่ให้มา ระบุ:
1. วิธีการป้องกันตนเองที่กล่าวถึง
2. สัญญาณเตือนภัยที่ควรสังเกต
3. ขอบเขตที่ควรตั้ง (Boundaries)

ตอบเป็นรายการ กระชับ
"""
        return self.invoke(prompt, context=content)


# Singleton instance
guardian = GuardianAgent()
