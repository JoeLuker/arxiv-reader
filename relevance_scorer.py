import logging
import re
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from arxiv_client import ArxivPaper

logger = logging.getLogger(__name__)

class RelevanceScorer:
    def __init__(self, keywords: List[str] = None):
        self.keywords = keywords or config.RELEVANCE_KEYWORDS
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
        
        # Create keyword reference vector
        self.keyword_text = ' '.join(self.keywords)
        
        if logger.isEnabledFor(logging.DEBUG):
            assert self.keywords, "Keywords list should not be empty"
            assert len(self.keywords) > 0, f"Need at least one keyword, got {len(self.keywords)}"
        
        logger.info(f"Initialized relevance scorer with {len(self.keywords)} keywords")
    
    def score_paper(self, paper: ArxivPaper) -> float:
        """Calculate relevance score for a paper (0-1)"""
        
        if logger.isEnabledFor(logging.DEBUG):
            assert isinstance(paper, ArxivPaper), f"Expected ArxivPaper, got {type(paper)}"
        
        # Combine title and abstract for scoring
        text_content = f"{paper.title} {paper.summary}".lower()
        
        if not text_content.strip():
            logger.warning(f"Empty content for paper {paper.id}")
            return 0.0
        
        # Calculate different scoring components
        keyword_score = self._calculate_keyword_score(text_content)
        category_score = self._calculate_category_score(paper.categories)
        semantic_score = self._calculate_semantic_score(text_content)
        
        # Weighted combination of scores
        weights = {
            'keyword': 0.4,
            'category': 0.3,
            'semantic': 0.3
        }
        
        final_score = (
            weights['keyword'] * keyword_score +
            weights['category'] * category_score +
            weights['semantic'] * semantic_score
        )
        
        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, final_score))
        
        if logger.isEnabledFor(logging.DEBUG):
            assert 0 <= final_score <= 1, f"Score must be 0-1, got {final_score}"
        
        logger.debug(f"Paper {paper.id[:8]} scores - keyword: {keyword_score:.3f}, "
                    f"category: {category_score:.3f}, semantic: {semantic_score:.3f}, "
                    f"final: {final_score:.3f}")
        
        return final_score
    
    def _calculate_keyword_score(self, text: str) -> float:
        """Score based on keyword frequency and importance"""
        score = 0.0
        text_words = set(re.findall(r'\b\w+\b', text.lower()))
        
        for keyword in self.keywords:
            keyword_words = set(re.findall(r'\b\w+\b', keyword.lower()))
            
            # Check for exact phrase match
            if keyword.lower() in text:
                score += 0.8
            
            # Check for partial matches (word overlap)
            overlap = len(keyword_words.intersection(text_words))
            if overlap > 0:
                overlap_ratio = overlap / len(keyword_words)
                score += 0.4 * overlap_ratio
        
        # Normalize by number of keywords
        return min(1.0, score / len(self.keywords))
    
    def _calculate_category_score(self, categories: List[str]) -> float:
        """Score based on arXiv category relevance"""
        if not categories:
            return 0.0
        
        relevant_categories = set(config.SUBJECT_CATEGORIES)
        paper_categories = set(categories)
        
        # Direct category matches
        matches = len(relevant_categories.intersection(paper_categories))
        
        if matches > 0:
            return min(1.0, matches / len(relevant_categories))
        
        # Partial category matches (same main category)
        partial_score = 0.0
        for cat in paper_categories:
            main_cat = cat.split('.')[0] if '.' in cat else cat
            for rel_cat in relevant_categories:
                rel_main = rel_cat.split('.')[0] if '.' in rel_cat else rel_cat
                if main_cat == rel_main:
                    partial_score += 0.5
        
        return min(1.0, partial_score / len(relevant_categories))
    
    def _calculate_semantic_score(self, text: str) -> float:
        """Score based on semantic similarity using TF-IDF"""
        try:
            # Combine keyword text and paper text for vectorization
            texts = [self.keyword_text, text]
            
            # Fit and transform texts
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            semantic_score = similarity_matrix[0, 1]  # Similarity between keywords and paper
            
            return max(0.0, semantic_score)
            
        except Exception as e:
            logger.warning(f"Failed to calculate semantic score: {e}")
            return 0.0
    
    def score_papers_batch(self, papers: List[ArxivPaper]) -> List[float]:
        """Score multiple papers efficiently"""
        if not papers:
            return []
        
        logger.info(f"Scoring {len(papers)} papers")
        
        scores = []
        for paper in papers:
            try:
                score = self.score_paper(paper)
                scores.append(score)
            except Exception as e:
                logger.warning(f"Failed to score paper {paper.id}: {e}")
                scores.append(0.0)
        
        if logger.isEnabledFor(logging.DEBUG):
            assert len(scores) == len(papers), f"Score count mismatch: {len(scores)} vs {len(papers)}"
        
        avg_score = np.mean(scores) if scores else 0.0
        logger.info(f"Batch scoring complete. Average score: {avg_score:.3f}")
        
        return scores
    
    def get_top_papers(self, papers: List[ArxivPaper], top_n: int = 10) -> List[tuple]:
        """Get top N papers by relevance score"""
        if not papers:
            return []
        
        scored_papers = []
        for paper in papers:
            score = self.score_paper(paper)
            if score >= config.MIN_RELEVANCE_SCORE:
                scored_papers.append((paper, score))
        
        # Sort by score descending
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        
        top_papers = scored_papers[:top_n]
        
        logger.info(f"Selected {len(top_papers)} top papers from {len(papers)} total")
        
        return top_papers