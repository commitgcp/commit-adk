from langchain_google_community.calendar.search_events import CalendarSearchEvents
from langchain_google_community.calendar.current_datetime import GetCurrentDatetime
from langchain_google_community.calendar.get_calendars_info import GetCalendarsInfo
from langchain_google_community.calendar.utils import build_resource_service
import google.auth
from google.adk.tools.langchain_tool import LangchainTool

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