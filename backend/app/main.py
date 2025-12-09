# app/main.py
"""
FastAPI Backend for Knowledge Graph API
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel

from .core import neo4j_client, settings
from .agents import debate_orchestrator


# ==================== FastAPI App ====================

app = FastAPI(
    title="Project Sun Tzu - Knowledge Graph API",
    description="API for Psychology & Strategy Knowledge Graph",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Response Models ====================

class GraphResponse(BaseModel):
    nodes: List[dict]
    edges: List[dict]
    stats: dict


class NodeResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str]


class DebateRequest(BaseModel):
    topic: str
    content: Optional[str] = None


class DebateResponse(BaseModel):
    topic: str
    predator_message: str
    guardian_message: str
    new_nodes: int
    new_edges: int


class SearchResponse(BaseModel):
    results: List[dict]
    count: int


# ==================== Endpoints ====================

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "Project Sun Tzu API"}


@app.get("/api/graph", response_model=GraphResponse)
async def get_graph():
    """Get full knowledge graph data for visualization"""
    try:
        data = neo4j_client.get_all_graph_data()
        stats = neo4j_client.get_stats()
        return GraphResponse(
            nodes=data["nodes"],
            edges=data["edges"],
            stats=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search", response_model=SearchResponse)
async def search_nodes(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, le=100, description="Max results")
):
    """Search nodes by name or description"""
    try:
        results = neo4j_client.search_nodes(q, limit)
        return SearchResponse(results=results, count=len(results))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/node/{node_id}")
async def get_node_details(node_id: str):
    """Get a node and its neighbors"""
    try:
        data = neo4j_client.get_node_neighbors(node_id)
        if not data:
            raise HTTPException(status_code=404, detail="Node not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/debate", response_model=DebateResponse)
async def trigger_debate(request: DebateRequest):
    """Trigger a debate on a specific topic (uses API credits)"""
    try:
        content = request.content or request.topic
        
        session = debate_orchestrator.debate_topic(
            topic=request.topic,
            content=content
        )
        
        # Ingest new nodes/edges to database
        if session.extracted_nodes:
            neo4j_client.create_nodes_batch(session.extracted_nodes)
        if session.extracted_edges:
            neo4j_client.create_edges_batch(session.extracted_edges)
        
        return DebateResponse(
            topic=request.topic,
            predator_message=session.messages[0].content if session.messages else "",
            guardian_message=session.messages[1].content if len(session.messages) > 1 else "",
            new_nodes=len(session.extracted_nodes),
            new_edges=len(session.extracted_edges)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        stats = neo4j_client.get_stats()
        debate_stats = debate_orchestrator.get_debate_summary()
        return {
            "database": stats,
            "debates": debate_stats,
            "api_keys": settings.api_key_manager.total_keys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
