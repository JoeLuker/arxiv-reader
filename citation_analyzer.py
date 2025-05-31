import logging
import re
import requests
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from urllib.parse import quote
import time

from arxiv_client import ArxivPaper
import config

logger = logging.getLogger(__name__)

@dataclass
class CitationData:
    """Represents citation/reference information for a paper"""
    paper_id: str
    references: List[str]  # List of referenced arXiv IDs
    cited_by: List[str]    # List of arXiv IDs that cite this paper
    reference_count: int
    citation_count: int
    
class CitationAnalyzer:
    """
    Analyzes citation networks for arXiv papers.
    
    Note: Since arXiv API doesn't provide citation data directly, this implementation
    focuses on extracting reference patterns from abstracts and building networks
    from available metadata. For production use, consider integrating with:
    - INSPIRE-HEP (for physics papers)
    - Semantic Scholar API
    - OpenCitations
    """
    
    def __init__(self):
        self.citation_cache: Dict[str, CitationData] = {}
        self.rate_limit_delay = 1.0  # Delay between external API calls
        self.last_request_time = 0
        
        # Patterns to extract arXiv references from text
        self.arxiv_patterns = [
            r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)',  # arXiv:YYYY.NNNNN
            r'(\d{4}\.\d{4,5}(?:v\d+)?)',        # Just the ID
            r'arXiv/(\w+/\d{7})',                # Old format arXiv/subject-class/YYMMnnn
        ]
        
        logger.info("Citation analyzer initialized")
    
    def _rate_limit(self):
        """Simple rate limiting for external API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def extract_arxiv_references(self, paper: ArxivPaper) -> List[str]:
        """
        Extract arXiv references from paper title and abstract.
        This is a heuristic approach since full paper text isn't available via API.
        """
        text = f"{paper.title} {paper.summary}".lower()
        references = set()
        
        for pattern in self.arxiv_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ref_id = match.group(1)
                # Clean up the reference ID
                if ref_id != paper.id:  # Don't include self-references
                    references.add(ref_id)
        
        result = list(references)
        logger.debug(f"Extracted {len(result)} arXiv references from paper {paper.id[:8]}")
        return result
    
    def build_citation_network(self, papers: List[ArxivPaper]) -> Dict[str, CitationData]:
        """
        Build a citation network from a list of papers.
        Creates bidirectional citation relationships.
        """
        logger.info(f"Building citation network for {len(papers)} papers")
        
        # First pass: extract all references
        paper_refs = {}
        all_paper_ids = {paper.id for paper in papers}
        
        for paper in papers:
            references = self.extract_arxiv_references(paper)
            # Only keep references that are in our paper set
            filtered_refs = [ref for ref in references if ref in all_paper_ids]
            paper_refs[paper.id] = filtered_refs
        
        # Second pass: build citation data with bidirectional links
        citation_network = {}
        
        for paper in papers:
            paper_id = paper.id
            references = paper_refs.get(paper_id, [])
            
            # Find papers that cite this paper
            cited_by = []
            for other_id, other_refs in paper_refs.items():
                if paper_id in other_refs and other_id != paper_id:
                    cited_by.append(other_id)
            
            citation_data = CitationData(
                paper_id=paper_id,
                references=references,
                cited_by=cited_by,
                reference_count=len(references),
                citation_count=len(cited_by)
            )
            
            citation_network[paper_id] = citation_data
            self.citation_cache[paper_id] = citation_data
        
        logger.info(f"Built citation network with {len(citation_network)} nodes")
        self._log_network_stats(citation_network)
        
        return citation_network
    
    def _log_network_stats(self, network: Dict[str, CitationData]):
        """Log statistics about the citation network"""
        if not network:
            return
        
        citation_counts = [data.citation_count for data in network.values()]
        reference_counts = [data.reference_count for data in network.values()]
        
        total_citations = sum(citation_counts)
        total_references = sum(reference_counts)
        avg_citations = total_citations / len(network) if network else 0
        avg_references = total_references / len(network) if network else 0
        
        most_cited = max(network.values(), key=lambda x: x.citation_count)
        most_references = max(network.values(), key=lambda x: x.reference_count)
        
        logger.info(f"Citation network stats:")
        logger.info(f"  Total citations: {total_citations}")
        logger.info(f"  Total references: {total_references}")
        logger.info(f"  Avg citations per paper: {avg_citations:.2f}")
        logger.info(f"  Avg references per paper: {avg_references:.2f}")
        logger.info(f"  Most cited paper: {most_cited.paper_id[:8]} ({most_cited.citation_count} citations)")
        logger.info(f"  Most references: {most_references.paper_id[:8]} ({most_references.reference_count} refs)")
    
    def get_citation_score(self, paper_id: str, network: Dict[str, CitationData]) -> float:
        """
        Calculate a citation-based relevance score for a paper.
        Combines direct citations with network centrality measures.
        """
        if paper_id not in network:
            return 0.0
        
        citation_data = network[paper_id]
        
        # Basic citation count score (normalized)
        max_citations = max((data.citation_count for data in network.values()), default=1)
        citation_score = citation_data.citation_count / max_citations if max_citations > 0 else 0
        
        # Reference network score (papers that reference important papers get boost)
        reference_score = 0.0
        if citation_data.references:
            ref_citation_counts = []
            for ref_id in citation_data.references:
                if ref_id in network:
                    ref_citation_counts.append(network[ref_id].citation_count)
            
            if ref_citation_counts:
                avg_ref_citations = sum(ref_citation_counts) / len(ref_citation_counts)
                reference_score = min(1.0, avg_ref_citations / max_citations) if max_citations > 0 else 0
        
        # Combine scores
        final_score = 0.7 * citation_score + 0.3 * reference_score
        
        logger.debug(f"Citation score for {paper_id[:8]}: {final_score:.3f} "
                    f"(citations: {citation_score:.3f}, refs: {reference_score:.3f})")
        
        return final_score
    
    def find_influential_papers(self, network: Dict[str, CitationData], top_k: int = 10) -> List[tuple]:
        """Find the most influential papers in the network based on citations"""
        if not network:
            return []
        
        papers_with_scores = []
        for paper_id, citation_data in network.items():
            score = self.get_citation_score(paper_id, network)
            papers_with_scores.append((paper_id, score, citation_data.citation_count))
        
        # Sort by score descending
        papers_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        result = papers_with_scores[:top_k]
        logger.info(f"Top {len(result)} influential papers identified")
        
        return result
    
    def get_related_papers(self, paper_id: str, network: Dict[str, CitationData], 
                          max_distance: int = 2) -> Set[str]:
        """
        Find papers related to the given paper through citation links.
        Uses breadth-first search to find papers within max_distance hops.
        """
        if paper_id not in network:
            return set()
        
        related = set()
        current_level = {paper_id}
        visited = {paper_id}
        
        for distance in range(max_distance):
            next_level = set()
            
            for current_id in current_level:
                if current_id in network:
                    citation_data = network[current_id]
                    
                    # Add papers this one references
                    for ref_id in citation_data.references:
                        if ref_id not in visited:
                            next_level.add(ref_id)
                            related.add(ref_id)
                            visited.add(ref_id)
                    
                    # Add papers that cite this one
                    for citing_id in citation_data.cited_by:
                        if citing_id not in visited:
                            next_level.add(citing_id)
                            related.add(citing_id)
                            visited.add(citing_id)
            
            current_level = next_level
            if not current_level:
                break
        
        logger.debug(f"Found {len(related)} related papers for {paper_id[:8]} "
                    f"within distance {max_distance}")
        
        return related
    
    def enhance_relevance_with_citations(self, papers: List[ArxivPaper], 
                                       base_scores: List[float]) -> List[float]:
        """
        Enhance relevance scores using citation network analysis.
        """
        if len(papers) != len(base_scores):
            logger.warning("Paper count doesn't match score count")
            return base_scores
        
        if len(papers) < 2:
            logger.info("Not enough papers for citation analysis")
            return base_scores
        
        # Build citation network
        network = self.build_citation_network(papers)
        
        if not network:
            logger.warning("No citation network could be built")
            return base_scores
        
        # Calculate enhanced scores
        enhanced_scores = []
        for i, paper in enumerate(papers):
            base_score = base_scores[i]
            citation_score = self.get_citation_score(paper.id, network)
            
            # Combine base relevance with citation importance
            # Give more weight to base relevance but boost highly cited papers
            enhanced_score = 0.8 * base_score + 0.2 * citation_score
            enhanced_scores.append(enhanced_score)
        
        logger.info("Enhanced relevance scores with citation analysis")
        return enhanced_scores