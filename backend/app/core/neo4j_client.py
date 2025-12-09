# app/core/neo4j_client.py
"""
Neo4j database client for Knowledge Graph operations
"""
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from .config import settings
from .schemas import GraphNode, GraphEdge, NodeType, EdgeType


class Neo4jClient:
    """Client for Neo4j database operations"""
    
    def __init__(self):
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            # Verify connection
            self.driver.verify_connectivity()
            print("✅ Connected to Neo4j")
        except Exception as e:
            print(f"⚠️ Neo4j connection failed: {e}")
            self.driver = None
    
    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
    
    @contextmanager
    def session(self):
        """Get a database session"""
        if not self.driver:
            self._connect()
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()
    
    # ==================== Node Operations ====================
    
    def create_node(self, node: GraphNode) -> bool:
        """Create a single node"""
        query = """
        MERGE (n:Node {id: $id})
        SET n.name = $name,
            n.type = $type,
            n.description = $description,
            n.source_book = $source_book,
            n.source_chapter = $source_chapter,
            n.properties = $properties
        RETURN n
        """
        try:
            with self.session() as session:
                session.run(query, 
                    id=node.id,
                    name=node.name,
                    type=node.type.value,
                    description=node.description,
                    source_book=node.source_book,
                    source_chapter=node.source_chapter,
                    properties=str(node.properties)
                )
            return True
        except Exception as e:
            print(f"Error creating node: {e}")
            return False
    
    def create_nodes_batch(self, nodes: List[GraphNode]) -> int:
        """Create multiple nodes in batch"""
        query = """
        UNWIND $nodes AS node
        MERGE (n:Node {id: node.id})
        SET n.name = node.name,
            n.type = node.type,
            n.description = node.description,
            n.source_book = node.source_book,
            n.source_chapter = node.source_chapter
        """
        try:
            with self.session() as session:
                nodes_data = [
                    {
                        "id": n.id,
                        "name": n.name,
                        "type": n.type.value,
                        "description": n.description,
                        "source_book": n.source_book,
                        "source_chapter": n.source_chapter
                    }
                    for n in nodes
                ]
                session.run(query, nodes=nodes_data)
            return len(nodes)
        except Exception as e:
            print(f"Error creating nodes batch: {e}")
            return 0
    
    # ==================== Edge Operations ====================
    
    def create_edge(self, edge: GraphEdge) -> bool:
        """Create a single edge"""
        query = """
        MATCH (a:Node {id: $source})
        MATCH (b:Node {id: $target})
        MERGE (a)-[r:RELATES {type: $type}]->(b)
        SET r.weight = $weight,
            r.description = $description,
            r.source_book = $source_book
        """
        try:
            with self.session() as session:
                session.run(query,
                    source=edge.source,
                    target=edge.target,
                    type=edge.type.value,
                    weight=edge.weight,
                    description=edge.description,
                    source_book=edge.source_book
                )
            return True
        except Exception as e:
            print(f"Error creating edge: {e}")
            return False
    
    def create_edges_batch(self, edges: List[GraphEdge]) -> int:
        """Create multiple edges in batch"""
        query = """
        UNWIND $edges AS edge
        MATCH (a:Node {id: edge.source})
        MATCH (b:Node {id: edge.target})
        MERGE (a)-[r:RELATES {type: edge.type}]->(b)
        SET r.weight = edge.weight,
            r.description = edge.description,
            r.source_book = edge.source_book
        """
        try:
            with self.session() as session:
                edges_data = [
                    {
                        "source": e.source,
                        "target": e.target,
                        "type": e.type.value,
                        "weight": e.weight,
                        "description": e.description,
                        "source_book": e.source_book
                    }
                    for e in edges
                ]
                session.run(query, edges=edges_data)
            return len(edges)
        except Exception as e:
            print(f"Error creating edges batch: {e}")
            return 0
    
    # ==================== Query Operations ====================
    
    def get_all_graph_data(self) -> Dict[str, Any]:
        """Get all nodes and edges for visualization"""
        nodes_query = "MATCH (n:Node) RETURN n"
        edges_query = "MATCH (a:Node)-[r:RELATES]->(b:Node) RETURN a.id AS source, b.id AS target, r.type AS type, r.weight AS weight"
        
        nodes = []
        edges = []
        
        try:
            with self.session() as session:
                # Get nodes
                result = session.run(nodes_query)
                for record in result:
                    node = record["n"]
                    nodes.append({
                        "id": node["id"],
                        "name": node.get("name", node["id"]),
                        "type": node.get("type", "concept"),
                        "description": node.get("description")
                    })
                
                # Get edges
                result = session.run(edges_query)
                for record in result:
                    edges.append({
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "weight": record.get("weight", 1.0)
                    })
        except Exception as e:
            print(f"Error getting graph data: {e}")
        
        return {"nodes": nodes, "edges": edges}
    
    def search_nodes(self, query: str, limit: int = 20) -> List[Dict]:
        """Search nodes by name or description"""
        cypher = """
        MATCH (n:Node)
        WHERE toLower(n.name) CONTAINS toLower($query) 
           OR toLower(n.description) CONTAINS toLower($query)
        RETURN n
        LIMIT $limit
        """
        nodes = []
        try:
            with self.session() as session:
                result = session.run(cypher, query=query, limit=limit)
                for record in result:
                    node = record["n"]
                    nodes.append({
                        "id": node["id"],
                        "name": node.get("name"),
                        "type": node.get("type"),
                        "description": node.get("description")
                    })
        except Exception as e:
            print(f"Search error: {e}")
        
        return nodes
    
    def get_node_neighbors(self, node_id: str) -> Dict[str, Any]:
        """Get a node and its immediate neighbors"""
        query = """
        MATCH (n:Node {id: $id})
        OPTIONAL MATCH (n)-[r]-(neighbor:Node)
        RETURN n, collect(DISTINCT {node: neighbor, rel: r}) AS neighbors
        """
        try:
            with self.session() as session:
                result = session.run(query, id=node_id)
                record = result.single()
                if record:
                    node = record["n"]
                    neighbors = record["neighbors"]
                    return {
                        "node": {
                            "id": node["id"],
                            "name": node.get("name"),
                            "type": node.get("type"),
                            "description": node.get("description")
                        },
                        "neighbors": [
                            {
                                "id": n["node"]["id"],
                                "name": n["node"].get("name"),
                                "relation": n["rel"].get("type") if n["rel"] else None
                            }
                            for n in neighbors if n["node"]
                        ]
                    }
        except Exception as e:
            print(f"Error getting neighbors: {e}")
        
        return None
    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution!)"""
        query = "MATCH (n) DETACH DELETE n"
        try:
            with self.session() as session:
                session.run(query)
            print("🗑️ Database cleared")
        except Exception as e:
            print(f"Error clearing database: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            with self.session() as session:
                nodes_count = session.run("MATCH (n:Node) RETURN count(n) AS count").single()["count"]
                edges_count = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) AS count").single()["count"]
                return {"nodes": nodes_count, "edges": edges_count}
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"nodes": 0, "edges": 0}


# Singleton instance
neo4j_client = Neo4jClient()
