#!/usr/bin/env python3
"""
ArXiv Paper Reader - Find and store relevant research papers
"""

import logging
import argparse
import sys
from datetime import datetime
from typing import List

import config
from arxiv_client import ArxivClient
from paper_storage import PaperStorage
from relevance_scorer import RelevanceScorer

logger = logging.getLogger(__name__)


class ArxivReader:
    def __init__(self):
        self.client = ArxivClient()
        self.storage = PaperStorage()
        self.scorer = RelevanceScorer()

        logger.info("ArXiv Reader initialized")

    def discover_papers(self, days_back: int = None, query: str = "") -> int:
        """Discover and store new relevant papers"""

        if days_back is None:
            days_back = config.DAYS_LOOKBACK

        logger.info(f"Discovering papers from the last {days_back} days")

        # Fetch recent papers
        papers = self.client.get_recent_papers(days_back=days_back)

        if not papers:
            logger.warning("No papers found")
            return 0

        # Score papers for relevance
        logger.info(f"Scoring {len(papers)} papers for relevance")
        stored_count = 0

        for paper in papers:
            try:
                score = self.scorer.score_paper(paper)

                if score >= config.MIN_RELEVANCE_SCORE:
                    success = self.storage.store_paper(paper, score)
                    if success:
                        stored_count += 1
                        logger.debug(
                            f"Stored paper: {paper.title[:50]}... (score: {score:.3f})"
                        )
                else:
                    logger.debug(
                        f"Skipped low-relevance paper: {paper.title[:50]}... (score: {score:.3f})"
                    )

            except Exception as e:
                logger.error(f"Failed to process paper {paper.id}: {e}")
                continue

        logger.info(f"Stored {stored_count} relevant papers out of {len(papers)} total")
        return stored_count

    def list_papers(self, limit: int = 20, min_relevance: float = None) -> List[dict]:
        """List stored papers"""

        if min_relevance is None:
            min_relevance = config.MIN_RELEVANCE_SCORE

        papers = self.storage.get_papers(
            min_relevance=min_relevance, limit=limit, order_by="relevance_score"
        )

        return papers

    def show_stats(self) -> dict:
        """Show database statistics"""
        return self.storage.get_stats()

    def search_papers(self, query: str, limit: int = 20) -> int:
        """Search for specific papers and store relevant ones"""

        logger.info(f"Searching for papers matching: {query}")

        papers = self.client.search_papers(query=query, max_results=limit * 2)

        if not papers:
            logger.warning("No papers found for query")
            return 0

        stored_count = 0
        for paper in papers:
            try:
                score = self.scorer.score_paper(paper)

                if score >= config.MIN_RELEVANCE_SCORE:
                    success = self.storage.store_paper(paper, score)
                    if success:
                        stored_count += 1
            except Exception as e:
                logger.error(f"Failed to process paper {paper.id}: {e}")
                continue

        logger.info(f"Stored {stored_count} relevant papers from search")
        return stored_count


def print_papers(papers: List[dict], show_summary: bool = False):
    """Pretty print papers list"""

    if not papers:
        print("No papers found.")
        return

    print(f"\nFound {len(papers)} papers:")
    print("=" * 80)

    for i, paper in enumerate(papers, 1):
        status_indicators = []
        if paper.get("is_read"):
            status_indicators.append("✓")
        if paper.get("is_starred"):
            status_indicators.append("★")

        status = " " + "".join(status_indicators) if status_indicators else ""

        print(f"{i}. {paper['title']}{status}")
        print(
            f"   Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}"
        )
        print(
            f"   Relevance: {paper['relevance_score']:.3f} | Published: {paper['published'][:10]}"
        )
        print(f"   Categories: {', '.join(paper['categories'][:3])}")
        print(f"   ID: {paper['id']}")

        if show_summary and paper.get("summary"):
            summary = (
                paper["summary"][:200] + "..."
                if len(paper["summary"]) > 200
                else paper["summary"]
            )
            print(f"   Summary: {summary}")

        print()


def main():
    parser = argparse.ArgumentParser(description="ArXiv Paper Reader")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover new papers")
    discover_parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Days to look back (default: {config.DAYS_LOOKBACK})",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List stored papers")
    list_parser.add_argument(
        "--limit", type=int, default=20, help="Number of papers to show"
    )
    list_parser.add_argument(
        "--min-relevance", type=float, default=None, help="Minimum relevance score"
    )
    list_parser.add_argument(
        "--summary", action="store_true", help="Show paper summaries"
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for specific papers")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit", type=int, default=20, help="Max results to fetch"
    )

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Mark commands
    mark_parser = subparsers.add_parser("mark", help="Mark paper status")
    mark_parser.add_argument("paper_id", help="Paper ID")
    mark_parser.add_argument(
        "action", choices=["read", "star", "unstar"], help="Action to perform"
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    if not args.command:
        parser.print_help()
        return

    try:
        reader = ArxivReader()

        if args.command == "discover":
            count = reader.discover_papers(days_back=args.days)
            print(f"Discovered and stored {count} relevant papers")

        elif args.command == "list":
            papers = reader.list_papers(
                limit=args.limit, min_relevance=args.min_relevance
            )
            print_papers(papers, show_summary=args.summary)

        elif args.command == "search":
            count = reader.search_papers(args.query, limit=args.limit)
            print(f"Found and stored {count} relevant papers for query: {args.query}")

        elif args.command == "stats":
            stats = reader.show_stats()
            print("\nDatabase Statistics:")
            print("=" * 30)
            for key, value in stats.items():
                formatted_key = key.replace("_", " ").title()
                print(f"{formatted_key}: {value}")

        elif args.command == "mark":
            storage = PaperStorage()

            if args.action == "read":
                success = storage.mark_as_read(args.paper_id)
            elif args.action == "star":
                success = storage.star_paper(args.paper_id, starred=True)
            elif args.action == "unstar":
                success = storage.star_paper(args.paper_id, starred=False)

            if success:
                print(f"Paper {args.paper_id} marked as {args.action}")
            else:
                print(f"Failed to mark paper {args.paper_id}")

    except KeyboardInterrupt:
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
