import asyncio
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from .tools import get_notion_tools
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from typing import Optional

def simple_after_model_modifier(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name
    print(f"[Callback] After model call for agent: {agent_name}")

    # --- Inspection ---
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            print(f"[Callback] Inspected original response text: '{original_text}'") # Log snippet
        elif llm_response.content.parts[0].function_call:
             print(f"[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification.")
             return None # Don't modify tool calls in this example
        else:
             print("[Callback] Inspected response: No text content found.")
             return None
    elif llm_response.error_message:
        print(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None
    else:
        print("[Callback] Inspected response: Empty LlmResponse.")
        return None # Nothing to modify

async def create_agent():
    notion_tools, exit_stack = await get_notion_tools()
    notion_agent = Agent(
        model="gemini-2.5-flash-preview-04-17",
        name="notion_agent",
        description="An agent that can interact with Notion, primarily focused on the 'Agent Collection' page and all the hierarchy of pages and databases under it.",
        instruction="""You are a versatile Notion assistant with full control over Notion using the available tools.
Your primary workspace is a specific Notion page named "Agent Collection" with the ID '1f123395-cca1-8095-b302-cbb724f3dc2b'.
When using tools that require a page ID or parent ID (like creating a page or appending blocks), always target this page ('1f123395-cca1-8095-b302-cbb724f3dc2b') or one of its subpages or databases.
Unless explicitly instructed to modify the main "Agent Collection" page, assume that new content, pages, or databases should be created under the "Agent Collection" page.
Carefully examine the required parameters for each tool, especially page IDs and parent IDs, to ensure you are operating within the correct context.

If you are asked to create a page and populate it with specific content, follow these steps:
1. Create the page using `API-post-page` as usual. Remember to use the correct parent ID ('1f123395-cca1-8095-b302-cbb724f3dc2b' or a subpage ID).
2. Take note of the `id` of the newly created page from the `API-post-page` response.
3. Format the provided content into Notion block objects. For plain text reports, split the text into paragraphs (separated by double newlines or similar logical breaks) and create a list of paragraph block objects. Example structure for two paragraphs: `[{\"type\": \"paragraph\", \"paragraph\": {\"rich_text\": [{\"type\": \"text\", \"text\": {\"content\": \"First paragraph text.\"}}]}}, {\"type\": \"paragraph\", \"paragraph\": {\"rich_text\": [{\"type\": \"text\", \"text\": {\"content\": \"Second paragraph text.\"}}]}}]`. You will need to construct the `children` argument for the next step using this format.
4. Call `API-patch-block-children` with the `block_id` set to the ID of the new page (obtained in step 2) and the `children` parameter containing the list of formatted block objects.
**Once you start a sequence like creating a page and populating it, complete all steps without asking for intermediate confirmation.**

If a request seems unrelated to managing Notion content within the "Agent Collection" page or its subpages, state that you cannot fulfill it and why.
Once you finish a task, you must always explain what you did and the steps you took to complete the task.
""",
        tools=notion_tools,
        generate_content_config=GenerateContentConfig(
            temperature=0,
        ),
        planner=BuiltInPlanner(thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=1000)),
        after_model_callback=simple_after_model_modifier,
    )
    return notion_agent, exit_stack

root_agent = create_agent()