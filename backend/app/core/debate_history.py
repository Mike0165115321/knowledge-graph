"""
Debate History Storage using SQLite
เก็บประวัติการสนทนาระหว่าง AI agents
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "debates.db"


def get_connection():
    """Get database connection"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            rounds INTEGER DEFAULT 2,
            node_count INTEGER DEFAULT 0,
            edge_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debate_id INTEGER NOT NULL,
            agent TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_order INTEGER DEFAULT 0,
            FOREIGN KEY (debate_id) REFERENCES debates(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_debate 
        ON messages(debate_id)
    """)
    
    conn.commit()
    conn.close()


def save_debate(
    topic: str, 
    messages: List[Dict],
    rounds: int = 2,
    node_count: int = 0,
    edge_count: int = 0
) -> int:
    """
    Save a debate session
    
    Args:
        topic: Debate topic
        messages: List of {"agent": "...", "content": "..."}
        rounds: Number of rounds
        node_count: Nodes extracted
        edge_count: Edges extracted
    
    Returns:
        debate_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Insert debate
    cursor.execute("""
        INSERT INTO debates (topic, rounds, node_count, edge_count)
        VALUES (?, ?, ?, ?)
    """, (topic, rounds, node_count, edge_count))
    
    debate_id = cursor.lastrowid
    
    # Insert messages
    for i, msg in enumerate(messages):
        cursor.execute("""
            INSERT INTO messages (debate_id, agent, content, msg_order)
            VALUES (?, ?, ?, ?)
        """, (debate_id, msg.get('agent', ''), msg.get('content', ''), i))
    
    conn.commit()
    conn.close()
    
    return debate_id


def get_all_debates() -> List[Dict]:
    """Get all debates (summary only)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, topic, rounds, node_count, edge_count, created_at
        FROM debates
        ORDER BY created_at DESC
    """)
    
    debates = []
    for row in cursor.fetchall():
        debates.append({
            "id": row["id"],
            "topic": row["topic"],
            "rounds": row["rounds"],
            "node_count": row["node_count"],
            "edge_count": row["edge_count"],
            "created_at": row["created_at"]
        })
    
    conn.close()
    return debates


def get_debate(debate_id: int) -> Optional[Dict]:
    """Get a debate with all messages"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get debate info
    cursor.execute("""
        SELECT id, topic, rounds, node_count, edge_count, created_at
        FROM debates WHERE id = ?
    """, (debate_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    debate = {
        "id": row["id"],
        "topic": row["topic"],
        "rounds": row["rounds"],
        "node_count": row["node_count"],
        "edge_count": row["edge_count"],
        "created_at": row["created_at"],
        "messages": []
    }
    
    # Get messages
    cursor.execute("""
        SELECT agent, content, msg_order
        FROM messages WHERE debate_id = ?
        ORDER BY msg_order
    """, (debate_id,))
    
    for msg_row in cursor.fetchall():
        debate["messages"].append({
            "agent": msg_row["agent"],
            "content": msg_row["content"]
        })
    
    conn.close()
    return debate


def search_debates(query: str) -> List[Dict]:
    """Search debates by topic"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, topic, rounds, node_count, edge_count, created_at
        FROM debates
        WHERE topic LIKE ?
        ORDER BY created_at DESC
    """, (f"%{query}%",))
    
    debates = []
    for row in cursor.fetchall():
        debates.append({
            "id": row["id"],
            "topic": row["topic"],
            "rounds": row["rounds"],
            "node_count": row["node_count"],
            "edge_count": row["edge_count"],
            "created_at": row["created_at"]
        })
    
    conn.close()
    return debates


def delete_debate(debate_id: int):
    """Delete a debate and its messages"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages WHERE debate_id = ?", (debate_id,))
    cursor.execute("DELETE FROM debates WHERE id = ?", (debate_id,))
    
    conn.commit()
    conn.close()


def get_stats() -> Dict:
    """Get database statistics"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM debates")
    debate_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    message_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(node_count), SUM(edge_count) FROM debates")
    row = cursor.fetchone()
    
    conn.close()
    
    return {
        "debates": debate_count,
        "messages": message_count,
        "total_nodes": row[0] or 0,
        "total_edges": row[1] or 0
    }


# Initialize on import
init_db()
