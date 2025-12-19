# app/rag/embedding_rag.py
"""
Embedding-based RAG using local models
Supports: BAAI-bge-m3, intfloat-multilingual-e5-large
"""
import json
import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    print("⚠️ sentence-transformers or faiss not installed")


class EmbeddingRAG:
    """RAG system using local embedding models and FAISS vector store"""
    
    def __init__(
        self,
        model_path: str = "/home/mikedev/MyModels/Model-RAG/intfloat-multilingual-e5-large",
        data_dir: str = "data",
        cache_dir: str = ".rag_cache"
    ):
        self.model_path = model_path
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product (cosine sim after norm)
        self.documents: List[dict] = []
        self.embeddings: Optional[np.ndarray] = None
        
        self._initialized = False
    
    def initialize(self, force_rebuild: bool = False):
        """Load model and build/load index"""
        if self._initialized and not force_rebuild:
            return
        
        if not HAS_EMBEDDINGS:
            raise RuntimeError("sentence-transformers and faiss-cpu are required")
        
        print(f"🚀 Initializing Embedding RAG...")
        
        # Load embedding model
        print(f"  📦 Loading model: {Path(self.model_path).name}")
        self.model = SentenceTransformer(self.model_path)
        print(f"     Dimension: {self.model.get_sentence_embedding_dimension()}")
        
        # Check cache
        index_path = self.cache_dir / "faiss.index"
        docs_path = self.cache_dir / "documents.pkl"
        
        if not force_rebuild and index_path.exists() and docs_path.exists():
            print(f"  💾 Loading cached index...")
            self._load_cache()
        else:
            print(f"  📚 Building index from documents...")
            self._build_index()
        
        self._initialized = True
        print(f"  ✅ RAG ready! {len(self.documents)} documents indexed")
    
    def _load_documents(self) -> List[dict]:
        """Load all JSONL documents"""
        documents = []
        
        for jsonl_file in self.data_dir.glob("*.jsonl"):
            book_name = jsonl_file.stem
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            entry = json.loads(line)
                            
                            # Create document with searchable text
                            title = entry.get('title', '') or entry.get('name', '')
                            content = entry.get('content', '') or entry.get('description', '')
                            
                            if title or content:
                                text = f"{title}\n{content}".strip()
                                documents.append({
                                    'id': f"{book_name}_{line_num}",
                                    'book': book_name,
                                    'title': title,
                                    'content': content[:2000],  # Limit length
                                    'text': text[:1000],  # For embedding
                                    'metadata': entry
                                })
            except Exception as e:
                print(f"  ⚠️ Error loading {jsonl_file.name}: {e}")
        
        return documents
    
    def _build_index(self):
        """Build FAISS index from documents"""
        # Load documents
        self.documents = self._load_documents()
        print(f"     Loaded {len(self.documents)} documents")
        
        if not self.documents:
            print("     ⚠️ No documents found!")
            return
        
        # Create embeddings
        print(f"     Creating embeddings...")
        texts = [doc['text'] for doc in self.documents]
        
        # Batch encode for efficiency
        self.embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # For cosine similarity
        )
        
        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product = cosine after normalization
        self.index.add(self.embeddings.astype('float32'))
        
        # Save cache
        self._save_cache()
        print(f"     Index built: {self.index.ntotal} vectors")
    
    def _save_cache(self):
        """Save index and documents to cache"""
        faiss.write_index(self.index, str(self.cache_dir / "faiss.index"))
        with open(self.cache_dir / "documents.pkl", 'wb') as f:
            pickle.dump(self.documents, f)
        np.save(self.cache_dir / "embeddings.npy", self.embeddings)
    
    def _load_cache(self):
        """Load index and documents from cache"""
        self.index = faiss.read_index(str(self.cache_dir / "faiss.index"))
        with open(self.cache_dir / "documents.pkl", 'rb') as f:
            self.documents = pickle.load(f)
        self.embeddings = np.load(self.cache_dir / "embeddings.npy")
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        min_score: float = 0.3
    ) -> List[Dict]:
        """Search for relevant documents"""
        if not self._initialized:
            self.initialize()
        
        if not self.index or not self.documents:
            return []
        
        # Encode query
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or score < min_score:
                continue
            
            doc = self.documents[idx]
            results.append({
                'score': float(score),
                'book': doc['book'],
                'title': doc['title'],
                'content': doc['content'],
                'id': doc['id']
            })
        
        return results
    
    def get_context(self, query: str, top_k: int = 3) -> str:
        """Get formatted context for LLM prompt"""
        results = self.search(query, top_k=top_k)
        
        if not results:
            return "ไม่พบข้อมูลที่เกี่ยวข้อง"
        
        context_parts = []
        for r in results:
            context_parts.append(
                f"📚 จาก {r['book']} - {r['title']}:\n{r['content']}"
            )
        
        return "\n\n---\n\n".join(context_parts)


# Singleton instance
_rag_instance: Optional[EmbeddingRAG] = None

def get_embedding_rag(
    model_path: str = "/home/mikedev/MyModels/Model-RAG/intfloat-multilingual-e5-large",
    data_dir: str = "data"
) -> EmbeddingRAG:
    """Get or create singleton RAG instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = EmbeddingRAG(model_path=model_path, data_dir=data_dir)
    return _rag_instance
