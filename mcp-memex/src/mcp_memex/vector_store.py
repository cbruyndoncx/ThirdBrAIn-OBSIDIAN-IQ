import json
import os
from pathlib import Path
from datetime import datetime

from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
from pymilvus.milvus_client import IndexParams
from voyageai.embeddings_utils import get_embedding

from mcp_memex.notes import get_frontmatter
from .chunking import MarkdownSection, split_markdown_sections

MODEL_NAME = "voyage-3"  # Which embedding model to use
DIMENSION = 1024  # Dimension of vector embedding
COLLECTION_NAME = "memex"

class VectorDB:
    def __init__(self, index_dir: Path):
        """Initialize Milvus vector store with Voyage embeddings"""
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        db_path = self.index_dir / "index.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Connecting to Milvus at {db_path}")
        
        self.client = MilvusClient(str(db_path))

        # Initialize Voyage embedding function
        self.voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not self.voyage_api_key:
            raise ValueError("VOYAGE_API_KEY environment variable is required")
        
        # Create collection if it doesn't exist
        if not self.client.has_collection(COLLECTION_NAME):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="path", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=30),
                FieldSchema(name="index", dtype=DataType.INT64),
                FieldSchema(name="level", dtype=DataType.INT64),
                FieldSchema(name="header", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
                FieldSchema(name="parent_index", dtype=DataType.INT64),
                FieldSchema(name="child_indices", dtype=DataType.VARCHAR, max_length=200)
            ]
            schema = CollectionSchema(fields)
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                schema=schema
            )
            
            # Create index immediately after collection creation
            self.client.create_index(
                collection_name=COLLECTION_NAME,
                index_params=IndexParams(
                    field_name="vector",
                    index_type="FLAT",
                    metric_type="COSINE",
                    params={"nprobe": 10}
                )
            )
            self.client.load_collection(COLLECTION_NAME)

        else:
            # Always load the collection when initializing
            self.client.load_collection(COLLECTION_NAME)

    def add_document(self, content: str, path: Path) -> None:
        """Add or update a document in the vector store"""

        metadata, remaining_content = get_frontmatter(content)
            
        timestamp = datetime.utcnow().isoformat()
        
        # Chunk the content
        chunks = split_markdown_sections(remaining_content, str(path))
        
        # Get embeddings for all chunks
        chunk_texts = [chunk.content for chunk in chunks]
        vectors = [get_embedding(text, model=MODEL_NAME, api_key=self.voyage_api_key) for text in chunk_texts]
        
        # Delete existing entries for this path if any
        self.client.delete(
            collection_name=COLLECTION_NAME,
            filter=f'path == "{str(path)}"'
        )
        
        # Prepare data for Milvus
        data = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            data.append({
                "id": hash(f"{path}_{i}"),  # Create unique ID from path and index
                "vector": vector, 
                "title": path.stem,
                "path": str(path),
                "timestamp": timestamp,
                "index": i,
                "level": chunk.level,
                "header": chunk.header,
                "content": chunk.content,
                "parent_index": chunk.parent_index,
                "child_indices": json.dumps(chunk.child_indices)  # Milvus doesn't support list fields
            })
        
        # Insert into Milvus
        self.client.insert(
            collection_name=COLLECTION_NAME,
            data=data
        )
        
        # Remove the try-except block for index creation since we handle it in __init__
        # The index will already exist

    def has_document(self, url: str) -> bool:
        """Check if a document exists in the store"""
        results = self.client.query(
            collection_name=COLLECTION_NAME,
            filter=f'url == "{url}"',
            output_fields=["url"],
            limit=1
        )
        return len(results) > 0

    def search(self, query: str, n_results: int = 20) -> list[dict]:
        """Search for relevant content chunks"""
        # Get query embedding using Voyage
        query_vector = get_embedding(query, model=MODEL_NAME, api_key=self.voyage_api_key)
        
        # Search in Milvus
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            data=[query_vector],
            limit=n_results,
            output_fields=["title", "path", "timestamp", "index", "level", "header", "content", "parent_index", "child_indices"],
            params={"nprobe": 10}  # Number of clusters to search
        )
        
        # Format results
        search_results = []
        for result in results[0]:  # First query's results
            metadata = result["entity"]
            search_results.append({
                "metadata": MarkdownSection(
                    path=metadata["path"],
                    index=metadata["index"],
                    level=metadata["level"],
                    header=metadata["header"],
                    content=metadata["content"],
                    parent_index=metadata["parent_index"],
                    child_indices=json.loads(metadata["child_indices"]),
                ),
                "title": metadata["title"],
                "timestamp": metadata["timestamp"],
                "similarity": 1 - result["distance"]  # Convert distance to similarity
            })
            
        return search_results
    
    def save_db(self):
        """Save the database to disk"""
        self.client.flush(COLLECTION_NAME)
