#!/usr/bin/env python3
"""
Test script for enhanced relevance scoring with semantic embeddings and citation analysis
"""

import logging
import sys
from datetime import datetime, timedelta

import config
from arxiv_client import ArxivClient, ArxivPaper
from relevance_scorer import RelevanceScorer

# Set up logging for testing
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def create_test_papers():
    """Create some test papers for mechanistic interpretability"""

    # Sample mechanistic interpretability papers (simulated)
    test_papers = [
        {
            "id": "2023.12345",
            "title": "Mechanistic Interpretability of Transformer Language Models: Understanding Circuit-Level Representations",
            "summary": "This paper presents a comprehensive analysis of neural circuits in transformer language models. We use activation patching and feature visualization to understand how attention heads process information. Our work contributes to mechanistic interpretability by revealing specific computational patterns in feed-forward networks and residual connections.",
            "authors": [{"name": "Jane Smith"}, {"name": "John Doe"}],
            "published": "2023-12-01T00:00:00Z",
            "updated": "2023-12-01T00:00:00Z",
            "tags": [{"term": "cs.AI"}, {"term": "cs.LG"}],
            "links": [
                {
                    "href": "http://arxiv.org/pdf/2023.12345.pdf",
                    "type": "application/pdf",
                }
            ],
        },
        {
            "id": "2023.67890",
            "title": "Deep Learning Optimization Techniques for Computer Vision",
            "summary": "We propose novel optimization methods for training deep neural networks on image classification tasks. Our approach uses adaptive learning rates and momentum-based updates to achieve state-of-the-art performance on CIFAR-10 and ImageNet datasets.",
            "authors": [{"name": "Alice Johnson"}],
            "published": "2023-11-15T00:00:00Z",
            "updated": "2023-11-15T00:00:00Z",
            "tags": [{"term": "cs.CV"}, {"term": "cs.LG"}],
            "links": [
                {
                    "href": "http://arxiv.org/pdf/2023.67890.pdf",
                    "type": "application/pdf",
                }
            ],
        },
        {
            "id": "2023.11111",
            "title": "Probing Representations in Large Language Models: What Do They Know About Syntax?",
            "summary": "This work investigates what linguistic knowledge is captured in the internal representations of large language models. Using probing techniques and gradient analysis, we analyze how models encode syntactic information across different layers. Our findings suggest that transformer attention patterns correlate with syntactic parsing decisions.",
            "authors": [{"name": "Bob Wilson"}, {"name": "Carol Lee"}],
            "published": "2023-10-30T00:00:00Z",
            "updated": "2023-10-30T00:00:00Z",
            "tags": [{"term": "cs.CL"}, {"term": "cs.AI"}],
            "links": [
                {
                    "href": "http://arxiv.org/pdf/2023.11111.pdf",
                    "type": "application/pdf",
                }
            ],
        },
        {
            "id": "2023.22222",
            "title": "Quantum Computing Algorithms for Cryptographic Applications",
            "summary": "We present quantum algorithms for solving discrete logarithm problems with applications to cryptography. Our approach leverages quantum superposition and entanglement to achieve exponential speedups over classical methods.",
            "authors": [{"name": "David Chen"}],
            "published": "2023-09-20T00:00:00Z",
            "updated": "2023-09-20T00:00:00Z",
            "tags": [{"term": "quant-ph"}, {"term": "cs.CR"}],
            "links": [
                {
                    "href": "http://arxiv.org/pdf/2023.22222.pdf",
                    "type": "application/pdf",
                }
            ],
        },
        {
            "id": "2023.33333",
            "title": "Understanding Attention Mechanisms: A Circuit Analysis of Transformer Models",
            "summary": "We conduct a detailed mechanistic analysis of attention mechanisms in transformer models. Through careful study of attention heads and their connectivity patterns, we identify specific circuits responsible for different types of reasoning tasks. Our work includes activation patching experiments and feature attribution analysis to understand model behavior. This research contributes to AI safety by making model internals more transparent and interpretable.",
            "authors": [{"name": "Eve Rodriguez"}, {"name": "Frank Miller"}],
            "published": "2023-08-10T00:00:00Z",
            "updated": "2023-08-10T00:00:00Z",
            "tags": [{"term": "cs.AI"}, {"term": "cs.LG"}],
            "links": [
                {
                    "href": "http://arxiv.org/pdf/2023.33333.pdf",
                    "type": "application/pdf",
                }
            ],
        },
    ]

    papers = []
    for paper_data in test_papers:
        paper = ArxivPaper(paper_data)
        papers.append(paper)

    return papers


