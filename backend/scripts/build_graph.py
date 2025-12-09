#!/usr/bin/env python3
# scripts/build_graph.py
"""
Main Pipeline Script: Build Knowledge Graph from JSONL books
Runs all 3 layers automatically
"""
import sys
import os
import time
import argparse

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.extractors import BaseGraphExtractor
from app.agents import debate_orchestrator, cartographer
from app.core import neo4j_client, settings
from app.core.schemas import GraphNode, GraphEdge


def run_layer1(data_dir: str = None):
    """Layer 1: Extract base graph from structured fields"""
    print("\n" + "="*60)
    print("🔵 LAYER 1: Base Graph Extraction (No API)")
    print("="*60)
    
    extractor = BaseGraphExtractor(data_dir)
    graph_data = extractor.extract_all()
    
    return extractor, graph_data


def run_layer2(extractor: BaseGraphExtractor, graph_data):
    """Layer 2: Enrich with AI connections"""
    print("\n" + "="*60)
    print("🟣 LAYER 2: AI Enrichment (Agent C)")
    print("="*60)
    
    # Get additional connections from Cartographer
    new_edges = debate_orchestrator.enrich_graph(
        graph_data.nodes,
        graph_data.edges
    )
    
    return new_edges


def run_layer3(extractor: BaseGraphExtractor, n_topics: int = 25):
    """Layer 3: Auto-debate top topics"""
    print("\n" + "="*60)
    print("🔴 LAYER 3: Auto-Debate Mode")
    print("="*60)
    
    # Get top concepts for debate
    top_concepts = extractor.get_top_concepts(n_topics)
    print(f"   Selected {len(top_concepts)} topics for debate")
    
    # Prepare topics with content
    topics = []
    for concept in top_concepts:
        content = concept.description or concept.name
        topics.append((concept.name, content))
    
    # Run debates
    debate_nodes, debate_edges = debate_orchestrator.auto_debate_top_topics(
        topics, 
        max_debates=n_topics
    )
    
    return debate_nodes, debate_edges


def ingest_to_neo4j(nodes, edges):
    """Ingest graph data to Neo4j"""
    print("\n" + "="*60)
    print("📥 Ingesting to Neo4j")
    print("="*60)
    
    # Create nodes
    node_count = neo4j_client.create_nodes_batch(nodes)
    print(f"   ✅ Created {node_count} nodes")
    
    # Create edges
    edge_count = neo4j_client.create_edges_batch(edges)
    print(f"   ✅ Created {edge_count} edges")
    
    # Get stats
    stats = neo4j_client.get_stats()
    print(f"\n   📊 Database Stats:")
    print(f"      Total nodes: {stats['nodes']}")
    print(f"      Total edges: {stats['edges']}")


def main():
    parser = argparse.ArgumentParser(description='Build Knowledge Graph from JSONL books')
    parser.add_argument('--layer', type=int, default=3, choices=[1, 2, 3],
                       help='Which layers to run (1=base only, 2=+enrichment, 3=+debate)')
    parser.add_argument('--topics', type=int, default=25,
                       help='Number of topics for auto-debate (Layer 3)')
    parser.add_argument('--data-dir', type=str, default=None,
                       help='Path to data directory with JSONL files')
    parser.add_argument('--no-ingest', action='store_true',
                       help='Skip Neo4j ingestion (dry run)')
    parser.add_argument('--clear-db', action='store_true',
                       help='Clear database before ingestion')
    
    args = parser.parse_args()
    
    print("\n🚀 Knowledge Graph Builder")
    print(f"   Layers: 1-{args.layer}")
    print(f"   Debate topics: {args.topics}")
    print(f"   API Keys available: {settings.api_key_manager.total_keys}")
    
    start_time = time.time()
    
    all_nodes = []
    all_edges = []
    
    # Layer 1: Base extraction (always runs)
    extractor, graph_data = run_layer1(args.data_dir)
    all_nodes.extend(graph_data.nodes)
    all_edges.extend(graph_data.edges)
    
    # Layer 2: Enrichment (if requested)
    if args.layer >= 2:
        try:
            new_edges = run_layer2(extractor, graph_data)
            all_edges.extend(new_edges)
        except Exception as e:
            print(f"⚠️ Layer 2 error: {e}")
    
    # Layer 3: Auto-debate (if requested)
    if args.layer >= 3:
        try:
            debate_nodes, debate_edges = run_layer3(extractor, args.topics)
            all_nodes.extend(debate_nodes)
            all_edges.extend(debate_edges)
        except Exception as e:
            print(f"⚠️ Layer 3 error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"   Total nodes: {len(all_nodes)}")
    print(f"   Total edges: {len(all_edges)}")
    print(f"   Time elapsed: {time.time() - start_time:.1f}s")
    
    # Ingest to Neo4j
    if not args.no_ingest:
        if args.clear_db:
            print("\n⚠️ Clearing database...")
            neo4j_client.clear_database()
        
        ingest_to_neo4j(all_nodes, all_edges)
    else:
        print("\n⏭️ Skipping Neo4j ingestion (dry run)")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
