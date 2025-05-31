import logging
import time
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

import config

logger = logging.getLogger(__name__)

class ArxivPaper:
    def __init__(self, entry: Dict[str, Any]):
        self.id = entry.get('id', '').split('/')[-1]
        self.title = entry.get('title', '').strip()
        self.summary = entry.get('summary', '').strip()
        self.authors = [author.get('name', '') for author in entry.get('authors', [])]
        self.published = entry.get('published', '')
        self.updated = entry.get('updated', '')
        self.categories = [tag.get('term', '') for tag in entry.get('tags', [])]
        self.pdf_url = self._extract_pdf_url(entry.get('links', []))
        
        if logger.isEnabledFor(logging.DEBUG):
            assert self.id, f"Paper ID should not be empty: {entry}"
            assert self.title, f"Paper title should not be empty: {entry}"
    
    def _extract_pdf_url(self, links: List[Dict[str, str]]) -> str:
        for link in links:
            if link.get('type') == 'application/pdf':
                return link.get('href', '')
        return ''
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'authors': self.authors,
            'published': self.published,
            'updated': self.updated,
            'categories': self.categories,
            'pdf_url': self.pdf_url
        }

class ArxivClient:
    def __init__(self):
        self.base_url = config.ARXIV_BASE_URL
        self.rate_limit_delay = config.RATE_LIMIT_DELAY
        self.last_request_time = 0
        
        if logger.isEnabledFor(logging.DEBUG):
            assert self.base_url, "ArXiv base URL must be configured"
            assert self.rate_limit_delay > 0, "Rate limit delay must be positive"
    
    def _rate_limit(self):
        """Ensure we don't exceed arXiv's rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_papers(self, 
                     query: str = '', 
                     categories: List[str] = None,
                     max_results: int = None,
                     start_date: Optional[datetime] = None) -> List[ArxivPaper]:
        """Search for papers on arXiv"""
        
        if max_results is None:
            max_results = config.MAX_RESULTS_PER_QUERY
            
        if categories is None:
            categories = config.SUBJECT_CATEGORIES
        
        # Build search query
        search_terms = []
        
        if query:
            search_terms.append(f'all:{query}')
        
        if categories:
            cat_query = ' OR '.join([f'cat:{cat}' for cat in categories])
            search_terms.append(f'({cat_query})')
        
        if start_date:
            date_str = start_date.strftime('%Y%m%d')
            search_terms.append(f'submittedDate:[{date_str}* TO *]')
        
        search_query = ' AND '.join(search_terms) if search_terms else 'cat:cs.AI'
        
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        logger.info(f"Searching arXiv with query: {search_query}")
        
        self._rate_limit()
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if logger.isEnabledFor(logging.DEBUG):
                assert 'entries' in feed, f"Feed should contain entries: {feed}"
            
            papers = []
            for entry in feed.entries:
                try:
                    paper = ArxivPaper(entry)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to parse paper entry: {e}")
                    continue
            
            logger.info(f"Found {len(papers)} papers")
            return papers
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            return []
    
    def get_recent_papers(self, days_back: int = None) -> List[ArxivPaper]:
        """Get papers from the last N days"""
        if days_back is None:
            days_back = config.DAYS_LOOKBACK
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        logger.info(f"Fetching papers from the last {days_back} days")
        
        return self.search_papers(start_date=start_date)