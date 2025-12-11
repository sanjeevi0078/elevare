#!/usr/bin/env python3
"""
Elevare MCP Server - True Model Context Protocol Implementation
================================================================

This server exposes Elevare's 7 powerful startup tools to external AI agents
via the official Model Context Protocol (MCP).

**What this enables:**
- Claude Desktop can directly invoke Elevare's tools
- ChatGPT plugins can access startup validation capabilities
- Any MCP-compatible client can leverage Elevare's autonomous agent toolkit

**Tools Exposed:**
1. validate_and_score_idea - AI-powered startup idea validation
2. find_compatible_cofounders - Intelligent cofounder matching
3. get_market_profile - Market viability analysis via Google Trends
4. ecosystem_discovery_tool - RAG-powered startup guidance (5 knowledge domains)
5. find_funding_options - Funding source recommendations
6. analyze_legal_requirements - Legal compliance analysis
7. send_team_notification - Real-time team communication bridge

**How to run:**
    python mcp_server.py

**How to connect:**
    Configure your MCP client (e.g., Claude Desktop) to connect to this stdio server.
    See PHASE_5_COMPLETE.md for detailed instructions.
"""

import asyncio
import os
import sys
import json
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# --- CRITICAL: Import our existing, powerful tools ---
print("🔧 Loading Elevare agent tools...", file=sys.stderr)

try:
    from services.agent_tools import (
        validate_and_score_idea,
        find_compatible_cofounders,
        get_market_profile,
        ecosystem_discovery_tool,
        find_funding_options,
        analyze_legal_requirements,
        send_team_notification
    )
    print("✅ All 7 Elevare tools loaded successfully", file=sys.stderr)
except Exception as e:
    print(f"❌ Error loading tools: {e}", file=sys.stderr)
    sys.exit(1)

# Create a map of our LangChain tools for easy lookup
ELEVARE_TOOLS = {
    "validate_and_score_idea": validate_and_score_idea,
    "find_compatible_cofounders": find_compatible_cofounders,
    "get_market_profile": get_market_profile,
    "ecosystem_discovery_tool": ecosystem_discovery_tool,
    "find_funding_options": find_funding_options,
    "analyze_legal_requirements": analyze_legal_requirements,
    "send_team_notification": send_team_notification,
}

# Initialize the MCP Server
app = Server("elevare-startup-support-v1")

print(f"🚀 Initializing Elevare MCP Server (v1.0.0)", file=sys.stderr)
print(f"📦 Exposing {len(ELEVARE_TOOLS)} tools to MCP clients", file=sys.stderr)


@app.list_tools()
async def list_elevare_tools() -> list[Tool]:
    """
    Returns all 7 of our agent tools, formatted for MCP.
    
    This is called by MCP clients to discover available capabilities.
    """
    print("📋 MCP Client requested tool list", file=sys.stderr)
    
    mcp_tools = []
    for name, tool in ELEVARE_TOOLS.items():
        try:
            # Convert our Pydantic input schemas to MCP's JSON Schema format
            if hasattr(tool, 'args_schema') and tool.args_schema:
                # Get the Pydantic schema
                schema = tool.args_schema.model_json_schema()
                
                # MCP expects a specific format
                input_schema = {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            else:
                # Fallback for tools without explicit schemas
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            mcp_tools.append(
                Tool(
                    name=name,
                    description=tool.description or f"Elevare tool: {name}",
                    inputSchema=input_schema
                )
            )
            print(f"  ✅ Registered: {name}", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not register {name}: {e}", file=sys.stderr)
    
    print(f"✅ Returning {len(mcp_tools)} tools to client", file=sys.stderr)
    return mcp_tools


@app.call_tool()
async def call_elevare_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """
    Receives a tool call from an external agent (like Claude Desktop),
    finds our corresponding LangChain tool, and executes it.
    
    Args:
        name: The name of the tool to execute
        arguments: Dictionary of arguments to pass to the tool
    
    Returns:
        List of TextContent containing the tool's response
    """
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"🔧 MCP Tool Call: {name}", file=sys.stderr)
    print(f"📥 Arguments: {json.dumps(arguments, indent=2)}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    
    if name not in ELEVARE_TOOLS:
        error_msg = f"❌ Unknown tool: {name}. Available tools: {list(ELEVARE_TOOLS.keys())}"
        print(error_msg, file=sys.stderr)
        raise ValueError(error_msg)

    # Get the LangChain tool
    tool_to_run = ELEVARE_TOOLS[name]

    try:
        print(f"⚙️  Executing {name}...", file=sys.stderr)
        
        # Execute the tool using its 'ainvoke' method
        # This calls our existing logic (httpx calls, RAG, Groq LLM, etc.)
        result = await tool_to_run.ainvoke(arguments)
        
        print(f"✅ Tool '{name}' executed successfully", file=sys.stderr)
        print(f"📤 Result preview: {str(result)[:200]}...", file=sys.stderr)
        
        # Convert result to string if needed
        if isinstance(result, dict):
            result_text = json.dumps(result, indent=2)
        elif isinstance(result, str):
            result_text = result
        else:
            result_text = str(result)
        
        # Return as MCP TextContent
        return [
            TextContent(
                type="text",
                text=result_text
            )
        ]
        
    except Exception as e:
        error_msg = f"❌ Error executing tool '{name}': {str(e)}"
        print(error_msg, file=sys.stderr)
        
        # Import traceback for detailed error logging
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        # Return error as TextContent (don't raise, let client handle it)
        return [
            TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )
        ]


async def main():
    """Main entry point for the MCP server."""
    print("\n" + "="*60, file=sys.stderr)
    print("🚀 Starting Elevare MCP Server", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    # Verify environment
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  WARNING: GROQ_API_KEY not set!", file=sys.stderr)
        print("   Tools requiring LLM reasoning will fail.", file=sys.stderr)
        print("   Set it in .env or export GROQ_API_KEY=your-key", file=sys.stderr)
    else:
        print("✅ GROQ_API_KEY configured", file=sys.stderr)
    
    print("\n📡 Server Status:", file=sys.stderr)
    print(f"   Mode: stdio (Standard Input/Output)", file=sys.stderr)
    print(f"   Protocol: Model Context Protocol (MCP)", file=sys.stderr)
    print(f"   Tools: {len(ELEVARE_TOOLS)} agent tools exposed", file=sys.stderr)
    print(f"   Backend: Groq Llama 3.3 70B + HuggingFace embeddings", file=sys.stderr)
    
    print("\n🔌 Waiting for MCP client connection...", file=sys.stderr)
    print("   (Claude Desktop, ChatGPT, or other MCP clients)", file=sys.stderr)
    print("\n" + "="*60 + "\n", file=sys.stderr)
    
    # Run the server on stdio
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ Elevare MCP Server shutdown gracefully", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
