#!/usr/bin/env python3
"""
Organize papers chronologically for mechanistic interpretability history
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

def get_papers_by_year():
    """Get papers organized by year"""
    conn = sqlite3.connect('arxiv_papers.db')
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute('''
        SELECT * FROM papers 
        ORDER BY published ASC
    ''')
    
    papers_by_year = defaultdict(list)
    
    for row in cursor.fetchall():
        paper = dict(row)
        paper['authors'] = json.loads(paper['authors'])
        paper['categories'] = json.loads(paper['categories'])
        
        # Extract year from published date
        try:
            pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
            year = pub_date.year
        except:
            # Try alternative parsing
            try:
                pub_date = datetime.strptime(paper['published'][:10], '%Y-%m-%d')
                year = pub_date.year
            except:
                year = 'Unknown'
        
        papers_by_year[year].append(paper)
    
    conn.close()
    return papers_by_year

def print_chronological_history():
    """Print papers organized chronologically"""
    papers_by_year = get_papers_by_year()
    
    print("MECHANISTIC INTERPRETABILITY RESEARCH TIMELINE")
    print("=" * 60)
    print()
    
    # Sort years
    for year in sorted(papers_by_year.keys()):
        papers = papers_by_year[year]
        
        print(f"📅 {year} ({len(papers)} papers)")
        print("-" * 40)
        
        # Sort papers by relevance within each year
        papers.sort(key=lambda p: p['relevance_score'], reverse=True)
        
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:2])}{'...' if len(paper['authors']) > 2 else ''}")
            print(f"   Relevance: {paper['relevance_score']:.3f} | ID: {paper['id']}")
            print(f"   Categories: {', '.join(paper['categories'][:3])}")
            
            # Add interpretation context based on year and content
            if year <= 2015:
                context = "🏗️  FOUNDATIONAL"
            elif year <= 2019:
                context = "🔬 DEVELOPMENT" 
            elif year <= 2022:
                context = "🚀 EXPANSION"
            else:
                context = "🔮 EXPLORATORY"
            
            print(f"   {context}")
            print()
        
        print()

def identify_key_papers():
    """Identify potentially key papers in the field"""
    conn = sqlite3.connect('arxiv_papers.db')
    conn.row_factory = sqlite3.Row
    
    # High relevance papers
    cursor = conn.execute('''
        SELECT * FROM papers 
        WHERE relevance_score > 0.25
        ORDER BY relevance_score DESC, published ASC
        LIMIT 15
    ''')
    
    print("🌟 POTENTIALLY KEY PAPERS (High Relevance)")
    print("=" * 50)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        paper = dict(row)
        paper['authors'] = json.loads(paper['authors'])
        
        try:
            pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
            year = pub_date.year
        except:
            year = paper['published'][:4]
        
        print(f"{i}. [{year}] {paper['title']}")
        print(f"   Relevance: {paper['relevance_score']:.3f}")
        print(f"   Key authors: {', '.join(paper['authors'][:2])}")
        print()
    
    conn.close()

if __name__ == "__main__":
    print_chronological_history()
    print("\n" + "="*60 + "\n")
    identify_key_papers()