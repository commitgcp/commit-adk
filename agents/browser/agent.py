import asyncio
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from .tools import get_browser_tools
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_after_model_modifier(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name
    logger.info(f"[Callback] After model call for agent: {agent_name}")

    # --- Inspection ---
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            logger.info(f"[Callback] Inspected original response text: '{original_text}'") # Log snippet
        elif llm_response.content.parts[0].function_call:
             logger.info(f"[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification.")
             return None # Don't modify tool calls in this example
        else:
             logger.info("[Callback] Inspected response: No text content found.")
             return None
    elif llm_response.error_message:
        logger.info(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None
    else:
        logger.info("[Callback] Inspected response: Empty LlmResponse.")
        return None # Nothing to modify

async def create_agent():
    browser_tools, exit_stack = await get_browser_tools()
    notion_agent = Agent(
        model="gemini-2.5-flash-preview-04-17",
        name="browser_agent",
        instruction="You are a browser agent that has full access to a browser.",
        description="An agent that has full access to a browser and can perform any task that a human can do with a browser.",
        tools=browser_tools,
        generate_content_config=GenerateContentConfig(
            temperature=0,
        ),
        planner=BuiltInPlanner(thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=1000)),
        after_model_callback=simple_after_model_modifier,
    )
    return notion_agent, exit_stack

root_agent = create_agent()