#!/usr/bin/env python3
"""
WebSocket Test Client for Phase 4 Collaboration
Demonstrates real-time team communication and agent notifications.
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

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

async def websocket_client(team_id="demo-team", username="User"):
    """
    Connect to team WebSocket and handle messages.
    
    Args:
        team_id: The team identifier
        username: Display name for this user
    """
    uri = f"ws://localhost:8000/api/v1/collaboration/ws/team/{team_id}"
    
    print_colored(f"\n{'='*60}", 'HEADER')
    print_colored(f"WebSocket Client - Phase 4 Collaboration Demo", 'HEADER')
    print_colored(f"{'='*60}\n", 'HEADER')
    
    print_colored(f"Connecting to: {uri}", 'OKCYAN')
    print_colored(f"Team ID: {team_id}", 'OKCYAN')
    print_colored(f"Username: {username}\n", 'OKCYAN')
    
    try:
        async with websockets.connect(uri) as websocket:
            print_colored("✅ Connected to team chat!", 'OKGREEN')
            print_colored("Type messages to send (or 'quit' to exit)\n", 'WARNING')
            
            # Task to receive messages
            async def receive_messages():
                try:
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            msg_content = data.get('message', '')
                            timestamp = data.get('timestamp', '')
                            
                            # Format timestamp
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                time_str = dt.strftime('%H:%M:%S')
                            except:
                                time_str = timestamp[:8] if timestamp else ''
                            
                            # Color-code by message type
                            if msg_type == 'system':
                                print_colored(f"[{time_str}] 🔧 SYSTEM: {msg_content}", 'OKCYAN')
                            elif msg_type == 'agent_notification':
                                print_colored(f"\n[{time_str}] 🤖 AGENT NOTIFICATION:", 'OKGREEN')
                                print_colored(f"{msg_content}\n", 'OKGREEN')
                            elif msg_type == 'user_joined':
                                print_colored(f"[{time_str}] ➕ {msg_content}", 'OKBLUE')
                            elif msg_type == 'user_left':
                                print_colored(f"[{time_str}] ➖ {msg_content}", 'WARNING')
                            elif msg_type == 'user_message':
                                print_colored(f"[{time_str}] 💬 {msg_content}", 'ENDC')
                            else:
                                print_colored(f"[{time_str}] {msg_type}: {msg_content}", 'ENDC')
                                
                        except json.JSONDecodeError:
                            # Plain text message
                            print_colored(f"📨 {message}", 'ENDC')
                            
                except websockets.exceptions.ConnectionClosed:
                    print_colored("\n❌ Connection closed by server", 'FAIL')
            
            # Task to send messages
            async def send_messages():
                while True:
                    try:
                        message = await asyncio.get_event_loop().run_in_executor(
                            None, input
                        )
                        
                        if message.strip().lower() == 'quit':
                            print_colored("Disconnecting...", 'WARNING')
                            break
                        
                        if message.strip():
                            await websocket.send(message)
                            
                    except EOFError:
                        break
            
            # Run both tasks concurrently
            await asyncio.gather(
                receive_messages(),
                send_messages()
            )
            
    except websockets.exceptions.ConnectionRefused:
        print_colored("\n❌ Connection refused. Is the server running?", 'FAIL')
        print_colored("Start server with: uvicorn main:app --reload --port 8000", 'WARNING')
    except Exception as e:
        print_colored(f"\n❌ Error: {e}", 'FAIL')

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket Team Chat Client')
    parser.add_argument(
        '--team', 
        default='demo-team', 
        help='Team ID to join (default: demo-team)'
    )
    parser.add_argument(
        '--username', 
        default='User', 
        help='Your display name (default: User)'
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(websocket_client(args.team, args.username))
    except KeyboardInterrupt:
        print_colored("\n\n✅ Disconnected", 'OKGREEN')
        sys.exit(0)

if __name__ == "__main__":
    main()
