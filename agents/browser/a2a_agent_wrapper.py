from collections.abc import AsyncIterable
from typing import Any
from google.genai import types as genai_types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Import the existing ADK agent creation coroutine
from agents.browser.agent import create_agent as create_browser_adk_agent # Renamed for clarity

# A default user_id for ADK runner, A2A may provide its own session/user context
DEFAULT_ADK_USER_ID = "a2a_user"

session_service = InMemorySessionService()

class BrowserA2AWrapper:
    SUPPORTED_CONTENT_TYPES = ["text"]

    def __init__(self):
        # Agent and runner will be initialized asynchronously
        self._agent = None
        self._runner = None
        self._exit_stack = None
        # The user_id for ADK sessions can be mapped from A2A session/user if needed
        # For simplicity, using a default one for now.
        self._user_id = DEFAULT_ADK_USER_ID

    @classmethod
    async def create(cls):
        """Asynchronously creates and initializes the NotionA2AWrapper."""
        wrapper = cls()
        wrapper._underlying_agent, wrapper._exit_stack = await create_browser_adk_agent()
        wrapper._runner = Runner(
            session_service=session_service,
            agent=wrapper._underlying_agent,
            app_name="browser_agent", # Consistent with original
        )
        return wrapper

    async def close(self):
        """Closes any resources, like the MCP exit_stack."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            print("BrowserA2AWrapper: MCP exit_stack closed.")

    def get_processing_message(self) -> str:
        return "The Browser agent is thinking..."

    async def invoke(self, query: str, session_id: str) -> str:
        if not self._runner or not self._underlying_agent:
            raise RuntimeError("Agent not initialized. Call create() first.")

        # Ensure session_id from A2A is used for ADK session
        session = self._runner.session_service.get_session(
            app_name=self._runner.app_name,
            user_id=self._user_id,
            session_id=session_id,
        )

        user_content = genai_types.Content(
            role='user', parts=[genai_types.Part.from_text(text=query)]
        )

        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._runner.app_name,
                user_id=self._user_id,
                state={}, # Initial state
                session_id=session_id,
            )

        # Runner.run is synchronous, but since we are in an async def,
        # it's better to use run_async and then process its result if we need to adapt.
        # However, the original 'invoke' was synchronous, implying it expects a single response.
        # Let's keep the synchronous run() for now, but be mindful if it causes blocking issues in A2A.
        # For a truly async invoke, one would typically use run_async and collect results.
        # Given A2A's invoke is also async now, we can directly use run_async and get the last event.

        events = []
        async for event in self._runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                new_message=user_content,
            ):
            events.append(event)

        if not events or not events[-1].content or not events[-1].content.parts:
            return '' # Or some error/empty message

        # Combine text parts from the last event
        response_text = '\\n'.join(
            [p.text for p in events[-1].content.parts if p.text is not None]
        )
        return response_text

    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        if not self._runner or not self._underlying_agent:
            raise RuntimeError("Agent not initialized. Call create() first.")

        # Ensure session_id from A2A is used for ADK session
        session = self._runner.session_service.get_session(
            app_name=self._runner.app_name,
            user_id=self._user_id,
            session_id=session_id,
        )

        user_content = genai_types.Content(
            role='user', parts=[genai_types.Part.from_text(text=query)]
        )

        if session is None:
            session = self._runner.session_service.create_session(
                app_name=self._runner.app_name,
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
                    text_parts = [p.text for p in event.content.parts if p.text is not None]
                    if text_parts:
                        response_content = '\\n'.join(text_parts)

                yield {
                    'is_task_complete': True,
                    'content': response_content,
                }
            elif event.content and event.content.parts:
                intermediate_text_parts = [p.text for p in event.content.parts if p.text is not None]
                if intermediate_text_parts:
                    yield {
                        'is_task_complete': False,
                        'updates': '\\n'.join(intermediate_text_parts),
                    }
            else:
                 yield {
                    'is_task_complete': False,
                    'updates': self.get_processing_message(),
                } 