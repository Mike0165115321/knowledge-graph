import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.neo4j_client import neo4j_client

def reset_database():
    print("🗑️  Resetting Neo4j Database...")
    try:
        # Delete all nodes and relationships
        neo4j_client.query("MATCH (n) DETACH DELETE n")
        print("✅ Database cleared successfully!")
        
        # Verify
        count = neo4j_client.query("MATCH (n) RETURN count(n) as count")[0]['count']
        print(f"   Nodes remaining: {count}")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    confirm = input("⚠️  WARNING: This will DELETE ALL DATA in Neo4j. Are you sure? (y/N): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("❌ Operation cancelled.")
