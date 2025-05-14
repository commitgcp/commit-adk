from .host_agent import HostAgent
from google.adk.agents import LlmAgent

python_dev_agent_address = "http://localhost:10000"
people_info_agent_address = "http://localhost:10001"
google_calendar_agent_address = "http://localhost:10002"
deep_research_agent_address = "http://localhost:10003"
notion_agent_address = "http://localhost:10004"
browser_agent_address = "http://localhost:10005"


root_agent = HostAgent(
    [
        python_dev_agent_address, 
        people_info_agent_address,
        google_calendar_agent_address,
        deep_research_agent_address,
        notion_agent_address,
        browser_agent_address
    ]
).create_agent()