import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import pickle
import os

class VectorDatabase:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.schemas = []
        self.embeddings = None
        
    def create_embeddings(self, schema_data: List[Dict]) -> np.ndarray:
        """Create embeddings for schema text data"""
        self.schemas = schema_data
        texts = [schema['search_text'] for schema in schema_data]
        
        print(f"Creating embeddings for {len(texts)} schema descriptions...")
        embeddings = self.model.encode(texts)
        self.embeddings = embeddings
        
        return embeddings
    
    def build_faiss_index(self, embeddings: np.ndarray):
        """Build FAISS index from embeddings"""
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype('float32'))
        
        print(f"Built FAISS index with {self.index.ntotal} vectors, dimension: {dimension}")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Dict, float]]:
        """Search for most relevant schemas based on query"""
        if self.index is None:
            raise ValueError("Index not built. Call build_faiss_index first.")
        
        # Encode query
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.schemas):
                results.append((self.schemas[idx], float(score)))
        
        return results
    
    def save_index(self, index_path: str, metadata_path: str):
        """Save FAISS index and metadata"""
        faiss.write_index(self.index, index_path)
        
        metadata = {
            'schemas': self.schemas,
            'embeddings': self.embeddings.tolist() if self.embeddings is not None else None
        }
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        print(f"Saved index to {index_path} and metadata to {metadata_path}")
    
    def load_index(self, index_path: str, metadata_path: str):
        """Load FAISS index and metadata"""
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError("Index or metadata file not found")
        
        self.index = faiss.read_index(index_path)
        
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        self.schemas = metadata['schemas']
        if metadata['embeddings']:
            self.embeddings = np.array(metadata['embeddings'])
        
        print(f"Loaded index with {self.index.ntotal} vectors")
    
    def get_relevant_tables(self, query: str, top_k: int = 3) -> List[str]:
        """Get list of relevant table names for a query"""
        results = self.search(query, top_k)
        table_names = [result[0]['table_name'] for result in results]
        return table_names
    
    def get_search_results_with_scores(self, query: str, top_k: int = 3) -> List[Dict]:
        """Get detailed search results with scores for display"""
        results = self.search(query, top_k)
        
        search_results = []
        for schema, score in results:
            search_results.append({
                'table_name': schema['table_name'],
                'relevance_score': round(score, 4),
                'schema_preview': schema['search_text'][:200] + "..." if len(schema['search_text']) > 200 else schema['search_text']
            })
        
        return search_results