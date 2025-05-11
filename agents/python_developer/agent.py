from google.adk.agents import LlmAgent
from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.planners import BuiltInPlanner
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner 
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


root_agent = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="coding_agent",
    description="An agent that can write and execute Python code. Use this agent for tasks involving calculations, data processing, logical analysis, or any general-purpose programming needs. It can handle complex operations that might involve math, data manipulation, and algorithmic logic.",
    instruction="""You are a powerful coding assistant. Your primary task is to write and execute Python code to complete the user's request or to perform calculations and analysis delegated by other agents.
Always ensure your code is robust and handles potential edge cases.
""",
    code_executor=VertexAiCodeExecutor(
        resource_name="projects/606879766101/locations/us-central1/extensions/8487407331733143552",
        optimize_data_file=True,
        stateful=False,
    ),
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=5000)
    ),
    generate_content_config=GenerateContentConfig(
        temperature=0,
    ),
    after_model_callback=simple_after_model_modifier
)

# Setup Runtime
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    app_name="python_developer",
)
