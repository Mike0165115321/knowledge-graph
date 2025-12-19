import os
import sys
import json
import uuid
import hashlib

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.neo4j_client import neo4j_client
from app.core.schemas import GraphNode, NodeType

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

def generate_id(text):
    return hashlib.md5(text.encode()).hexdigest()

def import_base_data():
    print(f"📂 Scanning data directory: {DATA_DIR}")
    
    if not os.path.exists(DATA_DIR):
        print("❌ Data directory not found!")
        return

    jsonl_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.jsonl')]
    print(f"📚 Found {len(jsonl_files)} JSONL files.")
    
    all_nodes = []
    
    for filename in jsonl_files:
        filepath = os.path.join(DATA_DIR, filename)
        book_title = filename.replace('.jsonl', '')
        
        # Create Book Node
        book_id = f"book_{generate_id(book_title)}"
        all_nodes.append(GraphNode(
            id=book_id,
            name=book_title,
            type=NodeType.BOOK,
            description=f"Initial import from {filename}",
            properties={"filename": filename}
        ))
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    
                    # Create Chapter/Section Node
                    title = data.get('title', 'Untitled')
                    content = data.get('content', '')
                    
                    node_id = f"section_{generate_id(book_title + title)}"
                    
                    # Determine type (heuristic)
                    node_type = NodeType.CHAPTER
                    if len(content) < 500 and "เทคนิค" in title:
                        node_type = NodeType.TECHNIQUE
                    elif "แนวคิด" in title or "Concept" in title:
                        node_type = NodeType.CONCEPT
                        
                    all_nodes.append(GraphNode(
                        id=node_id,
                        name=title,
                        type=node_type,
                        description=content[:200] + "...",  # Truncate for description
                        source_book=book_title
                    ))
                    
                    # Note: We are creating unconnected nodes for now. 
                    # Relationships will be built by the Debate Agent later.
                    
        except Exception as e:
            print(f"⚠️ Error reading {filename}: {e}")
            
    print(f"🧠 Importing {len(all_nodes)} initial nodes...")
    neo4j_client.create_nodes_batch(all_nodes)
    print("✅ Import complete!")

if __name__ == "__main__":
    import_base_data()
