# app/agents/predator.py
"""
Agent A: The Predator (นักล่า)
Analyzes offensive techniques, manipulation tactics, and power strategies
"""
from .base_agent import BaseAgent


class PredatorAgent(BaseAgent):
    """
    The Predator - Offensive Analysis Agent
    Focuses on: Attack strategies, manipulation techniques, power plays
    """
    
    def __init__(self):
        super().__init__(name="Predator", temperature=0.4)
    
    def get_system_prompt(self) -> str:
        return """คุณคือ "The Predator" (นักล่า) - ผู้เชี่ยวชาญด้านกลยุทธ์เชิงรุกและจิตวิทยาการโน้มน้าวใจ

บทบาทของคุณ:
- วิเคราะห์เทคนิคการโน้มน้าว การบงการ และการควบคุมจิตใจ
- มองหาจุดอ่อนทางจิตวิทยาที่สามารถใช้ประโยชน์ได้
- อธิบายว่าเทคนิคเหล่านี้ทำงานอย่างไรในเชิงจิตวิทยา
- ยกตัวอย่างการใช้งานจริงในธุรกิจ การเมือง และความสัมพันธ์

สไตล์การพูด:
- ตรงไปตรงมา ไม่อ้อมค้อม
- ใช้ภาษาที่เข้าใจง่าย
- อ้างอิงแนวคิดจากเนื้อหาที่ให้มา
- วิเคราะห์เชิงลึกถึงกลไกทางจิตวิทยา

ข้อควรระวัง:
- ไม่สนับสนุนการใช้เพื่อทำร้ายผู้อื่น
- เน้นการเรียนรู้เพื่อเข้าใจ ไม่ใช่เพื่อหลอกลวง"""
    
    def analyze_offensive(self, content: str, topic: str) -> str:
        """Analyze offensive aspects of a topic"""
        prompt = f"""
วิเคราะห์เทคนิคเชิงรุกและการโน้มน้าวใจในหัวข้อ: {topic}

จงตอบโดย:
1. ระบุเทคนิคการโน้มน้าว/บงการที่พบ
2. อธิบายกลไกทางจิตวิทยาว่าทำไมมันได้ผล
3. ยกตัวอย่างสถานการณ์ที่ใช้ได้
4. บอกระดับความเสี่ยง/อันตราย

ตอบกระชับ ไม่เกิน 300 คำ
"""
        return self.invoke(prompt, context=content)
    
    def identify_vulnerabilities(self, content: str) -> str:
        """Identify psychological vulnerabilities"""
        prompt = """
จากเนื้อหาที่ให้มา ระบุ:
1. จุดอ่อนทางจิตวิทยาที่มนุษย์มักมี
2. อคติทางความคิด (Cognitive Biases) ที่เกี่ยวข้อง
3. ช่วงเวลา/สถานการณ์ที่คนมีความเปราะบางมากที่สุด

ตอบเป็นรายการ กระชับ
"""
        return self.invoke(prompt, context=content)


# Singleton instance
predator = PredatorAgent()
