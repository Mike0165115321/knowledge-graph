#!/usr/bin/env python3
"""
Run Enhanced Multi-Round Debate
2 Reader Agents debate + 1 Analyst extracts graph
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.enhanced_debate import get_enhanced_debate
from app.core.neo4j_client import neo4j_client


def main():
    print("="*60)
    print("🧠 Enhanced Multi-Round Debate System")
    print("="*60)
    
    # Initialize system
    debate_system = get_enhanced_debate(data_dir="data")
    
    # Define debate topics
    topics = [
        "การควบคุมคนอื่นโดยไม่ให้รู้ตัว",
        "จุดอ่อนทางจิตวิทยาของมนุษย์",
        "กลยุทธ์การสร้างอิทธิพล",
        "การป้องกันตัวจากการถูกจัดการ",
        "ศิลปะแห่งการโน้มน้าว",
    ]
    
    print(f"\n📋 Topics to debate: {len(topics)}")
    for i, t in enumerate(topics, 1):
        print(f"   {i}. {t}")
    
    # Run debates
    all_nodes, all_edges = debate_system.run_batch_debates(
        topics=topics,
        rounds=2,  # Each topic gets 2 rounds of back-and-forth
        delay=2.0
    )
    
    # Save to Neo4j
    if all_nodes or all_edges:
        print("\n💾 Saving to Neo4j...")
        
        saved_nodes = 0
        saved_edges = 0
        
        for node in all_nodes:
            try:
                neo4j_client.create_node(node)
                saved_nodes += 1
            except Exception as e:
                print(f"  ⚠️ Node error: {e}")
        
        for edge in all_edges:
            try:
                neo4j_client.create_edge(edge)
                saved_edges += 1
            except Exception as e:
                print(f"  ⚠️ Edge error: {e}")
        
        print(f"✅ Saved: {saved_nodes} nodes, {saved_edges} edges")
    
    # Show final stats
    stats = neo4j_client.get_stats()
    print(f"\n📊 Database Stats:")
    print(f"   Total nodes: {stats['nodes']}")
    print(f"   Total edges: {stats['edges']}")
    
    print("\n🎉 Done!")


if __name__ == "__main__":
    main()
