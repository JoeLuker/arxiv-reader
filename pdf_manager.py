#!/usr/bin/env python3
"""
PDF Manager - Integration layer between the ArXiv reader and document store
"""

import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from paper_storage import PaperStorage
from document_store import DocumentStore, migrate_from_sqlite
from arxiv_client import ArxivPaper
import config

logger = logging.getLogger(__name__)


class PDFManager:
    """Manages PDF downloads and integrates with the document store"""
    
    def __init__(self, storage: PaperStorage = None, doc_store: DocumentStore = None):
        self.storage = storage or PaperStorage()
        self.doc_store = doc_store or DocumentStore()
        
    def download_papers_by_relevance(self, min_relevance: float = 0.7, limit: int = None) -> Dict[str, Any]:
        """Download PDFs for high-relevance papers"""
        papers = self.storage.get_papers(min_relevance=min_relevance, limit=limit)
        
        results = {
            'total': len(papers),
            'downloaded': 0,
            'failed': 0,
            'already_downloaded': 0,
            'papers': []
        }
        
        # Check which papers are already downloaded
        arxiv_ids = [p['id'] for p in papers]
        download_status = self.doc_store.get_download_status(arxiv_ids)
        
        for paper in papers:
            arxiv_id = paper['id']
            
            if download_status.get(arxiv_id, False):
                logger.info(f"Paper {arxiv_id} already downloaded, skipping")
                results['already_downloaded'] += 1
                continue
                
            logger.info(f"Downloading PDF for {arxiv_id}: {paper['title'][:60]}...")
            
            result = self.doc_store.download_and_store_pdf(
                arxiv_id=arxiv_id,
                pdf_url=paper['pdf_url']
            )
            
            if result['success']:
                results['downloaded'] += 1
                logger.info(f"Successfully downloaded {arxiv_id}")
            else:
                results['failed'] += 1
                logger.error(f"Failed to download {arxiv_id}: {result.get('error')}")
                
            results['papers'].append({
                'arxiv_id': arxiv_id,
                'title': paper['title'],
                'relevance_score': paper['relevance_score'],
                'result': result
            })
            
        return results
    
    def download_specific_papers(self, arxiv_ids: List[str]) -> Dict[str, Any]:
        """Download PDFs for specific papers by ID"""
        results = {
            'total': len(arxiv_ids),
            'downloaded': 0,
            'failed': 0,
            'not_found': 0,
            'papers': []
        }
        
        for arxiv_id in arxiv_ids:
            # Get paper from storage
            papers = self.storage.get_papers()
            paper = next((p for p in papers if p['id'] == arxiv_id), None)
            
            if not paper:
                logger.warning(f"Paper {arxiv_id} not found in database")
                results['not_found'] += 1
                continue
                
            result = self.doc_store.download_and_store_pdf(
                arxiv_id=arxiv_id,
                pdf_url=paper['pdf_url']
            )
            
            if result['success']:
                results['downloaded'] += 1
            else:
                results['failed'] += 1
                
            results['papers'].append({
                'arxiv_id': arxiv_id,
                'title': paper['title'],
                'result': result
            })
            
        return results
    
    def search_full_text(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """Search full text of downloaded papers"""
        return self.doc_store.search_full_text(query, size)
    
    def get_paper_with_text(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Get paper metadata along with extracted full text"""
        papers = self.storage.get_papers()
        paper = next((p for p in papers if p['id'] == arxiv_id), None)
        
        if not paper:
            return None
            
        full_text = self.doc_store.get_full_text(arxiv_id)
        
        return {
            **paper,
            'full_text': full_text,
            'has_pdf': full_text is not None
        }
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get combined statistics from storage and document store"""
        storage_stats = self.storage.get_stats()
        doc_stats = self.doc_store.get_storage_stats()
        
        # Calculate download percentage
        total_papers = storage_stats.get('total_papers', 0)
        downloaded_papers = doc_stats.get('mongodb', {}).get('pdfs_count', 0)
        
        return {
            'storage': storage_stats,
            'documents': doc_stats,
            'download_percentage': round(downloaded_papers / total_papers * 100, 1) if total_papers > 0 else 0
        }


def main():
    """Command line interface for PDF management"""
    parser = argparse.ArgumentParser(description='Manage PDFs for ArXiv papers')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download PDFs')
    download_parser.add_argument('--min-relevance', type=float, default=0.7,
                               help='Minimum relevance score (default: 0.7)')
    download_parser.add_argument('--limit', type=int, help='Maximum papers to download')
    download_parser.add_argument('--arxiv-ids', nargs='+', help='Specific ArXiv IDs to download')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search full text')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--size', type=int, default=10, help='Number of results')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate from SQLite to document store')
    migrate_parser.add_argument('--sqlite-path', default='arxiv_papers.db',
                              help='Path to SQLite database')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize manager
    manager = PDFManager()
    
    if args.command == 'download':
        if args.arxiv_ids:
            results = manager.download_specific_papers(args.arxiv_ids)
        else:
            results = manager.download_papers_by_relevance(
                min_relevance=args.min_relevance,
                limit=args.limit
            )
        
        print(f"\nDownload Summary:")
        print(f"Total papers: {results['total']}")
        print(f"Downloaded: {results['downloaded']}")
        print(f"Failed: {results['failed']}")
        if 'already_downloaded' in results:
            print(f"Already downloaded: {results['already_downloaded']}")
            
    elif args.command == 'search':
        results = manager.search_full_text(args.query, args.size)
        
        if results:
            print(f"\nFound {len(results)} results for '{args.query}':\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   ArXiv ID: {result['arxiv_id']}")
                print(f"   Score: {result['score']:.2f}")
                if result['highlights']:
                    print("   Highlights:")
                    for highlight in result['highlights'][:2]:
                        print(f"   - ...{highlight.strip()}...")
                print()
        else:
            print(f"No results found for '{args.query}'")
            
    elif args.command == 'stats':
        stats = manager.get_download_stats()
        
        print("\n=== ArXiv Paper Statistics ===")
        print(f"\nStorage Statistics:")
        print(f"  Total papers: {stats['storage']['total_papers']}")
        print(f"  Read papers: {stats['storage']['read_papers']}")
        print(f"  Starred papers: {stats['storage']['starred_papers']}")
        print(f"  High relevance (>0.7): {stats['storage']['high_relevance_papers']}")
        print(f"  Average relevance: {stats['storage']['avg_relevance']}")
        
        print(f"\nDocument Store Statistics:")
        print(f"  PDFs downloaded: {stats['documents']['mongodb']['pdfs_count']}")
        print(f"  Download percentage: {stats['download_percentage']}%")
        print(f"  Total storage: {stats['documents']['minio']['total_size_mb']:.1f} MB")
        print(f"  Indexed documents: {stats['documents']['elasticsearch']['indexed_documents']}")
        
    elif args.command == 'migrate':
        print(f"Migrating from {args.sqlite_path} to document store...")
        migrate_from_sqlite(args.sqlite_path, manager.doc_store)
        print("Migration completed!")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()