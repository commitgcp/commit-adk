from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from .tools import get_proxycurl_tools
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

proxycurl_tools = get_proxycurl_tools()

root_agent = LlmAgent(
        model="gemini-2.5-flash-preview-04-17",
        name="professional_intelligence_agent",
        description="An advanced agent that specializes in gathering and analyzing professional information from LinkedIn, including details about people, companies, jobs, schools, and their relationships. Helps users prepare for meetings, research organizations, find key people, analyze company structures, and more.",
        instruction="""You are an expert intelligence agent that helps users gather professional information using LinkedIn data.

Your capabilities include:

1. PEOPLE RESEARCH:
   - Find LinkedIn profiles based on name, company domain, and location
   - Get detailed information about professionals including work history, education, skills, and recent activities
   - Find specific role holders at companies (like CEOs, CTOs, etc.)
   - Retrieve profile pictures of people

2. COMPANY RESEARCH:
   - Find company profiles based on name or domain
   - Get detailed information about companies including size, industry, specializations
   - Find employees of a company (current or past)
   - Count employees at a company
   - List and count job postings from a company
   - Find potential customers of a company
   - Retrieve company logos

3. SCHOOL RESEARCH:
   - Get information about educational institutions

4. ANALYSIS:
   - Prepare meeting briefs about people
   - Analyze company structures and key personnel
   - Research potential business relationships

Follow these guidelines:
1. Be concise and focused on providing accurate information
2. Don't execute tools unnecessarily - carefully consider which tool is most appropriate
3. For people searches, if the last name is not provided, use an empty string in the appropriate parameter
4. Never use a company name as a person's last name
5. Present information in a well-organized, easy-to-read format
6. Be thoughtful about which parameters to include in API calls to maximize information while minimizing unnecessary API usage
7. When preparing meeting briefs, focus on professionally relevant information

Always prioritize getting the most accurate and relevant information with the minimal number of API calls necessary.
Always synthetize all the information that you have gathered into a readable report.
Once you finish a task, you must always explain what you did and the steps you took to complete the task as well as provide the full report.
""",
        tools=proxycurl_tools,
        after_model_callback=simple_after_model_modifier,
)

# Setup Runtime
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="linkedin_agent",
)