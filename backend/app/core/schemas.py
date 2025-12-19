# app/core/schemas.py
"""
Data schemas for Knowledge Graph
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph"""
    CONCEPT = "concept"           # แนวคิด/หลักการ
    TECHNIQUE = "technique"       # เทคนิค/วิธีการ
    RISK = "risk"                 # ความเสี่ยง/อันตราย
    DEFENSE = "defense"           # การป้องกัน
    PERSON = "person"             # บุคคล/ตัวละคร
    BOOK = "book"                 # หนังสือ
    CHAPTER = "chapter"           # บท
    OUTCOME = "outcome"           # ผลลัพธ์


class EdgeType(str, Enum):
    """Types of relationships between nodes"""
    LEADS_TO = "leads_to"                    # นำไปสู่
    PREVENTS = "prevents"                     # ป้องกัน
    CAUSES = "causes"                         # ทำให้เกิด
    COUNTERS = "counters"                     # ตอบโต้
    REQUIRES = "requires"                     # ต้องการ
    PART_OF = "part_of"                       # เป็นส่วนหนึ่งของ
    RELATED_TO = "related_to"                 # เกี่ยวข้องกับ
    MENTIONED_IN = "mentioned_in"             # กล่าวถึงใน
    USES = "uses"                             # ใช้
    EXPLOITS = "exploits"                     # ใช้ประโยชน์จาก
    ENABLES = "enables"                       # ทำให้สามารถ
    CONTRADICTS = "contradicts"               # ขัดแย้งกับ
    SUPPORTS = "supports"                     # สนับสนุน


class GraphNode(BaseModel):
    """A node in the knowledge graph"""
    id: str                              # Unique identifier
    name: str                            # Display name
    type: NodeType                       # Node type
    description: Optional[str] = None    # Description
    source_book: Optional[str] = None    # Source book title
    source_chapter: Optional[str] = None # Source chapter
    properties: Dict[str, Any] = {}      # Additional properties


class GraphEdge(BaseModel):
    """An edge (relationship) in the knowledge graph"""
    source: str                          # Source node ID
    target: str                          # Target node ID
    type: EdgeType                       # Relationship type
    weight: float = 1.0                  # Relationship strength
    description: Optional[str] = None    # Description of relationship
    source_book: Optional[str] = None    # Where this relationship was found


class GraphData(BaseModel):
    """Complete graph data structure"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class BookRecord(BaseModel):
    """A record from the JSONL book files"""
    book_title: str
    category: Optional[str] = None
    chapter_title: Optional[str] = None
    title: str
    description: Optional[str] = None
    content: str
    strategy_type: Optional[str] = None
    psychological_techniques: List[str] = []
    risk_factors: List[str] = []
    control_techniques: List[str] = []
    influence_level: Optional[str] = None
    adaptability_level: Optional[str] = None


class DebateMessage(BaseModel):
    """A message in a debate session"""
    agent: str                           # "predator" or "guardian"
    content: str                         # Message content
    referenced_concepts: List[str] = []  # Concepts mentioned


class DebateSession(BaseModel):
    """A debate session between agents"""
    topic: str
    messages: List[DebateMessage]
    extracted_nodes: List[GraphNode] = []
    extracted_edges: List[GraphEdge] = []
