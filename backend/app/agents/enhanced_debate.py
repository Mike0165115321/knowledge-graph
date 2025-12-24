# app/agents/enhanced_debate.py
"""
Enhanced Multi-Round Debate System
- 2 Reader Agents: Access book content via RAG, debate each other
- 1 Analyst Agent: Analyzes conversation and extracts knowledge graph
"""
import time
import json
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from ..core.config import settings
from ..core.schemas import GraphNode, GraphEdge, NodeType, EdgeType

# Try to import Embedding RAG
try:
    from ..rag import get_embedding_rag, EmbeddingRAG, HAS_EMBEDDINGS
except ImportError:
    HAS_EMBEDDINGS = False
    EmbeddingRAG = None

# Import Specialized Agents
from .predator import PredatorAgent
from .guardian import GuardianAgent
# Note: AnalystAgent is defined in this file, not imported


class BookRAG:
    """Simple RAG system to retrieve relevant book content"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.books: Dict[str, List[dict]] = {}
        self._load_books()
    
    def _load_books(self):
        """Load all JSONL files"""
        if not self.data_dir.exists():
            print(f"⚠️ Data directory {self.data_dir} not found")
            return
            
        for jsonl_file in self.data_dir.glob("*.jsonl"):
            book_name = jsonl_file.stem
            entries = []
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
                self.books[book_name] = entries
                print(f"  📚 Loaded: {book_name} ({len(entries)} entries)")
            except Exception as e:
                print(f"  ❌ Error loading {book_name}: {e}")
        
        print(f"  Total: {len(self.books)} books loaded")
    
    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """Search for relevant content across all books"""
        results = []
        query_lower = query.lower()
        
        for book_name, entries in self.books.items():
            for entry in entries:
                content = entry.get('content', '') or entry.get('description', '')
                title = entry.get('title', '') or entry.get('name', '')
                
                # Simple keyword matching (can be upgraded to embeddings)
                text = f"{title} {content}".lower()
                if any(word in text for word in query_lower.split()):
                    results.append({
                        'book': book_name,
                        'title': title,
                        'content': content[:1000],  # Limit length
                        'source': entry
                    })
        
        # Return top_k results
        return results[:top_k]
    
    def get_random_topics(self, n: int = 10) -> List[str]:
        """Get random topics/concepts from books"""
        topics = []
        for book_name, entries in self.books.items():
            for entry in entries:
                if 'title' in entry:
                    topics.append(entry['title'])
                if 'concepts' in entry:
                    topics.extend(entry['concepts'])
        
        import random
        return random.sample(topics, min(n, len(topics)))


class ReaderAgent:
    """Agent that reads books and debates from a specific perspective"""
    
    def __init__(
        self, 
        name: str,
        perspective: str,
        system_prompt: str,
        rag: Union['BookRAG', 'EmbeddingRAG']
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


class StrategistAgent(ReaderAgent):
    """
    Strategist Agent - ตัวแทนเชิงกลยุทธ์ของผู้สร้างระบบ (Analytic INFJ)
    วิเคราะห์ Game State, Framing, Hidden Intent, และ Implications
    """
    
    def __init__(self, rag: Union['BookRAG', 'EmbeddingRAG']):
        # Import the strategist prompt
        from ..core.strategist_config import STRATEGIST_SYSTEM_PROMPT
        
        super().__init__(
            name="Strategist",
            perspective="ตัวแทนเชิงกลยุทธ์ (Analytic INFJ)",
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            rag=rag
        )
    
    def _init_llm(self):
        """Override with lower temperature for analytical output"""
        api_key = settings.get_api_key()
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.5  # Lower temperature for strategic analysis
        )
    
    def _refresh_key(self):
        """Refresh API key if rate limited"""
        settings.rotate_api_key()
        api_key = settings.get_api_key()
        print(f"    🔄 Rotated Key for Strategist (Index: {settings.api_key_manager.current_index})")
        
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.5
        )


class AnalystAgent:
    """Agent that analyzes debates and extracts knowledge graph"""
    
    def __init__(self):
        self._llm = None
        self._init_llm()
    
    def _init_llm(self):
        api_key = settings.get_api_key()
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.3  # Lower for more structured output
        )
    
    def _refresh_key(self):
        settings.rotate_api_key() # FORCE ROTATION
        api_key = settings.get_api_key()
        print(f"    🔄 Rotated Analyst Key (Index: {settings.api_key_manager.current_index})")
        
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
    
    def analyze_and_extract(
        self, 
        topic: str,
        conversation: List[Dict],
        max_retries: int = 3
    ) -> Tuple[List[dict], List[dict]]:
        """Analyze debate and extract nodes/edges"""
        
        conv_text = "\n\n".join([
            f"**{msg['agent']}**: {msg['content']}"
            for msg in conversation
        ])
        
        prompt = f"""
