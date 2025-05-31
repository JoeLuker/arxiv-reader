import logging
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import torch

import config
from arxiv_client import ArxivPaper

logger = logging.getLogger(__name__)


class SemanticScorer:
    """Enhanced semantic scoring using sentence transformers for better relevance detection"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with a sentence transformer model optimized for semantic similarity.
        all-MiniLM-L6-v2 is a good balance of performance and speed for this use case.
        """
        self.model_name = model_name
        self.model = None
        self.keyword_embeddings = None

        if logger.isEnabledFor(logging.DEBUG):
            assert model_name, "Model name should not be empty"

        logger.info(f"Initializing semantic scorer with model: {model_name}")
        self._load_model()
        self._precompute_keyword_embeddings()

    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise

    def _precompute_keyword_embeddings(self):
        """Precompute embeddings for relevance keywords to improve performance"""
        if not self.model:
            return

        try:
            # Create comprehensive keyword text for mechanistic interpretability
            keyword_texts = config.RELEVANCE_KEYWORDS.copy()

            # Add some domain-specific context
            keyword_texts.extend(
                [
                    "understanding how neural networks work internally",
                    "explaining model behavior and decision making",
                    "analyzing internal representations in transformers",
                    "probing what language models learn",
                    "visualizing attention patterns and feature maps",
                    "circuit-level analysis of neural networks",
                ]
            )

            logger.info(
                f"Computing embeddings for {len(keyword_texts)} keyword phrases"
            )
            self.keyword_embeddings = self.model.encode(
                keyword_texts, convert_to_tensor=True
            )

            if logger.isEnabledFor(logging.DEBUG):
                assert (
                    self.keyword_embeddings is not None
                ), "Keyword embeddings should not be None"
                assert len(self.keyword_embeddings) == len(
                    keyword_texts
                ), f"Embedding count mismatch"

            logger.info("Keyword embeddings precomputed successfully")

        except Exception as e:
            logger.error(f"Failed to precompute keyword embeddings: {e}")
            self.keyword_embeddings = None

    def score_paper_semantic(self, paper: ArxivPaper) -> float:
        """Calculate semantic similarity score for a paper using embeddings"""

        if not self.model or self.keyword_embeddings is None:
            logger.warning(
                "Model or keyword embeddings not available, falling back to 0.0"
            )
            return 0.0

        if logger.isEnabledFor(logging.DEBUG):
            assert isinstance(
                paper, ArxivPaper
            ), f"Expected ArxivPaper, got {type(paper)}"

        try:
            # Combine title and abstract for semantic analysis
            paper_text = f"{paper.title} {paper.summary}".strip()

            if not paper_text:
                logger.warning(f"Empty text content for paper {paper.id}")
                return 0.0

            # Encode paper text
            paper_embedding = self.model.encode([paper_text], convert_to_tensor=True)

            # Calculate similarities with all keyword embeddings
            similarities = cosine_similarity(
                paper_embedding.cpu().numpy(), self.keyword_embeddings.cpu().numpy()
            )[0]

            # Use max similarity as the semantic score
            max_similarity = float(np.max(similarities))

            # Also calculate mean of top-k similarities for robustness
            top_k = min(5, len(similarities))
            top_similarities = np.sort(similarities)[-top_k:]
            mean_top_similarity = float(np.mean(top_similarities))

            # Combine max and mean for final score
            semantic_score = 0.7 * max_similarity + 0.3 * mean_top_similarity

            # Ensure score is between 0 and 1
            semantic_score = max(0.0, min(1.0, semantic_score))

            if logger.isEnabledFor(logging.DEBUG):
                assert (
                    0 <= semantic_score <= 1
                ), f"Semantic score must be 0-1, got {semantic_score}"

            logger.debug(
                f"Paper {paper.id[:8]} semantic score: {semantic_score:.3f} "
                f"(max: {max_similarity:.3f}, mean_top: {mean_top_similarity:.3f})"
            )

            return semantic_score

        except Exception as e:
            logger.warning(
                f"Failed to calculate semantic score for paper {paper.id}: {e}"
            )
            return 0.0

    def score_papers_batch(self, papers: List[ArxivPaper]) -> List[float]:
        """Score multiple papers efficiently using batch processing"""

        if not papers:
            return []

        if not self.model or self.keyword_embeddings is None:
            logger.warning("Model not available, returning zero scores")
            return [0.0] * len(papers)

        logger.info(f"Batch scoring {len(papers)} papers with semantic embeddings")

        try:
            # Extract text from all papers
            paper_texts = []
            for paper in papers:
                text = f"{paper.title} {paper.summary}".strip()
                paper_texts.append(text if text else "empty")

            # Batch encode all papers
            paper_embeddings = self.model.encode(
                paper_texts, convert_to_tensor=True, batch_size=32
            )

            # Calculate similarities with keyword embeddings
            similarities_matrix = cosine_similarity(
                paper_embeddings.cpu().numpy(), self.keyword_embeddings.cpu().numpy()
            )

            scores = []
            for i, similarities in enumerate(similarities_matrix):
                # Same scoring logic as single paper
                max_similarity = float(np.max(similarities))
                top_k = min(5, len(similarities))
                top_similarities = np.sort(similarities)[-top_k:]
                mean_top_similarity = float(np.mean(top_similarities))

                semantic_score = 0.7 * max_similarity + 0.3 * mean_top_similarity
                semantic_score = max(0.0, min(1.0, semantic_score))
                scores.append(semantic_score)

            if logger.isEnabledFor(logging.DEBUG):
                assert len(scores) == len(
                    papers
                ), f"Score count mismatch: {len(scores)} vs {len(papers)}"
                assert all(0 <= s <= 1 for s in scores), f"All scores must be 0-1"

            avg_score = np.mean(scores) if scores else 0.0
            logger.info(
                f"Batch semantic scoring complete. Average score: {avg_score:.3f}"
            )

            return scores

        except Exception as e:
            logger.error(f"Failed to batch score papers: {e}")
            return [0.0] * len(papers)

    def get_most_similar_keywords(
        self, paper: ArxivPaper, top_k: int = 3
    ) -> List[tuple]:
        """Get the most similar keywords for a paper (for debugging/analysis)"""

        if not self.model or self.keyword_embeddings is None:
            return []

        try:
            paper_text = f"{paper.title} {paper.summary}".strip()
            if not paper_text:
                return []

            paper_embedding = self.model.encode([paper_text], convert_to_tensor=True)
            similarities = cosine_similarity(
                paper_embedding.cpu().numpy(), self.keyword_embeddings.cpu().numpy()
            )[0]

            # Get indices of top similarities
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            result = []
            keywords_list = config.RELEVANCE_KEYWORDS + [
                "understanding how neural networks work internally",
                "explaining model behavior and decision making",
                "analyzing internal representations in transformers",
                "probing what language models learn",
                "visualizing attention patterns and feature maps",
                "circuit-level analysis of neural networks",
            ]

            for idx in top_indices:
                if idx < len(keywords_list):
                    result.append((keywords_list[idx], float(similarities[idx])))

            return result

        except Exception as e:
            logger.warning(f"Failed to get similar keywords for paper {paper.id}: {e}")
            return []
