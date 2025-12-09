# app/agents/cartographer.py
"""
Agent C: The Cartographer (ผู้สร้างแผนที่)
Extracts knowledge graph structure from content and debates
"""
import json
import re
from typing import List, Tuple, Optional
from .base_agent import BaseAgent
from ..core.schemas import GraphNode, GraphEdge, NodeType, EdgeType


class CartographerAgent(BaseAgent):
    """
    The Cartographer - Knowledge Graph Extractor Agent
    Focuses on: Extracting nodes, edges, and relationships
    """
    
    def __init__(self):
        super().__init__(name="Cartographer", temperature=0.1)  # Low temp for consistency
    
    def get_system_prompt(self) -> str:
        return """คุณคือ "The Cartographer" (ผู้สร้างแผนที่ความรู้) - ผู้เชี่ยวชาญในการสกัดโครงสร้างความรู้

บทบาทของคุณ:
- สกัดแนวคิด (Concepts) จากเนื้อหาที่ให้มา
- ระบุความสัมพันธ์ระหว่างแนวคิด
- แปลงข้อมูลเป็นโครงสร้าง JSON ที่ถูกต้อง

กฎสำคัญ:
- ตอบเป็น JSON เท่านั้น ห้ามพูดพร่ำทำเพลง
- ใช้ภาษาไทยสำหรับชื่อ nodes
- ใช้ภาษาอังกฤษสำหรับ relation types
- ทุก node ต้องมี id และ name"""
    
    def extract_graph_from_content(self, content: str, source_book: str = None) -> Tuple[List[dict], List[dict]]:
        """Extract graph structure from raw content"""
        prompt = f"""
จากเนื้อหาต่อไปนี้ จงสกัดเป็น JSON:

{content[:3000]}

ตอบในรูปแบบ JSON เท่านั้น:
{{
  "nodes": [
    {{"id": "unique_id", "name": "ชื่อแนวคิด", "type": "concept|technique|risk|defense"}},
    ...
  ],
  "edges": [
    {{"source": "node_id_1", "target": "node_id_2", "relation": "leads_to|prevents|causes|uses|counters"}},
    ...
  ]
}}

จำกัด: สูงสุด 10 nodes และ 15 edges ที่สำคัญที่สุด
"""
        response = self.invoke(prompt)
        return self._parse_json_response(response)
    
    def extract_from_debate(self, topic: str, predator_msg: str, guardian_msg: str) -> Tuple[List[dict], List[dict]]:
        """Extract graph structure from a debate session"""
        prompt = f"""
หัวข้อ: {topic}

การวิเคราะห์จาก The Predator:
{predator_msg[:1500]}

การวิเคราะห์จาก The Guardian:
{guardian_msg[:1500]}

จงสกัดความรู้จากทั้งสองมุมมองเป็น JSON:
{{
  "nodes": [
    {{"id": "unique_id", "name": "ชื่อแนวคิด", "type": "concept|technique|risk|defense"}},
    ...
  ],
  "edges": [
    {{"source": "node_id_1", "target": "node_id_2", "relation": "leads_to|prevents|causes|uses|counters"}},
    ...
  ]
}}

ข้อสำคัญ:
- รวมทั้งเทคนิคเชิงรุก (จาก Predator) และการป้องกัน (จาก Guardian)
- สร้าง edges ที่เชื่อมโยงระหว่างทั้งสองด้าน
- จำกัด: สูงสุด 15 nodes และ 20 edges
"""
        response = self.invoke(prompt)
        return self._parse_json_response(response)
    
    def enrich_connections(self, nodes: List[dict], existing_edges: List[dict]) -> List[dict]:
        """Find additional connections between existing nodes"""
        node_names = [n.get('name', n.get('id', '')) for n in nodes[:30]]
        
        prompt = f"""
มี nodes เหล่านี้ในกราฟ:
{json.dumps(node_names, ensure_ascii=False)}

edges ที่มีอยู่แล้ว:
{json.dumps(existing_edges[:20], ensure_ascii=False)}

จงหา edges เพิ่มเติมที่น่าจะมีความสัมพันธ์กัน แต่ยังไม่ได้เชื่อมต่อ
ตอบเป็น JSON array ของ edges เท่านั้น:
[
  {{"source": "node_name_1", "target": "node_name_2", "relation": "leads_to|prevents|causes|uses|counters|related_to"}},
  ...
]

จำกัด: สูงสุด 10 edges ใหม่
"""
        response = self.invoke(prompt)
        new_edges = self._parse_json_array(response)
        return new_edges if new_edges else []
    
    def _parse_json_response(self, response: str) -> Tuple[List[dict], List[dict]]:
        """Parse JSON response, handling common LLM formatting issues"""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                nodes = data.get('nodes', [])
                edges = data.get('edges', [])
                return nodes, edges
        except json.JSONDecodeError:
            pass
        
        print(f"⚠️ Cartographer: Failed to parse JSON response")
        return [], []
    
    def _parse_json_array(self, response: str) -> Optional[List[dict]]:
        """Parse a JSON array from response"""
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return None
    
    def convert_to_schema(self, nodes: List[dict], edges: List[dict], source_book: str = None) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Convert raw dicts to schema objects"""
        schema_nodes = []
        schema_edges = []
        
        # Node type mapping
        type_map = {
            'concept': NodeType.CONCEPT,
            'technique': NodeType.TECHNIQUE,
            'risk': NodeType.RISK,
            'defense': NodeType.DEFENSE,
            'person': NodeType.PERSON,
            'outcome': NodeType.OUTCOME
        }
        
        # Edge type mapping
        edge_map = {
            'leads_to': EdgeType.LEADS_TO,
            'prevents': EdgeType.PREVENTS,
            'causes': EdgeType.CAUSES,
            'uses': EdgeType.USES,
            'counters': EdgeType.COUNTERS,
            'requires': EdgeType.REQUIRES,
            'related_to': EdgeType.RELATED_TO,
            'exploits': EdgeType.EXPLOITS
        }
        
        for node in nodes:
            try:
                node_type = type_map.get(node.get('type', 'concept'), NodeType.CONCEPT)
                schema_nodes.append(GraphNode(
                    id=node.get('id', node.get('name', '')).replace(' ', '_').lower(),
                    name=node.get('name', node.get('id', 'unnamed')),
                    type=node_type,
                    description=node.get('description'),
                    source_book=source_book
                ))
            except Exception as e:
                print(f"⚠️ Skipping invalid node: {e}")
        
        for edge in edges:
            try:
                edge_type = edge_map.get(edge.get('relation', 'related_to'), EdgeType.RELATED_TO)
                schema_edges.append(GraphEdge(
                    source=edge.get('source', '').replace(' ', '_').lower(),
                    target=edge.get('target', '').replace(' ', '_').lower(),
                    type=edge_type,
                    source_book=source_book
                ))
            except Exception as e:
                print(f"⚠️ Skipping invalid edge: {e}")
        
        return schema_nodes, schema_edges


# Singleton instance
cartographer = CartographerAgent()
