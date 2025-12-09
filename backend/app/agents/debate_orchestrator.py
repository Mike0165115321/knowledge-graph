# app/agents/debate_orchestrator.py
"""
Debate Orchestrator - Manages debates between Predator and Guardian
Auto-selects top topics and orchestrates the debate flow
"""
import time
from typing import List, Tuple
from .predator import predator
from .guardian import guardian
from .cartographer import cartographer
from ..core.schemas import GraphNode, GraphEdge, DebateSession, DebateMessage


class DebateOrchestrator:
    """
    Orchestrates debates between Predator and Guardian agents
    Extracts knowledge graph from debate insights
    """
    
    def __init__(self, delay_between_calls: float = 1.0):
        self.predator = predator
        self.guardian = guardian
        self.cartographer = cartographer
        self.delay = delay_between_calls  # Prevent rate limiting
        self.debate_history: List[DebateSession] = []
    
    def debate_topic(self, topic: str, content: str) -> DebateSession:
        """
        Run a full debate on a topic
        Returns: DebateSession with messages and extracted graph
        """
        print(f"\n🔥 Starting debate on: {topic}")
        
        messages = []
        
        # 1. Predator opens with offensive analysis
        print("  🔴 Predator analyzing...")
        predator_msg = self.predator.analyze_offensive(content, topic)
        messages.append(DebateMessage(
            agent="predator",
            content=predator_msg
        ))
        time.sleep(self.delay)
        
        # 2. Guardian responds with defensive analysis
        print("  🔵 Guardian responding...")
        guardian_msg = self.guardian.counter_argument(predator_msg, topic)
        messages.append(DebateMessage(
            agent="guardian",
            content=guardian_msg
        ))
        time.sleep(self.delay)
        
        # 3. Cartographer extracts knowledge graph
        print("  🗺️ Cartographer extracting graph...")
        raw_nodes, raw_edges = self.cartographer.extract_from_debate(
            topic, predator_msg, guardian_msg
        )
        
        nodes, edges = self.cartographer.convert_to_schema(
            raw_nodes, raw_edges, source_book=f"Debate: {topic}"
        )
        
        session = DebateSession(
            topic=topic,
            messages=messages,
            extracted_nodes=nodes,
            extracted_edges=edges
        )
        
        self.debate_history.append(session)
        
        print(f"  ✅ Extracted: {len(nodes)} nodes, {len(edges)} edges")
        
        return session
    
    def auto_debate_top_topics(
        self, 
        topics: List[Tuple[str, str]], 
        max_debates: int = 25
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Automatically debate the top N topics
        
        Args:
            topics: List of (topic_name, related_content) tuples
            max_debates: Maximum number of debates to run
        
        Returns:
            Tuple of (all_nodes, all_edges) from all debates
        """
        print(f"\n🚀 Auto-Debate Mode: {min(len(topics), max_debates)} topics")
        
        all_nodes = []
        all_edges = []
        
        for i, (topic, content) in enumerate(topics[:max_debates]):
            print(f"\n[{i+1}/{min(len(topics), max_debates)}]")
            
            try:
                session = self.debate_topic(topic, content)
                all_nodes.extend(session.extracted_nodes)
                all_edges.extend(session.extracted_edges)
                
                # Longer delay between debates to avoid rate limits
                time.sleep(self.delay * 2)
                
            except Exception as e:
                print(f"  ❌ Error debating '{topic}': {e}")
                continue
        
        print(f"\n🎉 Auto-Debate Complete!")
        print(f"   Total nodes: {len(all_nodes)}")
        print(f"   Total edges: {len(all_edges)}")
        
        return all_nodes, all_edges
    
    def enrich_graph(
        self, 
        existing_nodes: List[GraphNode],
        existing_edges: List[GraphEdge]
    ) -> List[GraphEdge]:
        """
        Use Cartographer to find additional connections
        """
        print("\n🔍 Enriching graph with additional connections...")
        
        # Convert to dicts for the cartographer
        node_dicts = [{"id": n.id, "name": n.name, "type": n.type.value} for n in existing_nodes[:50]]
        edge_dicts = [{"source": e.source, "target": e.target, "relation": e.type.value} for e in existing_edges[:30]]
        
        new_edge_dicts = self.cartographer.enrich_connections(node_dicts, edge_dicts)
        
        if new_edge_dicts:
            _, new_edges = self.cartographer.convert_to_schema([], new_edge_dicts)
            print(f"   Found {len(new_edges)} new connections")
            return new_edges
        
        return []
    
    def get_debate_summary(self) -> dict:
        """Get summary of all debates"""
        return {
            "total_debates": len(self.debate_history),
            "topics": [s.topic for s in self.debate_history],
            "total_nodes_extracted": sum(len(s.extracted_nodes) for s in self.debate_history),
            "total_edges_extracted": sum(len(s.extracted_edges) for s in self.debate_history)
        }


# Singleton instance
debate_orchestrator = DebateOrchestrator()
