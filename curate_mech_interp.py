#!/usr/bin/env python3
"""
Curated Mechanistic Interpretability Research Timeline
Focus on historical progression from foundational to exploratory work
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

def create_curated_timeline():
    """Create a thoughtful narrative of mechanistic interpretability development"""
    
    conn = sqlite3.connect('arxiv_papers.db')
    conn.row_factory = sqlite3.Row
    
    # Get all papers sorted by date
    cursor = conn.execute('''
        SELECT * FROM papers 
        ORDER BY published ASC
    ''')
    
    papers = []
    for row in cursor.fetchall():
        paper = dict(row)
        paper['authors'] = json.loads(paper['authors'])
        paper['categories'] = json.loads(paper['categories'])
        papers.append(paper)
    
    conn.close()
    
    print("🧠 MECHANISTIC INTERPRETABILITY: FROM FOUNDATIONS TO FRONTIERS")
    print("=" * 70)
    print()
    
    # Curated narrative sections
    sections = {
        "foundations": {
            "title": "🏗️  FOUNDATIONAL WORK (2014-2018)",
            "description": "Early gradient-based methods and visualization techniques",
            "papers": []
        },
        "development": {
            "title": "🔬 METHODOLOGICAL DEVELOPMENT (2016-2020)", 
            "description": "Feature visualization, attribution methods, and concept-based approaches",
            "papers": []
        },
        "circuits": {
            "title": "⚡ CIRCUIT ANALYSIS ERA (2020-2023)",
            "description": "Understanding neural circuits, attention mechanisms, and mechanistic analysis",
            "papers": []
        },
        "modern": {
            "title": "🔮 MODERN MECHANISTIC WORK (2023-2025)",
            "description": "Sparse autoencoders, transformer internals, and scaling interpretability",
            "papers": []
        }
    }
    
    # Categorize papers based on content and year
    for paper in papers:
        try:
            pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
            year = pub_date.year
        except:
            year = int(paper['published'][:4]) if paper['published'][:4].isdigit() else 2025
        
        title_lower = paper['title'].lower()
        summary_lower = paper['summary'].lower() if paper['summary'] else ""
        
        # Classification logic based on content and year
        if any(term in title_lower for term in ['grad-cam', 'saliency', 'gradient']) and year <= 2018:
            sections["foundations"]["papers"].append(paper)
        elif any(term in title_lower for term in ['feature visualization', 'activation', 'lime', 'shap']) and year <= 2020:
            sections["development"]["papers"].append(paper)
        elif any(term in title_lower + summary_lower for term in ['circuit', 'attention heads', 'mechanistic', 'probe']) and year <= 2023:
            sections["circuits"]["papers"].append(paper)
        elif year >= 2023:
            sections["modern"]["papers"].append(paper)
        else:
            # Default to development if unclear
            sections["development"]["papers"].append(paper)
    
    # Print each section
    for section_key, section in sections.items():
        if section["papers"]:
            print(f"{section['title']}")
            print(f"📖 {section['description']}")
            print("-" * 50)
            
            # Sort by relevance within section
            section["papers"].sort(key=lambda p: p['relevance_score'], reverse=True)
            
            for i, paper in enumerate(section["papers"][:8], 1):  # Top 8 per section
                try:
                    pub_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
                    year = pub_date.year
                except:
                    year = paper['published'][:4]
                
                print(f"{i}. [{year}] {paper['title']}")
                print(f"   👥 {', '.join(paper['authors'][:2])}{'...' if len(paper['authors']) > 2 else ''}")
                print(f"   📊 Relevance: {paper['relevance_score']:.3f}")
                
                # Add contextual insight based on content
                title_lower = paper['title'].lower()
                if 'grad-cam' in title_lower:
                    print("   💡 Gradient-based visual explanations - foundational attribution method")
                elif 'interpretability' in title_lower and 'mechanistic' in title_lower:
                    print("   🔧 Core mechanistic interpretability methodology")
                elif 'attention' in title_lower:
                    print("   👁️  Attention mechanism analysis - transformer internals")
                elif 'probe' in title_lower or 'probing' in title_lower:
                    print("   🎯 Probing methodology - representation analysis")
                elif 'circuit' in title_lower:
                    print("   ⚡ Neural circuit analysis - understanding computation flow")
                elif 'feature' in title_lower:
                    print("   🎨 Feature analysis and visualization")
                
                print()
            
            print()
    
    # Key insights summary
    print("🎯 KEY INSIGHTS FROM THE COLLECTION")
    print("=" * 40)
    print("• Early work focused on gradient-based attribution (Grad-CAM, saliency)")
    print("• Development period saw concept-based methods (TCAV, LIME/SHAP)")
    print("• Circuit analysis emerged with transformer interpretability")
    print("• Modern work explores scaling interpretability to large models")
    print("• Recent focus: sparse autoencoders, mechanistic understanding")
    print()
    
    # Recommend next searches for missing foundational work
    print("🔍 RECOMMENDED SEARCHES TO COMPLETE THE HISTORY")
    print("=" * 45)
    print("• 'Zeiler Fergus' - early visualization work (2013)")
    print("• 'network dissection' - Bau et al. concept detection")
    print("• 'adversarial examples' - Szegedy, Goodfellow")
    print("• 'transformer circuits' - Elhage et al.")
    print("• 'sparse autoencoder' - Cunningham, Anthropic")

if __name__ == "__main__":
    create_curated_timeline()