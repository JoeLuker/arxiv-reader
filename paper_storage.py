import logging
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

import config
from arxiv_client import ArxivPaper

logger = logging.getLogger(__name__)

class PaperStorage:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        self._init_database()
        
        if logger.isEnabledFor(logging.DEBUG):
            assert self.db_path, "Database path must be specified"
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT,
                    authors TEXT,  -- JSON array
                    published TEXT,
                    updated TEXT,
                    categories TEXT,  -- JSON array
                    pdf_url TEXT,
                    relevance_score REAL,
                    added_date TEXT,
                    is_read BOOLEAN DEFAULT 0,
                    is_starred BOOLEAN DEFAULT 0,
                    notes TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_relevance_score ON papers(relevance_score)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_added_date ON papers(added_date)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_published ON papers(published)
            ''')
            
            logger.info("Database initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def store_paper(self, paper: ArxivPaper, relevance_score: float = 0.0) -> bool:
        """Store a paper in the database"""
        
        if logger.isEnabledFor(logging.DEBUG):
            assert isinstance(paper, ArxivPaper), f"Expected ArxivPaper, got {type(paper)}"
            assert 0 <= relevance_score <= 1, f"Relevance score must be 0-1, got {relevance_score}"
        
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO papers 
                    (id, title, summary, authors, published, updated, categories, 
                     pdf_url, relevance_score, added_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    paper.id,
                    paper.title,
                    paper.summary,
                    json.dumps(paper.authors),
                    paper.published,
                    paper.updated,
                    json.dumps(paper.categories),
                    paper.pdf_url,
                    relevance_score,
                    datetime.now().isoformat()
                ))
                
                logger.debug(f"Stored paper: {paper.id} with relevance {relevance_score:.3f}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to store paper {paper.id}: {e}")
            return False
    
    def get_papers(self, 
                   min_relevance: float = None,
                   limit: int = None,
                   order_by: str = 'relevance_score',
                   ascending: bool = False) -> List[Dict[str, Any]]:
        """Retrieve papers from database"""
        
        if min_relevance is None:
            min_relevance = config.MIN_RELEVANCE_SCORE
        
        order_direction = 'ASC' if ascending else 'DESC'
        
        query = f'''
            SELECT * FROM papers 
            WHERE relevance_score >= ?
            ORDER BY {order_by} {order_direction}
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (min_relevance,))
                rows = cursor.fetchall()
                
                papers = []
                for row in rows:
                    paper_dict = dict(row)
                    # Parse JSON fields
                    paper_dict['authors'] = json.loads(paper_dict['authors'])
                    paper_dict['categories'] = json.loads(paper_dict['categories'])
                    papers.append(paper_dict)
                
                logger.info(f"Retrieved {len(papers)} papers with relevance >= {min_relevance}")
                return papers
                
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve papers: {e}")
            return []
    
    def mark_as_read(self, paper_id: str) -> bool:
        """Mark a paper as read"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'UPDATE papers SET is_read = 1 WHERE id = ?',
                    (paper_id,)
                )
                
                if cursor.rowcount > 0:
                    logger.info(f"Marked paper {paper_id} as read")
                    return True
                else:
                    logger.warning(f"Paper {paper_id} not found")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to mark paper {paper_id} as read: {e}")
            return False
    
    def star_paper(self, paper_id: str, starred: bool = True) -> bool:
        """Star or unstar a paper"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'UPDATE papers SET is_starred = ? WHERE id = ?',
                    (starred, paper_id)
                )
                
                if cursor.rowcount > 0:
                    action = "starred" if starred else "unstarred"
                    logger.info(f"Paper {paper_id} {action}")
                    return True
                else:
                    logger.warning(f"Paper {paper_id} not found")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to update star status for paper {paper_id}: {e}")
            return False
    
    def add_notes(self, paper_id: str, notes: str) -> bool:
        """Add notes to a paper"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'UPDATE papers SET notes = ? WHERE id = ?',
                    (notes, paper_id)
                )
                
                if cursor.rowcount > 0:
                    logger.info(f"Added notes to paper {paper_id}")
                    return True
                else:
                    logger.warning(f"Paper {paper_id} not found")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to add notes to paper {paper_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self._get_connection() as conn:
                stats = {}
                
                # Total papers
                cursor = conn.execute('SELECT COUNT(*) FROM papers')
                stats['total_papers'] = cursor.fetchone()[0]
                
                # Read papers
                cursor = conn.execute('SELECT COUNT(*) FROM papers WHERE is_read = 1')
                stats['read_papers'] = cursor.fetchone()[0]
                
                # Starred papers
                cursor = conn.execute('SELECT COUNT(*) FROM papers WHERE is_starred = 1')
                stats['starred_papers'] = cursor.fetchone()[0]
                
                # Average relevance score
                cursor = conn.execute('SELECT AVG(relevance_score) FROM papers')
                avg_relevance = cursor.fetchone()[0]
                stats['avg_relevance'] = round(avg_relevance, 3) if avg_relevance else 0
                
                # High relevance papers (> 0.7)
                cursor = conn.execute('SELECT COUNT(*) FROM papers WHERE relevance_score > 0.7')
                stats['high_relevance_papers'] = cursor.fetchone()[0]
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}