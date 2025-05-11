import os
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

async def get_notion_tools():
    """Gets tools from the File System MCP Server."""
    print("Attempting to connect to MCP Filesystem server...")
    tools, exit_stack = await MCPToolset.from_server(
        # Use StdioServerParameters for local process communication
        connection_params=StdioServerParameters(
            command="npx",  # Command to run the server
            args=[
                "-y",
                "@notionhq/notion-mcp-server"
            ],
            env={
                "OPENAPI_MCP_HEADERS": 
                f"{{\"Authorization\": \"Bearer {NOTION_API_KEY}\", \"Notion-Version\": \"2022-06-28\" }}"
            }
        )
    )
    print("MCP Toolset created successfully.")
    return tools, exit_stack






