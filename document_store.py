#!/usr/bin/env python3
"""
Document Store Integration for ArXiv Papers

Integrates with:
- MinIO for PDF storage (S3-compatible)
- MongoDB for metadata and relationships
- Elasticsearch for full-text search
- Apache Tika for PDF text extraction
"""

import os
import logging
import requests
import hashlib
from typing import List, Dict, Any, Optional
from io import BytesIO
from datetime import datetime
import json

# Document store libraries
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
import zincsearch_sdk
from zincsearch_sdk.api import document, index, search
from zincsearch_sdk.model.meta_zinc_query import MetaZincQuery
import tika
from tika import parser as tika_parser

# Configure Tika
tika.TikaClientOnly = True
os.environ['TIKA_SERVER_ENDPOINT'] = 'http://localhost:9998'

logger = logging.getLogger(__name__)


class DocumentStore:
    """Manages PDF storage and full-text search for ArXiv papers"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize document store connections"""
        self.config = config or self._get_default_config()
        
        # Initialize MinIO client
        self.minio_client = Minio(
            self.config['minio']['endpoint'],
            access_key=self.config['minio']['access_key'],
            secret_key=self.config['minio']['secret_key'],
            secure=self.config['minio'].get('secure', False)
        )
        self.bucket_name = self.config['minio']['bucket']
        
        # Initialize MongoDB client
        mongo_uri = f"mongodb://{self.config['mongodb']['username']}:{self.config['mongodb']['password']}@{self.config['mongodb']['host']}:{self.config['mongodb']['port']}"
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[self.config['mongodb']['database']]
        
        # Initialize ZincSearch client
        zinc_config = zincsearch_sdk.Configuration(
            host=f"http://{self.config['zincsearch']['host']}:{self.config['zincsearch']['port']}",
            username=self.config['zincsearch']['username'],
            password=self.config['zincsearch']['password']
        )
        self.zinc_api_client = zincsearch_sdk.ApiClient(zinc_config)
        self.zinc_document_api = document.Document(self.zinc_api_client)
        self.zinc_index_api = index.Index(self.zinc_api_client)
        self.zinc_search_api = search.Search(self.zinc_api_client)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        # Ensure ZincSearch index exists
        self._ensure_index_exists()
        
        logger.info("Document store initialized successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration from environment or defaults"""
        return {
            'minio': {
                'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
                'access_key': os.getenv('MINIO_ROOT_USER', 'minioadmin'),
                'secret_key': os.getenv('MINIO_ROOT_PASSWORD', 'minioadmin123'),
                'bucket': 'arxiv-pdfs',
                'secure': False
            },
            'mongodb': {
                'host': os.getenv('MONGO_HOST', 'localhost'),
                'port': int(os.getenv('MONGO_PORT', '27017')),
                'username': os.getenv('MONGO_USER', 'arxivadmin'),
                'password': os.getenv('MONGO_PASSWORD', 'arxivpass123'),
                'database': 'arxiv_papers'
            },
            'zincsearch': {
                'host': os.getenv('ZINC_HOST', 'localhost'),
                'port': int(os.getenv('ZINC_PORT', '4080')),
                'username': os.getenv('ZINC_USER', 'arxivadmin'),
                'password': os.getenv('ZINC_PASSWORD', 'zincsearch123')
            },
            'tika': {
                'endpoint': os.getenv('TIKA_ENDPOINT', 'http://localhost:9998')
            }
        }
    
    def _ensure_bucket_exists(self):
        """Ensure MinIO bucket exists"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
    
    def _ensure_index_exists(self):
        """Ensure ZincSearch index exists"""
        try:
            # ZincSearch creates indices automatically when documents are indexed
            # We'll let it auto-create for simplicity
            logger.debug("ZincSearch will auto-create index on first document")
        except Exception as e:
            logger.error(f"Error ensuring ZincSearch index: {e}")
    
    def download_and_store_pdf(self, arxiv_id: str, pdf_url: str) -> Dict[str, Any]:
        """Download PDF from ArXiv and store in MinIO"""
        try:
            logger.info(f"Downloading PDF for {arxiv_id} from {pdf_url}")
            
            # Download PDF
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Calculate file hash
            hasher = hashlib.sha256()
            pdf_content = response.content
            hasher.update(pdf_content)
            file_hash = hasher.hexdigest()
            
            # Store in MinIO
            object_name = f"{arxiv_id}.pdf"
            self.minio_client.put_object(
                self.bucket_name,
                object_name,
                data=BytesIO(pdf_content),
                length=len(pdf_content),
                content_type='application/pdf'
            )
            
            # Extract text using Tika
            logger.info(f"Extracting text from {arxiv_id}")
            parsed = tika_parser.from_buffer(pdf_content)
            full_text = parsed.get('content', '')
            metadata = parsed.get('metadata', {})
            
            # Store metadata in MongoDB
            pdf_doc = {
                'arxiv_id': arxiv_id,
                'pdf_url': pdf_url,
                'object_name': object_name,
                'file_size': len(pdf_content),
                'file_hash': file_hash,
                'download_date': datetime.utcnow(),
                'tika_metadata': metadata,
                'status': 'downloaded'
            }
            
            self.db.pdfs.update_one(
                {'arxiv_id': arxiv_id},
                {'$set': pdf_doc},
                upsert=True
            )
            
            # Store full text in MongoDB for backup
            self.db.full_text.update_one(
                {'arxiv_id': arxiv_id},
                {'$set': {
                    'arxiv_id': arxiv_id,
                    'content': full_text,
                    'extraction_date': datetime.utcnow()
                }},
                upsert=True
            )
            
            # Index in ZincSearch for search
            self._index_document(arxiv_id, full_text, metadata)
            
            logger.info(f"Successfully stored PDF and extracted text for {arxiv_id}")
            
            return {
                'success': True,
                'arxiv_id': arxiv_id,
                'file_size': len(pdf_content),
                'text_length': len(full_text),
                'object_name': object_name
            }
            
        except Exception as e:
            logger.error(f"Error downloading/storing PDF for {arxiv_id}: {e}")
            return {
                'success': False,
                'arxiv_id': arxiv_id,
                'error': str(e)
            }
    
    def _index_document(self, arxiv_id: str, full_text: str, metadata: Dict[str, Any]):
        """Index document in ZincSearch"""
        try:
            # Get paper metadata from MongoDB first
            paper = self.db.papers.find_one({'arxiv_id': arxiv_id})
            if not paper:
                # Try looking by 'id' field (from SQLite migration)
                paper = self.db.papers.find_one({'id': arxiv_id})
            
            # If not in MongoDB, try SQLite database for backward compatibility
            if not paper:
                try:
                    import sqlite3
                    import config
                    conn = sqlite3.connect(config.DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("SELECT * FROM papers WHERE id = ?", (arxiv_id,))
                    row = cursor.fetchone()
                    if row:
                        paper = dict(row)
                        paper['authors'] = json.loads(paper['authors'])
                        paper['categories'] = json.loads(paper['categories'])
                        paper['abstract'] = paper.get('summary', '')
                    conn.close()
                except Exception as e:
                    logger.warning(f"Could not fetch from SQLite: {e}")
            
            doc = {
                'arxiv_id': arxiv_id,
                'title': paper.get('title', '') if paper else '',
                'abstract': paper.get('abstract', '') if paper else '',
                'authors': ' '.join(paper.get('authors', [])) if paper and isinstance(paper.get('authors'), list) else '',
                'categories': ' '.join(paper.get('categories', [])) if paper and isinstance(paper.get('categories'), list) else '',
                'full_text': full_text,
                'pdf_metadata': json.dumps(metadata),
                'indexed_date': datetime.utcnow().isoformat()
            }
            
            # ZincSearch bulk format
            bulk_data = f'{{"index": {{"_index": "arxiv-papers", "_id": "{arxiv_id}"}}}}\n{json.dumps(doc)}\n'
            
            self.zinc_document_api.bulk(query=bulk_data)
            
            logger.info(f"Indexed {arxiv_id} in ZincSearch")
            
        except Exception as e:
            logger.error(f"Error indexing document {arxiv_id}: {e}")
    
    def search_full_text(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """Search full text of papers using ZincSearch"""
        try:
            # Use direct HTTP request since the SDK has issues with the search format
            import requests
            import base64
            
            auth_string = f"{self.config['zincsearch']['username']}:{self.config['zincsearch']['password']}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            search_data = {
                "search_type": "querystring",
                "query": {
                    "term": query
                },
                "from": 0,
                "size": size
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth_b64}"
            }
            
            url = f"http://{self.config['zincsearch']['host']}:{self.config['zincsearch']['port']}/api/arxiv-papers/_search"
            response = requests.post(url, json=search_data, headers=headers)
            response.raise_for_status()
            
            search_results = response.json()
            
            results = []
            if 'hits' in search_results and 'hits' in search_results['hits']:
                for hit in search_results['hits']['hits']:
                    source = hit.get('_source', {})
                    result = {
                        'arxiv_id': source.get('arxiv_id', ''),
                        'title': source.get('title', ''),
                        'score': hit.get('_score', 0),
                        'highlights': []  # Can be added later if needed
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching full text: {e}")
            return []
    
    def get_pdf_content(self, arxiv_id: str) -> Optional[bytes]:
        """Retrieve PDF content from MinIO"""
        try:
            object_name = f"{arxiv_id}.pdf"
            response = self.minio_client.get_object(self.bucket_name, object_name)
            pdf_content = response.read()
            response.close()
            response.release_conn()
            return pdf_content
        except S3Error as e:
            logger.error(f"Error retrieving PDF for {arxiv_id}: {e}")
            return None
    
    def get_full_text(self, arxiv_id: str) -> Optional[str]:
        """Get extracted full text for a paper"""
        doc = self.db.full_text.find_one({'arxiv_id': arxiv_id})
        return doc.get('content') if doc else None
    
    def get_download_status(self, arxiv_ids: List[str]) -> Dict[str, bool]:
        """Check which papers have been downloaded"""
        downloaded = self.db.pdfs.find(
            {'arxiv_id': {'$in': arxiv_ids}},
            {'arxiv_id': 1}
        )
        downloaded_ids = {doc['arxiv_id'] for doc in downloaded}
        
        return {arxiv_id: arxiv_id in downloaded_ids for arxiv_id in arxiv_ids}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            # Get MinIO stats
            objects = self.minio_client.list_objects(self.bucket_name, recursive=True)
            total_size = 0
            pdf_count = 0
            
            for obj in objects:
                if obj.object_name.endswith('.pdf'):
                    pdf_count += 1
                    total_size += obj.size
            
            # Get MongoDB stats
            mongo_stats = {
                'papers_count': self.db.papers.count_documents({}),
                'pdfs_count': self.db.pdfs.count_documents({}),
                'full_text_count': self.db.full_text.count_documents({})
            }
            
            # Get ZincSearch stats
            try:
                zinc_response = self.zinc_index_api.get_mapping(index='arxiv-papers')
                zinc_count = zinc_response.mapping.get('num_docs', 0) if zinc_response else 0
            except Exception:
                zinc_count = 0
            
            return {
                'minio': {
                    'pdf_count': pdf_count,
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                },
                'mongodb': mongo_stats,
                'zincsearch': {
                    'indexed_documents': zinc_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}


def migrate_from_sqlite(sqlite_db_path: str, doc_store: DocumentStore):
    """Migrate existing SQLite data to document store"""
    import sqlite3
    
    conn = sqlite3.connect(sqlite_db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("SELECT * FROM papers")
    papers = [dict(row) for row in cursor.fetchall()]
    
    logger.info(f"Migrating {len(papers)} papers from SQLite")
    
    for paper in papers:
        # Parse JSON fields
        paper['authors'] = json.loads(paper['authors'])
        paper['categories'] = json.loads(paper['categories'])
        
        # Store in MongoDB
        doc_store.db.papers.update_one(
            {'arxiv_id': paper['id']},
            {'$set': {
                'arxiv_id': paper['id'],
                'title': paper['title'],
                'abstract': paper['summary'],
                'authors': paper['authors'],
                'published_date': paper['published'],
                'updated_date': paper['updated'],
                'categories': paper['categories'],
                'pdf_url': paper['pdf_url'],
                'relevance_score': paper['relevance_score'],
                'added_date': paper['added_date'],
                'is_read': bool(paper.get('is_read', 0)),
                'is_starred': bool(paper.get('is_starred', 0)),
                'notes': paper.get('notes', '')
            }},
            upsert=True
        )
    
    conn.close()
    logger.info("Migration completed")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    doc_store = DocumentStore()
    stats = doc_store.get_storage_stats()
    print("Storage Statistics:", json.dumps(stats, indent=2))