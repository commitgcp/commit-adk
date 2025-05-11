from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)
import requests
from langchain_google_community.calendar.search_events import CalendarSearchEvents
from langchain_google_community.calendar.current_datetime import GetCurrentDatetime
from langchain_google_community.calendar.get_calendars_info import GetCalendarsInfo
from langchain_google_community.calendar.utils import (
    build_resource_service,
)
import google.auth
from google.adk.tools.langchain_tool import LangchainTool
from dotenv import load_dotenv
import os

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")

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

def linkedin_brief(raw_json):
    profile = raw_json.get("profile", {})
    brief = {}

    # Basic Info
    brief["full_name"] = profile.get("full_name")
    brief["headline"] = profile.get("headline")
    brief["occupation"] = profile.get("occupation")
    brief["location"] = ", ".join(filter(None, [profile.get("city"), profile.get("state"), profile.get("country_full_name")]))
    brief["profile_url"] = raw_json.get("url")
    brief["profile_pic_url"] = profile.get("profile_pic_url")
    brief["connections"] = profile.get("connections")
    brief["followers"] = profile.get("follower_count")

    # Experiences
    experiences = []
    for exp in profile.get("experiences", []):
        if exp.get("company") or exp.get("title"):
            experiences.append({
                "company": exp.get("company"),
                "title": exp.get("title"),
                "location": exp.get("location"),
                "start": exp.get("starts_at"),
                "end": exp.get("ends_at"),
            })
    if experiences:
        brief["experiences"] = experiences

    # Education
    education = []
    for edu in profile.get("education", []):
        if edu.get("school") or edu.get("degree_name"):
            education.append({
                "school": edu.get("school"),
                "degree": edu.get("degree_name"),
                "field": edu.get("field_of_study"),
                "start": edu.get("starts_at"),
                "end": edu.get("ends_at"),
            })
    if education:
        brief["education"] = education

    # Certifications
    certifications = []
    for cert in profile.get("certifications", []):
        if cert.get("name"):
            certifications.append({
                "name": cert.get("name"),
                "authority": cert.get("authority"),
                "start": cert.get("starts_at"),
                "end": cert.get("ends_at"),
                "url": cert.get("url"),
            })
    if certifications:
        brief["certifications"] = certifications

    # Activities
    activities = []
    for act in profile.get("activities", []):
        if act.get("title"):
            activities.append({
                "title": act.get("title"),
                "link": act.get("link"),
                "status": act.get("activity_status"),
            })
    if activities:
        brief["recent_activities"] = activities

    # Remove empty fields
    brief = {k: v for k, v in brief.items() if v}

    return brief

def scrape_linkedin_profile(company_domain: str, first_name: str, last_name: str) -> dict:
    """
    Fetches and summarizes a LinkedIn profile using the Proxycurl API, or returns a mock response for development/testing.

    Args:
        company_domain (str): The domain of the company associated with the person (e.g., 'comm-it.com').
        first_name (str): The first name of the person.
        last_name (str): The last name of the person. (Optional, can be an empty string)

    Returns:
        dict: A filtered and formatted brief of the LinkedIn profile, containing only relevant, non-empty fields.
    """
    # similarity_checks and enrich_profile are hardcoded as per API requirements
    api_endpoint = 'https://nubela.co/proxycurl/api/linkedin/profile/resolve'
    headers = {'Authorization': 'Bearer ' + PROXYCURL_API_KEY}
    params = {
        'company_domain': company_domain,
        'first_name': first_name,
        'last_name': last_name,
        'similarity_checks': 'include',
        'enrich_profile': 'enrich',
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    raw_response = response.json()
    return linkedin_brief(raw_response)

    # # Using mock response:
    # mock_response = {
    #     "url": f"https://www.linkedin.com/in/{first_name.lower()}{last_name.lower()}",
    #     "profile": {
    #         "full_name": f"{first_name} {last_name}",
    #         "headline": "Cloud Architect at Commit",
    #         "occupation": "Cloud Architect at Commit (Formerly Comm-IT)",
    #         "city": "Petah Tikva",
    #         "state": "Center District",
    #         "country_full_name": "Israel",
    #         "profile_pic_url": "https://s3.us-west-000.backblazeb2.com/proxycurl/person/jonathanjalfon/profile?...",
    #         "connections": 500,
    #         "follower_count": 1472,
    #         "experiences": [
    #             {
    #                 "company": "Commit (Formerly Comm-IT)",
    #                 "title": "Cloud Architect",
    #                 "location": "Petaẖ Tiqwa, Central, Israel",
    #                 "starts_at": {"day": 1, "month": 10, "year": 2022},
    #                 "ends_at": None
    #             },
    #             {
    #                 "company": "Sela Group",
    #                 "title": "DevOps Consultant",
    #                 "location": None,
    #                 "starts_at": {"day": 1, "month": 12, "year": 2020},
    #                 "ends_at": {"day": 31, "month": 10, "year": 2022}
    #             }
    #         ],
    #         "education": [
    #             {
    #                 "school": "Sela College",
    #                 "degree_name": "Associate's degree",
    #                 "field_of_study": "Computer Software Engineering",
    #                 "starts_at": {"day": 1, "month": 1, "year": 2019},
    #                 "ends_at": {"day": 31, "month": 1, "year": 2020}
    #             }
    #         ],
    #         "certifications": [
    #             {
    #                 "name": "Google Cloud Certified Professional Cloud Architect",
    #                 "authority": "Google",
    #                 "starts_at": {"day": 1, "month": 4, "year": 2023},
    #                 "ends_at": {"day": 30, "month": 4, "year": 2025},
    #                 "url": "https://google.accredible.com/7357a0d1-e261-431a-be57-0b103b2f6201?..."
    #             }
    #         ],
    #         "activities": [
    #             {
    #                 "title": "Just wanted to share that I recently completed the 'Leadership' course...",
    #                 "link": "https://www.linkedin.com/posts/andrey-dzhezhora-...",
    #                 "activity_status": f"Liked by {first_name} {last_name}"
    #             }
    #         ]
    #     }
    # }
    # return linkedin_brief(mock_response)

def get_calendar_tools():
    credentials, _ = google.auth.default()
    api_resource = build_resource_service(credentials=credentials)
    calendar_tools = [
        LangchainTool(tool=CalendarSearchEvents(api_resource=api_resource)),
        LangchainTool(tool=GetCurrentDatetime(api_resource=api_resource)),
        LangchainTool(tool=GetCalendarsInfo(api_resource=api_resource)),
    ]
    return calendar_tools

def get_event_attendees(calendar_id: str, event_id: str) -> list:
    """
    Fetches the attendees of a specific Google Calendar event.

    Args:
        calendar_id (str): The ID of the calendar containing the event. (email address)
        event_id (str): The ID of the event.

    Returns:
        list: A list of attendee email addresses, or an empty list if none.
    """
    credentials, _ = google.auth.default()
    api_resource = build_resource_service(credentials=credentials)
    event = api_resource.events().get(calendarId=calendar_id, eventId=event_id).execute()
    attendees = event.get('attendees', [])
    return [attendee.get('email') for attendee in attendees if 'email' in attendee]