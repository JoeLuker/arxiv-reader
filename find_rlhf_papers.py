#!/usr/bin/env python3
"""
Find and analyze RLHF training activation and interpretability papers
"""

import sqlite3
import json
from datetime import datetime

def find_rlhf_interpretability_papers():
    """Find papers related to RLHF training and activation analysis"""
    
    conn = sqlite3.connect('arxiv_papers.db')
    conn.row_factory = sqlite3.Row
    
    # Search for papers with RLHF-related terms
    rlhf_keywords = [
        'rlhf', 'reinforcement learning from human feedback',
        'human feedback', 'preference learning', 'reward model',
        'constitutional ai', 'alignment', 'preference'
    ]
    
    interpretability_keywords = [
        'activation', 'interpretability', 'probe', 'circuit',
        'mechanistic', 'representation', 'feature', 'analysis'
    ]
    
    cursor = conn.execute('SELECT * FROM papers ORDER BY relevance_score DESC')
    
    rlhf_papers = []
    
    for row in cursor:
        paper = dict(row)
        paper['authors'] = json.loads(paper['authors'])
        paper['categories'] = json.loads(paper['categories'])
        
        title_lower = paper['title'].lower()
        summary_lower = paper['summary'].lower() if paper['summary'] else ""
        full_text = title_lower + " " + summary_lower
        
        # Check for RLHF-related terms
        has_rlhf = any(keyword in full_text for keyword in rlhf_keywords)
        has_interpretability = any(keyword in full_text for keyword in interpretability_keywords)
        
        if has_rlhf or (has_interpretability and ('human' in full_text or 'feedback' in full_text)):
            paper['rlhf_relevance'] = has_rlhf
            paper['interp_relevance'] = has_interpretability
            rlhf_papers.append(paper)
    
    conn.close()
    return rlhf_papers

def analyze_rlhf_papers():
    """Analyze and categorize RLHF-related papers"""
    
    papers = find_rlhf_interpretability_papers()
    
    print("🤖 RLHF TRAINING & ACTIVATION ANALYSIS PAPERS")
    print("=" * 55)
    print(f"Found {len(papers)} papers related to RLHF and interpretability")
    print()
    
    # Categorize papers
    direct_rlhf = []
    preference_learning = []
    reward_modeling = []
    alignment_interp = []
    general_feedback = []
    
    for paper in papers:
        title_lower = paper['title'].lower()
        summary_lower = paper['summary'].lower() if paper['summary'] else ""
        full_text = title_lower + " " + summary_lower
        
        if 'rlhf' in full_text:
            direct_rlhf.append(paper)
        elif 'preference' in full_text and ('learning' in full_text or 'model' in full_text):
            preference_learning.append(paper)
        elif 'reward' in full_text and 'model' in full_text:
            reward_modeling.append(paper)
        elif any(term in full_text for term in ['alignment', 'constitutional', 'safety']):
            alignment_interp.append(paper)
        else:
            general_feedback.append(paper)
    
    # Print each category
    categories = [
        ("🎯 DIRECT RLHF STUDIES", direct_rlhf),
        ("⚖️ PREFERENCE LEARNING", preference_learning),
        ("🏆 REWARD MODELING", reward_modeling),
        ("🛡️ ALIGNMENT & SAFETY", alignment_interp),
        ("📝 HUMAN FEEDBACK GENERAL", general_feedback)
    ]
    
    for category_name, category_papers in categories:
        if category_papers:
            print(f"{category_name} ({len(category_papers)} papers)")
            print("-" * 40)
            
            # Sort by relevance
            category_papers.sort(key=lambda p: p['relevance_score'], reverse=True)
            
            for i, paper in enumerate(category_papers[:6], 1):  # Top 6 per category
                try:
                    year = paper['published'][:4]
                except:
                    year = "????"
                
                print(f"{i}. [{year}] {paper['title']}")
                print(f"   👥 {', '.join(paper['authors'][:2])}{'...' if len(paper['authors']) > 2 else ''}")
                print(f"   📊 Relevance: {paper['relevance_score']:.3f}")
                
                # Add specific insights about RLHF relevance
                title_lower = paper['title'].lower()
                summary_lower = paper['summary'].lower() if paper['summary'] else ""
                
                if 'activation' in title_lower + summary_lower:
                    print("   🧠 Contains activation analysis")
                if 'mechanistic' in title_lower + summary_lower:
                    print("   ⚙️ Mechanistic interpretability approach")
                if 'probe' in title_lower + summary_lower:
                    print("   🎯 Uses probing methodology")
                if 'circuit' in title_lower + summary_lower:
                    print("   ⚡ Neural circuit analysis")
                if 'training' in title_lower + summary_lower:
                    print("   📈 Training dynamics analysis")
                
                print(f"   📄 ID: {paper['id']}")
                print()
            
            print()
    
    # Highlight most promising for activation analysis
    print("🔬 MOST PROMISING FOR RLHF ACTIVATION ANALYSIS")
    print("=" * 45)
    
    # Filter for papers that mention both RLHF concepts and activation/training analysis
    promising = []
    for paper in papers:
        title_lower = paper['title'].lower()
        summary_lower = paper['summary'].lower() if paper['summary'] else ""
        full_text = title_lower + " " + summary_lower
        
        has_training_analysis = any(term in full_text for term in [
            'activation', 'training dynamics', 'mechanistic', 'circuit', 'probe'
        ])
        
        has_rlhf_context = any(term in full_text for term in [
            'rlhf', 'human feedback', 'preference', 'reward model', 'alignment'
        ])
        
        if has_training_analysis and has_rlhf_context and paper['relevance_score'] >= 0.16:
            promising.append(paper)
    
    if promising:
        promising.sort(key=lambda p: p['relevance_score'], reverse=True)
        for i, paper in enumerate(promising[:5], 1):
            try:
                year = paper['published'][:4]
            except:
                year = "????"
            
            print(f"{i}. [{year}] {paper['title']}")
            print(f"   📊 Relevance: {paper['relevance_score']:.3f}")
            print(f"   📄 ID: {paper['id']}")
            print()
    else:
        print("No papers found that directly combine RLHF with activation analysis.")
        print("This suggests a research gap in mechanistic interpretability of RLHF training!")

if __name__ == "__main__":
    analyze_rlhf_papers()