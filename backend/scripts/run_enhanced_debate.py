#!/usr/bin/env python3
"""
Auto Debate System - Batch Run with Delay
อ่านหัวข้อจาก topics.txt และรัน debate อัตโนมัติ
"""
import sys
import os
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.enhanced_debate import get_enhanced_debate
from app.core.neo4j_client import neo4j_client

# ============================================
# Configuration
# ============================================
DEFAULT_TOPICS_FILE = "scripts/topics.txt"
DEFAULT_DELAY_BETWEEN_TOPICS = 30  # seconds
DEFAULT_DELAY_BETWEEN_ROUNDS = 3   # seconds
DEFAULT_ROUNDS = 2
DELAY_AFTER_ERROR = 60  # seconds

COMPLETED_LOG = "scripts/completed_topics.txt"


def load_topics(topics_file: str) -> list:
    """Load topics from txt file (one per line, # = comment)"""
    topics = []
    path = Path(topics_file)
    
    if not path.exists():
        print(f"❌ File not found: {topics_file}")
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                topics.append(line)
    
    return topics


def load_completed() -> set:
    """Load list of completed topics"""
    completed = set()
    path = Path(COMPLETED_LOG)
    
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                completed.add(line.strip())
    
    return completed


def save_completed(topic: str):
    """Append topic to completed log"""
    with open(COMPLETED_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{topic}\n")


def format_eta(seconds: float) -> str:
    """Format seconds to readable time"""
    if seconds < 60:
        return f"{int(seconds)} วินาที"
    elif seconds < 3600:
        return f"{int(seconds/60)} นาที"
    else:
        return f"{seconds/3600:.1f} ชั่วโมง"


def run_auto_debate(
    topics_file: str = DEFAULT_TOPICS_FILE,
    delay_between_topics: int = DEFAULT_DELAY_BETWEEN_TOPICS,
    rounds: int = DEFAULT_ROUNDS,
    resume: bool = True
):
    """
    Run automated debates on all topics
    
    Args:
        topics_file: Path to topics.txt
        delay_between_topics: Seconds to wait between each topic
        rounds: Number of debate rounds per topic
        resume: Skip already completed topics
    """
    print("=" * 60)
    print("🤖 AUTO DEBATE SYSTEM")
    print("=" * 60)
    print(f"  📄 Topics file: {topics_file}")
    print(f"  ⏱️  Delay between topics: {delay_between_topics}s")
    print(f"  🔄 Rounds per topic: {rounds}")
    print(f"  🔁 Resume mode: {'ON' if resume else 'OFF'}")
    print("=" * 60)
    
    # Load topics
    all_topics = load_topics(topics_file)
    if not all_topics:
        print("❌ No topics found!")
        return
    
    # Filter completed if resume mode
    completed = load_completed() if resume else set()
    topics = [t for t in all_topics if t not in completed]
    
    print(f"\n📋 Topics: {len(all_topics)} total, {len(completed)} completed, {len(topics)} remaining")
    
    if not topics:
        print("✅ All topics already completed!")
        return
    
    # Initialize system
    print("\n🚀 Initializing AI System...")
    debate_system = get_enhanced_debate(data_dir="data")
    
    # Calculate ETA
    est_time_per_topic = (rounds * 2 * 15) + delay_between_topics  # rough estimate
    total_est_time = len(topics) * est_time_per_topic
    print(f"⏳ Estimated total time: {format_eta(total_est_time)}")
    
    # Stats
    total_nodes = 0
    total_edges = 0
    start_time = datetime.now()
    
    # Run debates
    for i, topic in enumerate(topics):
        current = i + 1
        remaining = len(topics) - current
        eta_seconds = remaining * est_time_per_topic
        
        print(f"\n{'='*60}")
        print(f"📌 [{current}/{len(topics)}] {topic}")
        print(f"   ⏳ ETA: {format_eta(eta_seconds)}")
        print(f"{'='*60}")
        
        try:
            result = debate_system.run_debate(
                topic=topic,
                rounds=rounds,
                delay=DEFAULT_DELAY_BETWEEN_ROUNDS
            )
            
            nodes = result['nodes']
            edges = result['edges']
            
            # Save to Neo4j
            print(f"\n💾 Saving to Neo4j...")
            saved_n, saved_e = 0, 0
            
            for node in nodes:
                try:
                    neo4j_client.create_node(node)
                    saved_n += 1
                except Exception as e:
                    print(f"  ⚠️ Node error: {e}")
            
            for edge in edges:
                try:
                    neo4j_client.create_edge(edge)
                    saved_e += 1
                except Exception as e:
                    print(f"  ⚠️ Edge error: {e}")
            
            total_nodes += saved_n
            total_edges += saved_e
            
            print(f"✅ Saved: {saved_n} nodes, {saved_e} edges")
            
            # Mark completed
            save_completed(topic)
            
            # Delay before next topic
            if remaining > 0:
                print(f"\n⏸️  Waiting {delay_between_topics}s before next topic...")
                time.sleep(delay_between_topics)
            
        except Exception as e:
            print(f"❌ Error on '{topic}': {e}")
            print(f"⏸️  Cooling down for {DELAY_AFTER_ERROR}s...")
            time.sleep(DELAY_AFTER_ERROR)
            continue
    
    # Final stats
    elapsed = datetime.now() - start_time
    
    print(f"\n{'='*60}")
    print("🎉 AUTO DEBATE COMPLETE!")
    print(f"{'='*60}")
    print(f"  ✅ Topics completed: {len(topics)}")
    print(f"  📊 Total nodes: {total_nodes}")
    print(f"  🔗 Total edges: {total_edges}")
    print(f"  ⏱️  Time elapsed: {elapsed}")
    
    # Database stats
    try:
        stats = neo4j_client.get_stats()
        print(f"\n📊 Database Total:")
        print(f"   Nodes: {stats['nodes']}")
        print(f"   Edges: {stats['edges']}")
    except Exception:
        pass
    
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Auto Debate System")
    parser.add_argument(
        '--file', '-f',
        default=DEFAULT_TOPICS_FILE,
        help=f'Topics file path (default: {DEFAULT_TOPICS_FILE})'
    )
    parser.add_argument(
        '--delay', '-d',
        type=int,
        default=DEFAULT_DELAY_BETWEEN_TOPICS,
        help=f'Delay between topics in seconds (default: {DEFAULT_DELAY_BETWEEN_TOPICS})'
    )
    parser.add_argument(
        '--rounds', '-r',
        type=int,
        default=DEFAULT_ROUNDS,
        help=f'Rounds per topic (default: {DEFAULT_ROUNDS})'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Disable resume mode (re-run completed topics)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Clear completed topics log and start fresh'
    )
    
    args = parser.parse_args()
    
    # Reset if requested
    if args.reset:
        path = Path(COMPLETED_LOG)
        if path.exists():
            path.unlink()
            print("🗑️  Cleared completed topics log")
    
    run_auto_debate(
        topics_file=args.file,
        delay_between_topics=args.delay,
        rounds=args.rounds,
        resume=not args.no_resume
    )


if __name__ == "__main__":
    main()
