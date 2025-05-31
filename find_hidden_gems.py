#!/usr/bin/env python3
"""
Find hidden gems - smaller papers from unknown authors that may be worth reading
"""

import sqlite3
import json
from collections import Counter
import re


def analyze_author_prominence():
    """Analyze author patterns to identify less prominent researchers"""

    conn = sqlite3.connect("arxiv_papers.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("SELECT * FROM papers")

    all_authors = []
    author_paper_count = Counter()

    for row in cursor:
        authors = json.loads(row["authors"])
        all_authors.extend(authors)
        for author in authors:
            author_paper_count[author] += 1

    conn.close()

    # Identify "unknown" authors (appear in few papers)
    unknown_authors = {
        author for author, count in author_paper_count.items() if count <= 2
    }
    prominent_authors = {
        author for author, count in author_paper_count.items() if count >= 3
    }

    print(f"📊 AUTHOR ANALYSIS")
    print(f"Total unique authors: {len(set(all_authors))}")
    print(f"Authors with 1-2 papers: {len(unknown_authors)}")
    print(f"Authors with 3+ papers: {len(prominent_authors)}")
    print()

    return unknown_authors, prominent_authors


def find_hidden_gems():
    """Find papers from lesser-known authors with good relevance scores"""

    unknown_authors, prominent_authors = analyze_author_prominence()

    conn = sqlite3.connect("arxiv_papers.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT * FROM papers 
        WHERE relevance_score >= 0.17
        ORDER BY relevance_score DESC
    """
    )

    hidden_gems = []

    for row in cursor:
        paper = dict(row)
        paper["authors"] = json.loads(paper["authors"])

        # Check if paper has mostly unknown authors
        paper_authors = set(paper["authors"])
        unknown_count = len(paper_authors.intersection(unknown_authors))
        prominent_count = len(paper_authors.intersection(prominent_authors))

        # Criteria for hidden gem:
        # 1. Mostly unknown authors OR single/few authors
        # 2. Decent relevance score
        # 3. Not from obvious big labs

        is_mostly_unknown = unknown_count >= prominent_count
        is_small_team = len(paper["authors"]) <= 3

        # Check for big lab indicators in affiliations (heuristic)
        title_text = paper["title"].lower()
        has_novelty_indicators = any(
            term in title_text
            for term in ["novel", "new", "towards", "approach", "method", "framework"]
        )

        if (is_mostly_unknown or is_small_team) and has_novelty_indicators:
            paper["unknown_ratio"] = (
                unknown_count / len(paper["authors"]) if paper["authors"] else 0
            )
            paper["team_size"] = len(paper["authors"])
            hidden_gems.append(paper)

    conn.close()
    return hidden_gems


def print_hidden_gems():
    """Print curated list of hidden gems"""

    gems = find_hidden_gems()

    print("💎 HIDDEN GEMS: Lesser-Known but Potentially Valuable Papers")
    print("=" * 65)
    print("Criteria: Unknown/small author teams + novel approaches + decent relevance")
    print()

    # Group by relevance tiers
    high_relevance = [p for p in gems if p["relevance_score"] >= 0.25]
    medium_relevance = [p for p in gems if 0.20 <= p["relevance_score"] < 0.25]
    decent_relevance = [p for p in gems if 0.17 <= p["relevance_score"] < 0.20]

    sections = [
        ("🌟 HIGH POTENTIAL GEMS", high_relevance),
        ("💡 INTERESTING APPROACHES", medium_relevance),
        ("🔍 WORTH INVESTIGATING", decent_relevance),
    ]

    for section_title, papers in sections:
        if papers:
            print(f"{section_title} ({len(papers)} papers)")
            print("-" * 40)

            for i, paper in enumerate(papers[:8], 1):  # Top 8 per section
                try:
                    year = paper["published"][:4]
                except:
                    year = "????"

                print(f"{i}. [{year}] {paper['title']}")
                print(f"   👥 Authors: {', '.join(paper['authors'])}")
                print(f"   📊 Relevance: {paper['relevance_score']:.3f}")
                print(f"   👤 Team size: {paper['team_size']}")
                print(f"   🔬 Unknown author ratio: {paper['unknown_ratio']:.1%}")

                # Add insight about why this might be a gem
                title_lower = paper["title"].lower()
                if "novel" in title_lower:
                    print("   💫 Claims novel approach")
                elif "towards" in title_lower:
                    print("   🎯 Exploratory/directional work")
                elif "method" in title_lower or "framework" in title_lower:
                    print("   🛠️ New methodology")

                print(f"   📄 ID: {paper['id']}")
                print()

            print()


def search_for_more_gems():
    """Suggest specific searches for more hidden gems"""

    print("🔍 RECOMMENDED SEARCHES FOR MORE HIDDEN GEMS")
    print("=" * 50)
    print("Try these specific terms to find niche work:")
    print()
    print("• 'neural probe' - smaller probing studies")
    print("• 'representation analysis' - focused analysis work")
    print("• 'activation pattern' - detailed activation studies")
    print("• 'feature extraction' - specific feature work")
    print("• 'model understanding' - broad understanding papers")
    print("• 'hidden layer' - layer-specific analysis")
    print("• 'embedding analysis' - embedding space studies")
    print("• 'neuron activation' - individual neuron studies")
    print()


if __name__ == "__main__":
    print_hidden_gems()
    print()
    search_for_more_gems()
