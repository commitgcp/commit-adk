import logging
from collections.abc import AsyncIterable
from typing import Any

# Assuming a2a library is installed and common.server/types are accessible
# If not, these would need to be vendored or their paths adjusted.
from common.server import utils as a2a_utils
from common.server.task_manager import InMemoryTaskManager
from common.types import (
    Artifact,
    DataPart,
    InternalError,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from .a2a_agent_wrapper import LinkedinA2AWrapper

logger = logging.getLogger(__name__)

class LinkedinTaskManager(InMemoryTaskManager):
    def __init__(self, agent_wrapper: LinkedinA2AWrapper):
        super().__init__()
        self.agent_wrapper = agent_wrapper

    async def _stream_generator(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        if query is None: # Handle non-text input if necessary, or error out
            yield JSONRPCResponse(
                id=request.id,
                error=InternalError(message="Invalid input: Only text queries are supported."),
            )
            return

        try:
            async for item in self.agent_wrapper.stream(
                query, task_send_params.sessionId
            ):
                is_task_complete = item['is_task_complete']
                current_artifacts = None # Renamed from 'artifacts' to avoid conflict
                
                if not is_task_complete:
                    task_state = TaskState.WORKING
                    # Ensure item['updates'] is a string
                    update_text = str(item.get('updates', '')) 
                    parts = [TextPart(text=update_text)]
                else:
                    content = item.get('content', '')
                    if isinstance(content, dict): # For potential future structured output
                        # This part might need adjustment based on how the PythonDeveloperAgent formats structured output
                        task_state = TaskState.COMPLETED # Or INPUT_REQUIRED if it's a form
                        parts = [DataPart(data=content)] 
                    else:
                        task_state = TaskState.COMPLETED
                        # Ensure content is a string
                        content_text = str(content)
                        parts = [TextPart(text=content_text)]
                    current_artifacts = [Artifact(parts=parts, index=0, append=False)]
                
                message = Message(role='agent', parts=parts)
                task_status = TaskStatus(state=task_state, message=message)
                
                await self._update_store(
                    task_send_params.id, task_status, current_artifacts
                )
                
                task_update_event = TaskStatusUpdateEvent(
                    id=task_send_params.id,
                    status=task_status,
                    final=False, # This will be set to True later if is_task_complete
                )
                yield SendTaskStreamingResponse(
                    id=request.id, result=task_update_event
                )

                if current_artifacts:
                    for art in current_artifacts: # Renamed loop variable
                        yield SendTaskStreamingResponse(
                            id=request.id,
                            result=TaskArtifactUpdateEvent(
                                id=task_send_params.id,
                                artifact=art,
                                final=False, # Artifacts themselves aren't 'final' task events usually
                            ),
                        )
                
                if is_task_complete:
                    final_status_event = TaskStatusUpdateEvent(
                        id=task_send_params.id,
                        status=TaskStatus(state=task_status.state), # Send only state for final update
                        final=True,
                    )
                    yield SendTaskStreamingResponse(
                        id=request.id, result=final_status_event
                    )

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}', exc_info=True)
            yield JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message=f'An error occurred while streaming the response: {str(e)}'
                ),
            )

    def _validate_request(
        self, request: SendTaskRequest | SendTaskStreamingRequest
    ) -> JSONRPCResponse | None:
        task_send_params: TaskSendParams = request.params
        if not a2a_utils.are_modalities_compatible(
            task_send_params.acceptedOutputModes,
            self.agent_wrapper.SUPPORTED_CONTENT_TYPES,
        ):
            logger.warning(
                'Unsupported output mode. Received %s, Agent supports %s',
                task_send_params.acceptedOutputModes,
                self.agent_wrapper.SUPPORTED_CONTENT_TYPES,
            )
            return a2a_utils.new_incompatible_types_error(request.id)
        if not task_send_params.message or not task_send_params.message.parts:
             logger.warning('Received task with no message parts.')
             return JSONRPCResponse(id=request.id, error=InternalError(message="Task message parts are missing."))
        if not any(isinstance(part, TextPart) for part in task_send_params.message.parts):
            logger.warning('Received task with no text parts.')
            return JSONRPCResponse(id=request.id, error=InternalError(message="Only text input is supported."))
        return None

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        error_resp = self._validate_request(request)
        if error_resp:
            return error_resp
        
        await self.upsert_task(request.params)
        return await self._invoke(request)

    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        error_resp = self._validate_request(request)
        if error_resp:
            return error_resp
        
        await self.upsert_task(request.params)
        # The generator itself handles yielding JSONRPCResponse on internal errors
        return self._stream_generator(request) 

    async def _update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact] | None
    ) -> Task:
        async with self.lock:
            try:
                task = self.tasks[task_id]
            except KeyError:
                logger.error(f'Task {task_id} not found for updating.')
                # This case should ideally be handled by upsert_task before _update_store is called.
                # If upsert_task was called, this implies a race or logic error.
                raise ValueError(f'Task {task_id} not found during update. Ensure upsert_task was called.')
            
            task.status = status
            if artifacts:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)
            return task

    async def _invoke(self, request: SendTaskRequest) -> SendTaskResponse:
        task_send_params: TaskSendParams = request.params
        query = self._get_user_query(task_send_params)
        if query is None:
            return SendTaskResponse(
                id=request.id, 
                error=InternalError(message="Invalid input: Only text queries are supported.")
            )

        try:
            result_text = self.agent_wrapper.invoke(query, task_send_params.sessionId)
        except Exception as e:
            logger.error(f'Error invoking agent_wrapper: {e}', exc_info=True)
            # Update task state to FAILED before returning error
            fail_status = TaskStatus(state=TaskState.FAILED, message=Message(role='agent', parts=[TextPart(text=f"Agent invocation failed: {str(e)}")]))
            await self._update_store(task_send_params.id, fail_status, None)
            return SendTaskResponse(
                id=request.id, 
                error=InternalError(message=f'Error invoking agent: {str(e)}')
            )
        
        # Assuming simple text response for now
        # If PythonDeveloperAgent can signal INPUT_REQUIRED, this logic needs adjustment
        parts = [TextPart(text=str(result_text))]
        task_state = TaskState.COMPLETED 
        
        final_task_status = TaskStatus(state=task_state, message=Message(role='agent', parts=parts))
        final_artifacts = [Artifact(parts=parts)]

        task = await self._update_store(
            task_send_params.id,
            final_task_status,
            final_artifacts,
        )
        return SendTaskResponse(id=request.id, result=task)

    def _get_user_query(self, task_send_params: TaskSendParams) -> str | None:
        if task_send_params.message and task_send_params.message.parts:
            for part in task_send_params.message.parts:
                if isinstance(part, TextPart):
                    return part.text
        return None # No text part found 