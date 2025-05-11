from collections.abc import AsyncIterable
from typing import Any
from google.genai import types as genai_types

# Import the existing ADK agent and runner
from agents.deep_research.agent import root_agent, runner

# A default user_id for ADK runner, A2A may provide its own session/user context
DEFAULT_ADK_USER_ID = "a2a_user"

class DeepResearchA2AWrapper:
    SUPPORTED_CONTENT_TYPES = ["text"]

    def __init__(self):
        self._agent = root_agent
        self._runner = runner
        # The user_id for ADK sessions can be mapped from A2A session/user if needed
        # For simplicity, using a default one for now.
        self._user_id = DEFAULT_ADK_USER_ID 

    def get_processing_message(self) -> str:
        return "The Deep Research agent is thinking..."

    def invoke(self, query: str, session_id: str) -> str:
        # Ensure session_id from A2A is used for ADK session
        # The ADK runner's app_name is already set to "deep_research"
        
        # Check if session exists, create if not
        session = self._runner.session_service.get_session(
            app_name=self._runner.app_name, # Use runner's app_name
            user_id=self._user_id,
            session_id=session_id,
        )
        
        user_content = genai_types.Content(
            role='user', parts=[genai_types.Part.from_text(text=query)]
        )

        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._runner.app_name, # Use runner's app_name
                user_id=self._user_id,
                state={}, # Initial state
                session_id=session_id,
            )

        events = list(
            self._runner.run(
                user_id=self._user_id, # Use the mapped/default user_id
                session_id=session.id, # Use the A2A provided session_id
                new_message=user_content,
            )
        )
        
        if not events or not events[-1].content or not events[-1].content.parts:
            return '' # Or some error/empty message
        
        # Combine text parts from the last event
        response_text = '\n'.join(
            [p.text for p in events[-1].content.parts if p.text is not None]
        )
        return response_text

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        # Ensure session_id from A2A is used for ADK session
        session = self._runner.session_service.get_session(
            app_name=self._runner.app_name, # Use runner's app_name
            user_id=self._user_id,
            session_id=session_id,
        )

        user_content = genai_types.Content(
            role='user', parts=[genai_types.Part.from_text(text=query)]
        )

        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._runner.app_name, # Use runner's app_name
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )

        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=user_content,
        ):
            if event.is_final_response():
                response_content = ''
                if event.content and event.content.parts:
                    # Check for text parts
                    text_parts = [p.text for p in event.content.parts if p.text is not None]
                    if text_parts:
                        response_content = '\n'.join(text_parts)
                    # Could also check for function_response or other part types if the agent uses them
                    # For now, primarily focusing on text output as per LlmAgent's typical behavior.

                yield {
                    'is_task_complete': True,
                    'content': response_content,
                }
            # ADK's LlmAgent might produce intermediate "thought" events or tool call events.
            # A2A's streaming expects progress updates.
            # We can map ADK's non-final events to A2A's "WORKING" state with a message.
            elif event.content and event.content.parts: # Intermediate content
                intermediate_text_parts = [p.text for p in event.content.parts if p.text is not None]
                if intermediate_text_parts:
                    yield {
                        'is_task_complete': False,
                        'updates': '\n'.join(intermediate_text_parts),
                    }
                # If there are tool calls or other non-text parts, decide how to represent them
                # For now, sticking to text updates or the generic processing message.

            else: # No specific content in this event, use generic message
                 yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                } 