def test_semantic_scoring():
    """Test semantic scoring improvements"""
    logger.info("=== Testing Semantic Scoring ===")

    papers = create_test_papers()

    # Test with semantic scoring enabled
    scorer_semantic = RelevanceScorer(use_semantic=True, use_citations=False)

    # Test without semantic scoring (TF-IDF only)
    scorer_tfidf = RelevanceScorer(use_semantic=False, use_citations=False)

    logger.info("\nScoring papers with different methods:")

    for paper in papers:
        semantic_score = scorer_semantic.score_paper(paper)
        tfidf_score = scorer_tfidf.score_paper(paper)

        logger.info(f"\nPaper: {paper.title[:50]}...")
        logger.info(f"  Semantic score: {semantic_score:.3f}")
        logger.info(f"  TF-IDF score:   {tfidf_score:.3f}")
        logger.info(f"  Difference:     {semantic_score - tfidf_score:+.3f}")

    # Test batch scoring
    logger.info("\n=== Testing Batch Scoring ===")
    semantic_batch_scores = scorer_semantic.score_papers_batch(papers)
    tfidf_batch_scores = scorer_tfidf.score_papers_batch(papers)

    logger.info("Batch scoring results:")
    for i, paper in enumerate(papers):
        logger.info(
            f"{paper.id}: Semantic={semantic_batch_scores[i]:.3f}, TF-IDF={tfidf_batch_scores[i]:.3f}"
        )


def test_citation_analysis():
    """Test citation network analysis"""
    logger.info("\n=== Testing Citation Analysis ===")

    papers = create_test_papers()

    # Add some simulated references to create a citation network
    # Modify paper summaries to include arXiv references
    papers[
        0
    ].summary += " This work builds on previous interpretability research including arXiv:2023.11111 and extends the methodology from arXiv:2023.33333."
    papers[
        2
    ].summary += " Our probing approach is inspired by circuit analysis techniques from arXiv:2023.12345."
    papers[
        4
    ].summary += " This paper references foundational work on attention mechanisms from arXiv:2023.11111."

    # Test scorer with citations enabled
    scorer_with_citations = RelevanceScorer(use_semantic=True, use_citations=True)
    scorer_without_citations = RelevanceScorer(use_semantic=True, use_citations=False)

    scores_with_citations = scorer_with_citations.score_papers_batch(papers)
    scores_without_citations = scorer_without_citations.score_papers_batch(papers)

    logger.info("Citation analysis results:")
    for i, paper in enumerate(papers):
        with_cit = scores_with_citations[i]
        without_cit = scores_without_citations[i]
        diff = with_cit - without_cit

        logger.info(f"\n{paper.id}: {paper.title[:40]}...")
        logger.info(f"  With citations:    {with_cit:.3f}")
        logger.info(f"  Without citations: {without_cit:.3f}")
        logger.info(f"  Citation boost:    {diff:+.3f}")


def test_keyword_matching():
    """Test improved keyword matching for mechanistic interpretability"""
    logger.info("\n=== Testing Enhanced Keywords ===")

    papers = create_test_papers()
    scorer = RelevanceScorer(
        use_semantic=False, use_citations=False
    )  # Pure keyword matching

    logger.info("Keyword matching scores:")
    for paper in papers:
        score = scorer.score_paper(paper)
        logger.info(f"\n{paper.id}: {score:.3f} - {paper.title[:50]}...")

        # Show which keywords matched
        text = f"{paper.title} {paper.summary}".lower()
        matched_keywords = []
        for keyword in config.RELEVANCE_KEYWORDS:
            if keyword.lower() in text:
                matched_keywords.append(keyword)

        if matched_keywords:
            logger.info(f"  Matched keywords: {', '.join(matched_keywords[:5])}")
            if len(matched_keywords) > 5:
                logger.info(f"  ... and {len(matched_keywords) - 5} more")
        else:
            logger.info("  No keyword matches")


def main():
    """Run all tests"""
    logger.info("Starting enhanced scoring system tests")

    try:
        test_keyword_matching()
        test_semantic_scoring()
        test_citation_analysis()

        logger.info("\n=== Test Summary ===")
        logger.info("✓ Enhanced keywords for mechanistic interpretability")
        logger.info("✓ Semantic scoring with sentence transformers")
        logger.info("✓ Citation network analysis")
        logger.info("✓ Batch processing optimization")

        logger.info("\nAll tests completed successfully!")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
