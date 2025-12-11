#!/usr/bin/env python3
"""
AI Mentor CLI - Interactive startup guidance using Phase 4 RAG system
"""

import requests
import sys
import json

COLORS = {
    'HEADER': '\033[95m',
    'OKBLUE': '\033[94m',
    'OKCYAN': '\033[96m',
    'OKGREEN': '\033[92m',
    'WARNING': '\033[93m',
    'FAIL': '\033[91m',
    'ENDC': '\033[0m',
    'BOLD': '\033[1m',
}

def print_colored(message, color='ENDC'):
    print(f"{COLORS.get(color, '')}{message}{COLORS['ENDC']}")

def get_mentor_status():
    """Check if AI Mentor is operational."""
    try:
        response = requests.get("http://localhost:8000/api/v1/mentor/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_colored("\n✅ AI Mentor Status: OPERATIONAL", 'OKGREEN')
            print_colored(f"   Backend: {data['backend']}", 'OKCYAN')
            print_colored(f"   Knowledge Base: {data['knowledge_base']['documents']} documents", 'OKCYAN')
            return True
        else:
            print_colored(f"\n❌ Mentor unavailable: {response.status_code}", 'FAIL')
            return False
    except requests.exceptions.ConnectionError:
        print_colored("\n❌ Cannot connect to server. Is it running?", 'FAIL')
        print_colored("Start server with: uvicorn main:app --reload --port 8000", 'WARNING')
        return False
    except Exception as e:
        print_colored(f"\n❌ Error: {e}", 'FAIL')
        return False

def get_topics():
    """Fetch available knowledge domains."""
    try:
        response = requests.get("http://localhost:8000/api/v1/mentor/topics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_colored("\n📚 Available Knowledge Domains:", 'HEADER')
            print_colored("="*60, 'HEADER')
            
            for idx, topic in enumerate(data['topics'], 1):
                print_colored(f"\n{idx}. {topic['name']}", 'OKGREEN')
                print_colored(f"   {topic['description']}", 'ENDC')
                print_colored(f"   Example: \"{topic['example_question']}\"", 'OKCYAN')
            
            print_colored("\n" + "="*60, 'HEADER')
            return True
        else:
            print_colored(f"\n❌ Could not fetch topics: {response.status_code}", 'FAIL')
            return False
    except Exception as e:
        print_colored(f"\n❌ Error: {e}", 'FAIL')
        return False

def ask_question(question):
    """Ask AI Mentor a question."""
    if len(question) < 10:
        print_colored("❌ Question too short (min 10 characters)", 'FAIL')
        return False
    
    print_colored(f"\n🤖 Asking AI Mentor...", 'WARNING')
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/mentor/ask",
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print_colored("\n" + "="*60, 'OKGREEN')
            print_colored("AI MENTOR RESPONSE", 'OKGREEN')
            print_colored("="*60, 'OKGREEN')
            
            print_colored(f"\n📝 Question:", 'HEADER')
            print_colored(f"{data['question']}\n", 'ENDC')
            
            print_colored(f"💡 Answer:", 'OKGREEN')
            print_colored(f"{data['answer']}\n", 'ENDC')
            
            if data.get('sources'):
                print_colored(f"📚 Sources:", 'OKCYAN')
                print_colored(f"{data['sources'][:200]}...\n", 'OKCYAN')
            
            print_colored("="*60 + "\n", 'OKGREEN')
            return True
            
        elif response.status_code == 422:
            print_colored(f"❌ Invalid question format", 'FAIL')
            return False
        elif response.status_code == 500:
            error_data = response.json()
            print_colored(f"❌ Server error: {error_data.get('detail', 'Unknown error')}", 'FAIL')
            return False
        else:
            print_colored(f"❌ Unexpected response: {response.status_code}", 'FAIL')
            return False
            
    except requests.exceptions.Timeout:
        print_colored("❌ Request timeout (AI taking too long to respond)", 'FAIL')
        return False
    except Exception as e:
        print_colored(f"❌ Error: {e}", 'FAIL')
        return False

def interactive_mode():
    """Interactive Q&A mode."""
    print_colored("\n" + "="*60, 'HEADER')
    print_colored("AI MENTOR - Interactive Mode", 'HEADER')
    print_colored("="*60, 'HEADER')
    print_colored("\nCommands:", 'WARNING')
    print_colored("  'topics' - Show available knowledge domains", 'OKCYAN')
    print_colored("  'status' - Check mentor status", 'OKCYAN')
    print_colored("  'quit'   - Exit", 'OKCYAN')
    print_colored("\nOr type any startup question (min 10 characters)\n", 'WARNING')
    
    while True:
        try:
            question = input(f"{COLORS['BOLD']}Ask> {COLORS['ENDC']}").strip()
            
            if not question:
                continue
            
            if question.lower() == 'quit':
                print_colored("\n✅ Goodbye!", 'OKGREEN')
                break
            elif question.lower() == 'topics':
                get_topics()
            elif question.lower() == 'status':
                get_mentor_status()
            else:
                ask_question(question)
                
        except KeyboardInterrupt:
            print_colored("\n\n✅ Goodbye!", 'OKGREEN')
            break
        except EOFError:
            print_colored("\n\n✅ Goodbye!", 'OKGREEN')
            break

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Mentor CLI - Startup Guidance')
    parser.add_argument('question', nargs='*', help='Question to ask (or omit for interactive mode)')
    parser.add_argument('--topics', action='store_true', help='Show available topics')
    parser.add_argument('--status', action='store_true', help='Check mentor status')
    
    args = parser.parse_args()
    
    # Check server availability
    if not get_mentor_status():
        sys.exit(1)
    
    if args.topics:
        get_topics()
    elif args.status:
        pass  # Already shown in status check
    elif args.question:
        question = ' '.join(args.question)
        ask_question(question)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