คุณคือนักวิเคราะห์ความรู้ระดับสูง (Senior Knowledge Graph Architect) 
หน้าที่ของคุณคือ "ขุด" (Mine) ความรู้จากบทสนทนาให้ได้มากที่สุดเท่าที่จะเป็นไปได้ อย่าทิ้งประเด็นสำคัญ

หัวข้อ: {topic}

บทสนทนา:
{conv_text}

---

ภารกิจ:
1. วิเคราะห์บทสนทนาอย่างละเอียดทุกประโยค
2. สกัด Nodes ออกมาให้ "เยอะที่สุด" เท่าที่จะทำได้ (อย่างน้อย 10-20 Nodes ถ้าทำได้)
3. เชื่อมโยงความสัมพันธ์ (Edges) ให้ซับซ้อนและครอบคลุม
4. ห้ามทิ้งรายละเอียดเล็กน้อยที่เป็นเทคนิค (Technique) หรือ ความเสี่ยง (Risk)

รูปแบบ Graph Schema:

NODES:
- id: unique_id (snake_case language agnostic, e.g., 'psychological_manipulation')
- name: ชื่อที่กระชับ สื่อความหมาย (ภาษาไทย)
- type: เลือกจาก [concept, technique, risk, defense, example, principle, bias, fallacy]
- description: คำอธิบายสั้นๆ 1 ประโยค

EDGES:
- source: node_id ต้นทาง
- target: node_id ปลายทาง
- type: เลือกจาก [causes, prevents, is_a, part_of, uses, counters, leads_to, correlated_with]

สำคัญ: 
- ขอปริมาณ (Quantity) และ คุณภาพ (Quality) สูงสุด
- อย่าสรุปย่อจนความหาย

ตอบเป็น JSON เท่านั้น:
```json
{{
  "nodes": [...],
  "edges": [...]
}}
```
"""
        
        for attempt in range(max_retries):
            try:
                response = self._llm.invoke(prompt)
                content = response.content
                
                # Extract JSON from response
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content
                
                data = json.loads(json_str.strip())
                return data.get('nodes', []), data.get('edges', [])
                
            except json.JSONDecodeError as e:
                print(f"    ⚠️ JSON parse error, retrying...")
                continue
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = (attempt + 1) * 15 # Progressive backoff: 15s, 30s, 45s
                    print(f"    ⚠️ Rate limit hit. Cooling down for {wait_time}s and switching key...")
                    time.sleep(wait_time) 
                    self._refresh_key()
                else:
                    print(f"    ❌ Error extracting graph: {e}")
                    # Don't crash the debate for graph failure, just return empty to keep UI running
                    return [], []
        
        return [], []
    
    def convert_to_schema(
        self, 
        raw_nodes: List[dict], 
        raw_edges: List[dict],
        source: str = "debate"
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Convert raw dicts to schema objects"""
        
        type_map = {
            'concept': NodeType.CONCEPT,
            'technique': NodeType.TECHNIQUE,
            'risk': NodeType.RISK,
            'defense': NodeType.DEFENSE,
            'outcome': NodeType.OUTCOME,
            'insight': NodeType.CONCEPT,
        }
        
        edge_type_map = {
            'causes': EdgeType.CAUSES,
            'prevents': EdgeType.PREVENTS,
            'enables': EdgeType.ENABLES,
            'contradicts': EdgeType.CONTRADICTS,
            'supports': EdgeType.RELATED_TO,
            'relates_to': EdgeType.RELATED_TO,
        }
        
        nodes = []
        for n in raw_nodes:
            try:
                nodes.append(GraphNode(
                    id=n.get('id', ''),
                    name=n.get('name', n.get('id', '')),
                    type=type_map.get(n.get('type', 'concept'), NodeType.CONCEPT),
                    description=n.get('description'),
                    source_book=source
                ))
            except Exception:
                continue
        
        edges = []
        for e in raw_edges:
            try:
                edges.append(GraphEdge(
                    source=e.get('source', ''),
                    target=e.get('target', ''),
                    type=edge_type_map.get(e.get('type', 'relates_to'), EdgeType.RELATED_TO)
                ))
            except Exception:
                continue
        
        return nodes, edges


