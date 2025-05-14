from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.tools import google_search, agent_tool
from google.genai.types import GenerateContentConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
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

search_tool = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="search_tool",
    description="A tool that conducts research on a given topic",
    instruction="""You are a research specialist.
Your task is to conduct research on a given topic.
Your answer should be in the form of a report and based on the information found.
You must always reference the source of your information.
Conduct research as many times as needed in order to produce a comprehensive report.
You cannot use your own knowledge, only the information found.
""",
    tools=[google_search],
    output_key="research_results",
    generate_content_config=GenerateContentConfig(
        temperature=0,
    ),
    after_model_callback=simple_after_model_modifier,
)

initial_context_search = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="initial_context_search",
    description="An agent that does preliminary research on a given topic",
    instruction="You are a research assistant, your task is to do preliminary research on a given topic. and provide a concise summary for the research team to put them in context.",
    tools=[google_search],
    output_key="initial_context",
    generate_content_config=GenerateContentConfig(
        temperature=0,
    ),
    after_model_callback=simple_after_model_modifier,
)

formulate_research_question_agent = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="formulate_research_question_agent",
    description="An agent that formulates a research question",
    instruction="Formulate a research question based on the given topic",
    output_key="research_questions",
    generate_content_config=GenerateContentConfig(
        temperature=0.5,
    ),
    after_model_callback=simple_after_model_modifier,
)

report_writer_agent = LlmAgent(
    model="gemini-2.5-pro-preview-05-06",
    name="report_writer_agent",
    description="An agent that writes a report based on the research",
    instruction="""You are a professional writer.
You specialize in writing comprehensive and engaging reports based on the research provided.
You can structure the report in any way you want, but it should always contain a ## References section citing the sources used.""",
    output_key="report",
    generate_content_config=GenerateContentConfig(
        temperature=0,
    ),
    after_model_callback=simple_after_model_modifier,
)

loop_agent = LoopAgent(
    name="loop_agent",
    max_iterations=3,
    sub_agents=[formulate_research_question_agent, search_tool],
)

deep_research_tool = SequentialAgent(
    name="deep_research_tool",
    description="A long running process that involves several steps and generates a comprehensive report about a given topic.",
    sub_agents=[initial_context_search, loop_agent, report_writer_agent],
)

root_agent = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="deep_research_agent",
    description="A research assistant that can conduct deep research or quick search on a given topic.",
    instruction="""
You are a research assistant.
You can conduct deep research or quick search on a given topic.
You can use the `deep_research_tool` to conduct deep research.
You can use the `search_tool` to conduct a quick search.
You can use the `initial_context_search` to get an initial context for the research.

Always synthetize all the information that you have gathered into a readable report.
Once you finish a task, you must always explain what you did and the steps you took to complete the task as well as provide the full report.
""",
    tools=[agent_tool.AgentTool(deep_research_tool), agent_tool.AgentTool(search_tool), agent_tool.AgentTool(initial_context_search)],
    after_model_callback=simple_after_model_modifier,
)

session_service = InMemorySessionService()
runner = Runner(
    session_service=session_service,
    agent=root_agent,
    app_name="deep_research",
)