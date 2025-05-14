import os
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)
from dotenv import load_dotenv

load_dotenv()

async def get_browser_tools():
    """Gets tools from the File System MCP Server."""
    print("Attempting to connect to MCP Filesystem server...")
    tools, exit_stack = await MCPToolset.from_server(
        # Use StdioServerParameters for local process communication
        connection_params=StdioServerParameters(
            command="npx",  # Command to run the server
            args=[
                "-y",
                "@playwright/mcp@latest",
            ]
        )
    )
    print("MCP Toolset created successfully.")
    return tools, exit_stack