class EnhancedDebateSystem:
    """
    Multi-round debate system with:
    - 2 Reader agents with book access (via Embedding RAG or keyword search)
    - 1 Strategist agent for strategic analysis (optional)
    - 1 Analyst agent for graph extraction
    """
    
    def __init__(
        self, 
        data_dir: str = "data",
        embedding_model_path: str = "/home/mikedev/MyModels/Model-RAG/intfloat-multilingual-e5-large",
        use_embeddings: bool = True,
        enable_strategist: bool = True  # NEW: เปิด/ปิด Strategist Agent
    ):
        print("🚀 Initializing Enhanced Debate System...")
        
        # Initialize RAG (prefer Embedding RAG if available)
        if use_embeddings and HAS_EMBEDDINGS:
            print(f"  📦 Using Embedding RAG...")
            self.rag = get_embedding_rag(model_path=embedding_model_path, data_dir=data_dir)
            self.rag.initialize()
        else:
            print(f"  📖 Using Simple RAG...")
            self.rag = BookRAG(data_dir=data_dir)
        
        # Initialize Agents with Specialized Personas
        self.attacker = PredatorAgent(rag=self.rag)
        self.defender = GuardianAgent(rag=self.rag)
        print("  🔴 Predator Agent initialized")
        print("  🟢 Guardian Agent initialized")
        
        # Initialize Strategist (optional)
        self.enable_strategist = enable_strategist
        if enable_strategist:
            self.strategist = StrategistAgent(rag=self.rag)
            print("  🟣 Strategist Agent initialized")
        else:
            self.strategist = None
        
        # Initialize Analyst
        self.analyst = AnalystAgent()
        
        print("✅ System ready!")
    
    def run_debate(
        self, 
        topic: str, 
        rounds: int = 3,
        delay: float = 1.0
    ) -> Dict:
        """
        Run a multi-round debate on a topic
        
        Args:
            topic: The debate topic
            rounds: Number of back-and-forth rounds
            delay: Delay between API calls
        
        Returns:
            Dict with conversation, nodes, and edges
        """
        print(f"\n{'='*50}")
        print(f"🔥 DEBATE: {topic}")
        print(f"{'='*50}")
        
        conversation = []
        
        for round_num in range(rounds):
            print(f"\n--- Round {round_num + 1}/{rounds} ---")
            
            # Attacker speaks
            print(f"  🔴 แมน thinking...")
            attacker_response = self.attacker.respond(topic, conversation)
            conversation.append({
                "agent": "🔴 แมน",
                "content": attacker_response
            })
            print(f"     ✓ แมน responded")
            time.sleep(delay)
            
            # Defender responds
            print(f"  🟢 Defender thinking...")
            defender_response = self.defender.respond(topic, conversation)
            conversation.append({
                "agent": "🟢 Defender",
                "content": defender_response
            })
            print(f"     ✓ Defender responded")
            time.sleep(delay)
            
            # Strategist analyzes (if enabled)
            if self.enable_strategist and self.strategist:
                print(f"  🟣 Strategist analyzing...")
                strategist_response = self.strategist.respond(topic, conversation)
                conversation.append({
                    "agent": "🟣 Strategist",
                    "content": strategist_response
                })
                print(f"     ✓ Strategist responded")
                time.sleep(delay)
        
        # Analyst extracts graph
        print(f"\n  🔵 Analyst extracting knowledge graph...")
        raw_nodes, raw_edges = self.analyst.analyze_and_extract(topic, conversation)
        nodes, edges = self.analyst.convert_to_schema(
            raw_nodes, raw_edges, 
            source=f"Debate: {topic}"
        )
        
        print(f"  ✅ Extracted: {len(nodes)} nodes, {len(edges)} edges")
        
        return {
            "topic": topic,
            "rounds": rounds,
            "conversation": conversation,
            "nodes": nodes,
            "edges": edges,
            "raw_nodes": raw_nodes,
            "raw_edges": raw_edges
        }
    
    def stream_debate(
        self, 
        topic: str, 
        rounds: int = 3,
        delay: float = 1.0
    ):
        """
        Generator that streams debate progress
        Yields: Dict with keys 'type', 'agent', 'content', 'data'
        """
        conversation = []
        
        yield {
            "type": "start", 
            "topic": topic,
            "message": f"🔥 Starting debate on: {topic}"
        }
        
        for round_num in range(rounds):
            yield {"type": "info", "message": f"\n--- Round {round_num + 1}/{rounds} ---"}
            
            # Attacker speaks
            yield {"type": "thinking", "agent": "🔴 แมน"}
            attacker_response = self.attacker.respond(topic, conversation)
            conversation.append({
                "agent": "🔴 แมน",
                "content": attacker_response
            })
            yield {
                "type": "message", 
                "agent": "🔴 แมน", 
                "content": attacker_response
            }
            time.sleep(delay)
            
            # Defender responds
            yield {"type": "thinking", "agent": "🟢 Defender"}
            defender_response = self.defender.respond(topic, conversation)
            conversation.append({
                "agent": "🟢 Defender",
                "content": defender_response
            })
            yield {
                "type": "message", 
                "agent": "🟢 Defender", 
                "content": defender_response
            }
            time.sleep(delay)
            
            # Strategist analyzes (if enabled)
            if self.enable_strategist and self.strategist:
                yield {"type": "thinking", "agent": "🟣 Strategist"}
                strategist_response = self.strategist.respond(topic, conversation)
                conversation.append({
                    "agent": "🟣 Strategist",
                    "content": strategist_response
                })
                yield {
                    "type": "message", 
                    "agent": "🟣 Strategist", 
                    "content": strategist_response
                }
                time.sleep(delay)

            # Incremental Analysis (Analyst peeks every round)
            yield {"type": "thinking", "agent": "🔵 Analyst", "message": f"Analyzing Round {round_num + 1}..."}
            
            # Analyze conversation so far
            raw_nodes, raw_edges = self.analyst.analyze_and_extract(topic, conversation)
            nodes, edges = self.analyst.convert_to_schema(
                raw_nodes, raw_edges, 
                source=f"Debate: {topic}"
            )
            
            yield {
                "type": "graph_update", 
                "nodes": [n.dict() for n in nodes],
                "edges": [e.dict() for e in edges],
                "stats": {"nodes": len(nodes), "edges": len(edges)}
            }
        
        yield {
            "type": "complete",
            "conversation": conversation
        }

    def run_batch_debates(
        self,
        topics: List[str],
        rounds: int = 2,
        delay: float = 2.0
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Run debates on multiple topics"""
        
        print(f"\n🚀 Batch Debate: {len(topics)} topics, {rounds} rounds each")
        
        all_nodes = []
        all_edges = []
        
        for i, topic in enumerate(topics):
            print(f"\n[{i+1}/{len(topics)}]")
            
            try:
                result = self.run_debate(topic, rounds=rounds, delay=delay)
                all_nodes.extend(result['nodes'])
                all_edges.extend(result['edges'])
                time.sleep(delay * 2)  # Extra delay between debates
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        print(f"\n{'='*50}")
        print(f"🎉 BATCH COMPLETE!")
        print(f"   Total nodes: {len(all_nodes)}")
        print(f"   Total edges: {len(all_edges)}")
        print(f"{'='*50}")
        
        return all_nodes, all_edges


# Singleton instance
enhanced_debate = None

def get_enhanced_debate(
    data_dir: str = "data",
    embedding_model_path: str = "/home/mikedev/MyModels/Model-RAG/intfloat-multilingual-e5-large",
    use_embeddings: bool = True
) -> EnhancedDebateSystem:
    global enhanced_debate
    if enhanced_debate is None:
        enhanced_debate = EnhancedDebateSystem(
            data_dir=data_dir,
            embedding_model_path=embedding_model_path,
            use_embeddings=use_embeddings
        )
    return enhanced_debate
