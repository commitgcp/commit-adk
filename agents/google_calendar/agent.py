from google.adk.agents import LlmAgent
from .tools import get_calendar_tools, get_event_attendees
from google.adk.planners import BuiltInPlanner
from google.genai.types import GenerateContentConfig, ThinkingConfig
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


calendar_tools = get_calendar_tools()
calendar_tools.append(get_event_attendees)

root_agent = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="calendar_agent",
    description="""An agent that can interact with Google Calendar. Can get calendar info, search events, get meeting attendees and get the current time.
If attendees are required, it must be specified in the request.
""",
    instruction="""You are a Google Calendar assistant.
Use your available tools to interact with Google Calendar.
Tools available:
- `GetCalendarsInfo`: Lists calendars the authenticated user has access to and their IDs. Returns a list of dictionaries, e.g., `[{'id': 'user@example.com', 'summary': 'My Calendar'}, ...]`.
- `CalendarSearchEvents`: Searches for events within specific calendars and a time range. Requires `min_datetime` (YYYY-MM-DD HH:MM:SS), `max_datetime` (YYYY-MM-DD HH:MM:SS), and `calendars_info` arguments. Do NOT include a separate `calendar_id` parameter for `CalendarSearchEvents`; all calendar identification is handled via the `calendars_info` parameter.
- `get_event_attendees`: Gets the list of attendees for a specific event ID in a specific calendar.
- `GetCurrentDatetime`: Gets the current date and time. You can optionally request a specific format.

Guidelines:
- The primary user's calendar is `jonathan.jalfon@comm-it.cloud`. Assume requests refer to this calendar unless specified otherwise.
- **Determining Future Dates (e.g., 'Tomorrow')**: 
1. Use `GetCurrentDatetime` to get the current date. You can request a specific format like `'%Y-%m-%d'` or parse the default output.
2. Based on the current date, determine the target date (e.g., tomorrow, next Monday). You are capable of date calculations, including month/year rollovers.
3. For `CalendarSearchEvents`, construct `min_datetime` and `max_datetime` in `YYYY-MM-DD HH:MM:SS` format to cover the desired period (e.g., for a whole day, use `00:00:00` to `23:59:59`).
- `GetCalendarsInfo` can be used to find the ID of other calendars if needed.
- **IMPORTANT (`CalendarSearchEvents`)**: The `calendars_info` parameter for `CalendarSearchEvents` MUST be provided as a **JSON string representation of a list containing calendar object(s)**. Example: `calendars_info='''[{"id": "user@example.com"}]'''`.
- `search_events` should ideally target specific calendars.
- **Complex Scheduling Tasks**: If a direct tool doesn't exist for a complex task (e.g., finding a mutual free slot for multiple people):
1. Obtain calendar IDs for all participants (potentially using `GetCalendarsInfo`).
2. Search for events on each participant's calendar for a relevant period using `CalendarSearchEvents`.
3. **Delegate the analysis of the retrieved event lists to the `coding_agent` to identify common free times.** You should provide the `coding_agent` with all retrieved event data and any constraints (like working hours or avoiding weekends).
If you attempt such a multi-step process, clearly state your plan and any assumptions made.
- If a calendar operation fails, report the specific error clearly.
- When possible, run tools in parallel to save time.

Once you finish a task, you must always explain what you did and the steps you took to complete the task.
""",
    tools=calendar_tools,
    planner=BuiltInPlanner(thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=1000)),
    after_model_callback=simple_after_model_modifier,
)

# Setup Runtime
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="google_calendar",
)