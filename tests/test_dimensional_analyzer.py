"""
Test Script for Dimensional Analyzer
Tests the dimensional analysis service with sample startup ideas
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dimensional_analyzer import DimensionalAnalyzer


def test_dimensional_analyzer():
    """Test the dimensional analyzer with a sample idea"""
    
    print("=" * 80)
    print("Testing Dimensional Analyzer")
    print("=" * 80)
    
    # Initialize analyzer
    try:
        analyzer = DimensionalAnalyzer()
        print("✅ Dimensional analyzer initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {e}")
        return
    
    # Sample idea context
    idea_context = {
        'raw_idea': """
        A mobile app that helps college students find compatible study partners
        based on their courses, learning styles, and schedules. The app would
        match students taking the same classes who have overlapping free time
        and complementary study preferences (visual vs. auditory learners,
        group vs. one-on-one, etc.).
        """,
        'validation_profile': {
            'target_market': 'College students',
            'problem_intensity': 'High during exam periods',
            'current_solutions': 'Facebook groups, random pairings'
        },
        'market_insights': {
            'market_size': 'Large (millions of college students)',
            'competition': 'Informal solutions exist',
            'willingness_to_pay': 'Unknown'
        }
    }
    
    print("📝 Sample Idea:")
    print(idea_context['raw_idea'].strip())
    print("\n" + "=" * 80)
    print("🔍 Running Dimensional Analysis...\n")
    
    # Run analysis
    try:
        result = analyzer.analyze_dimensions(idea_context)
        
        print("✅ Analysis Complete!\n")
        print("=" * 80)
        print("📊 DIMENSIONAL SCORES")
        print("=" * 80)
        
        scores = result['scores']
        
        # Display each dimension
        dimensions = [
            ('Problem Clarity', 'problem_clarity'),
            ('Problem Significance', 'problem_significance'),
            ('Solution Specificity', 'solution_specificity'),
            ('Technical Complexity', 'technical_complexity'),
            ('Market Validation', 'market_validation'),
            ('Technical Viability', 'technical_viability'),
            ('Differentiation', 'differentiation'),
            ('Scalability', 'scalability')
        ]
        
        for name, key in dimensions:
            value = scores.get(key, 0)
            if isinstance(value, float):
                percentage = int(value * 100)
                bar = '█' * (percentage // 5) + '░' * (20 - percentage // 5)
                print(f"{name:25} [{bar}] {percentage}%")
            else:
                print(f"{name:25} {value.upper()}")
        
        print("\n" + "=" * 80)
        print("🏷️  DOMAIN CLASSIFICATION")
        print("=" * 80)
        
        domains = result.get('domain', [])
        confidence = result.get('domain_confidence', 0)
        
        print(f"Domains: {', '.join(domains)}")
        print(f"Confidence: {int(confidence * 100)}%")
        
        print("\n" + "=" * 80)
        print("🎯 OVERALL ASSESSMENT")
        print("=" * 80)
        
        overall_score = analyzer.calculate_overall_score(scores)
        interpretation = analyzer.get_score_interpretation(overall_score)
        
        print(f"Overall Score: {int(overall_score * 100)}%")
        print(f"Level: {interpretation['level'].upper()}")
        print(f"Assessment: {interpretation['emoji']} {interpretation['message']}")
        
        print("\n" + "=" * 80)
        print("📄 RAW JSON OUTPUT")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_multiple_ideas():
    """Test with multiple different ideas"""
    
    ideas = [
        {
            'name': 'Study Partner Matcher',
            'context': {
                'raw_idea': 'Mobile app to match college students for study groups based on courses and learning styles',
                'validation_profile': {'target_market': 'College students'},
                'market_insights': {'market_size': 'Large'}
            }
        },
        {
            'name': 'AI Healthcare Navigator',
            'context': {
                'raw_idea': 'AI-powered platform to help international students navigate US healthcare system with multilingual support',
                'validation_profile': {'target_market': 'International students'},
                'market_insights': {'market_size': 'Niche but growing'}
            }
        },
        {
            'name': 'Freelance Payment Automation',
            'context': {
                'raw_idea': 'Automated invoicing and payment collection for freelancers with automatic late fee calculation',
                'validation_profile': {'target_market': 'Freelancers'},
                'market_insights': {'market_size': 'Very large', 'competition': 'High'}
            }
        }
    ]
    
    analyzer = DimensionalAnalyzer()
    
    print("\n" + "=" * 80)
    print("TESTING MULTIPLE IDEAS")
    print("=" * 80)
    
    results = []
    
    for idea in ideas:
        print(f"\n📝 {idea['name']}")
        print("-" * 80)
        
        result = analyzer.analyze_dimensions(idea['context'])
        overall = analyzer.calculate_overall_score(result['scores'])
        interp = analyzer.get_score_interpretation(overall)
        
        print(f"Overall Score: {int(overall * 100)}% - {interp['emoji']} {interp['level'].upper()}")
        print(f"Domains: {', '.join(result['domain'])}")
        
        results.append({
            'name': idea['name'],
            'score': overall,
            'domains': result['domain']
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY COMPARISON")
    print("=" * 80)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    for i, result in enumerate(results, 1):
        score_pct = int(result['score'] * 100)
        print(f"{i}. {result['name']:30} {score_pct}%  ({', '.join(result['domains'])})")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Dimensional Analyzer')
    parser.add_argument('--multiple', action='store_true', help='Test with multiple ideas')
    
    args = parser.parse_args()
    
    if args.multiple:
        test_multiple_ideas()
    else:
        test_dimensional_analyzer()
