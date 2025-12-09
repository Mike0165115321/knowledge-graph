# app/extractors/base_extractor.py
"""
Layer 1: Base Graph Extractor
Extracts nodes and edges directly from structured JSONL fields (NO API calls needed)
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Generator, Tuple
from ..core.schemas import (
    GraphNode, GraphEdge, BookRecord, GraphData,
    NodeType, EdgeType
)


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug for node IDs"""
    # Remove special characters, keep Thai and English
    text = text.lower().strip()
    text = re.sub(r'[^\w\sก-๙]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text[:100]  # Limit length


class BaseGraphExtractor:
    """
    Layer 1: Extract base graph from structured JSONL data
    No API calls - purely extracts from existing fields
    """
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(__file__), "../../data"
        )
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
    
    def load_jsonl_files(self) -> Generator[BookRecord, None, None]:
        """Load all JSONL files from data directory"""
        data_path = Path(self.data_dir)
        
        for jsonl_file in data_path.glob("*.jsonl"):
            print(f"📖 Loading: {jsonl_file.name}")
            
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            yield BookRecord(**data)
                        except json.JSONDecodeError as e:
                            print(f"  ⚠️ JSON error line {line_num}: {e}")
                        except Exception as e:
                            print(f"  ⚠️ Parse error line {line_num}: {e}")
            except Exception as e:
                print(f"  ❌ File error: {e}")
    
    def _add_node(self, node: GraphNode):
        """Add node to collection (deduplicates by ID)"""
        if node.id not in self.nodes:
            self.nodes[node.id] = node
    
    def _add_edge(self, edge: GraphEdge):
        """Add edge to collection"""
        # Check for duplicate edges
        for existing in self.edges:
            if (existing.source == edge.source and 
                existing.target == edge.target and
                existing.type == edge.type):
                return
        self.edges.append(edge)
    
    def extract_from_record(self, record: BookRecord) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Extract nodes and edges from a single record"""
        nodes = []
        edges = []
        
        book_id = slugify(record.book_title)
        chapter_id = slugify(record.chapter_title) if record.chapter_title else None
        title_id = slugify(record.title)
        
        # 1. Create Book Node
        book_node = GraphNode(
            id=book_id,
            name=record.book_title,
            type=NodeType.BOOK,
            description=record.category
        )
        nodes.append(book_node)
        
        # 2. Create Chapter Node (if exists)
        if chapter_id:
            chapter_node = GraphNode(
                id=f"{book_id}_{chapter_id}",
                name=record.chapter_title,
                type=NodeType.CHAPTER,
                source_book=record.book_title
            )
            nodes.append(chapter_node)
            
            # Book -> Chapter edge
            edges.append(GraphEdge(
                source=book_id,
                target=chapter_node.id,
                type=EdgeType.PART_OF,
                source_book=record.book_title
            ))
        
        # 3. Create Concept Node from title
        concept_node = GraphNode(
            id=f"concept_{title_id}",
            name=record.title,
            type=NodeType.CONCEPT,
            description=record.description,
            source_book=record.book_title,
            source_chapter=record.chapter_title
        )
        nodes.append(concept_node)
        
        # Link to chapter or book
        if chapter_id:
            edges.append(GraphEdge(
                source=concept_node.id,
                target=f"{book_id}_{chapter_id}",
                type=EdgeType.MENTIONED_IN,
                source_book=record.book_title
            ))
        
        # 4. Extract Technique Nodes
        for technique in record.psychological_techniques:
            tech_id = f"tech_{slugify(technique)}"
            tech_node = GraphNode(
                id=tech_id,
                name=technique,
                type=NodeType.TECHNIQUE,
                source_book=record.book_title
            )
            nodes.append(tech_node)
            
            # Concept -> Technique edge
            edges.append(GraphEdge(
                source=concept_node.id,
                target=tech_id,
                type=EdgeType.USES,
                source_book=record.book_title
            ))
        
        # 5. Extract Risk Nodes
        for risk in record.risk_factors:
            risk_id = f"risk_{slugify(risk)}"
            risk_node = GraphNode(
                id=risk_id,
                name=risk,
                type=NodeType.RISK,
                source_book=record.book_title
            )
            nodes.append(risk_node)
            
            # Concept -> Risk edge
            edges.append(GraphEdge(
                source=concept_node.id,
                target=risk_id,
                type=EdgeType.CAUSES,
                source_book=record.book_title
            ))
        
        # 6. Extract Defense/Control Nodes
        for defense in record.control_techniques:
            def_id = f"defense_{slugify(defense)}"
            def_node = GraphNode(
                id=def_id,
                name=defense,
                type=NodeType.DEFENSE,
                source_book=record.book_title
            )
            nodes.append(def_node)
            
            # Defense prevents risks
            for risk in record.risk_factors:
                risk_id = f"risk_{slugify(risk)}"
                edges.append(GraphEdge(
                    source=def_id,
                    target=risk_id,
                    type=EdgeType.PREVENTS,
                    source_book=record.book_title
                ))
        
        # 7. Create Outcome Node from influence_level
        if record.influence_level:
            outcome_id = f"outcome_{slugify(record.influence_level)}"
            outcome_node = GraphNode(
                id=outcome_id,
                name=f"อิทธิพล{record.influence_level}",
                type=NodeType.OUTCOME
            )
            nodes.append(outcome_node)
            
            edges.append(GraphEdge(
                source=concept_node.id,
                target=outcome_id,
                type=EdgeType.LEADS_TO,
                source_book=record.book_title
            ))
        
        return nodes, edges
    
    def extract_all(self) -> GraphData:
        """Extract base graph from all JSONL files"""
        print("🔄 Starting Layer 1: Base Graph Extraction...")
        
        record_count = 0
        for record in self.load_jsonl_files():
            nodes, edges = self.extract_from_record(record)
            
            for node in nodes:
                self._add_node(node)
            for edge in edges:
                self._add_edge(edge)
            
            record_count += 1
        
        print(f"\n✅ Layer 1 Complete!")
        print(f"   📊 Records processed: {record_count}")
        print(f"   🔵 Nodes extracted: {len(self.nodes)}")
        print(f"   🔗 Edges extracted: {len(self.edges)}")
        
        return GraphData(
            nodes=list(self.nodes.values()),
            edges=self.edges
        )
    
    def get_top_concepts(self, n: int = 25) -> List[GraphNode]:
        """Get top N concepts for debate selection"""
        concepts = [
            node for node in self.nodes.values() 
            if node.type == NodeType.CONCEPT
        ]
        
        # Sort by number of edges connected
        edge_counts = {}
        for edge in self.edges:
            edge_counts[edge.source] = edge_counts.get(edge.source, 0) + 1
            edge_counts[edge.target] = edge_counts.get(edge.target, 0) + 1
        
        concepts.sort(key=lambda c: edge_counts.get(c.id, 0), reverse=True)
        
        return concepts[:n]
    
    def export_to_jsonl(self, filepath: str):
        """Export graph data to JSONL file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            # Export nodes
            for node in self.nodes.values():
                f.write(json.dumps({
                    "type": "node",
                    "data": node.model_dump()
                }, ensure_ascii=False) + "\n")
            
            # Export edges
            for edge in self.edges:
                f.write(json.dumps({
                    "type": "edge",
                    "data": edge.model_dump()
                }, ensure_ascii=False) + "\n")
        
        print(f"✅ Exported to {filepath}")


# Convenience function
def extract_base_graph(data_dir: str = None) -> GraphData:
    """Extract base graph from JSONL files"""
    extractor = BaseGraphExtractor(data_dir)
    return extractor.extract_all()
