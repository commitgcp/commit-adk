import uuid

from collections.abc import Callable

from common.client import A2AClient
from common.types import (
    AgentCard,
    Task,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)


TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard):
        self.agent_client = A2AClient(agent_card)
        self.card = agent_card

        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_task(
        self,
        request: TaskSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | None:
        if self.card.capabilities.streaming:
            # Initialize a Task object to be populated from stream events
            current_task_state = Task(
                id=request.id,
                sessionId=request.sessionId,
                status=TaskStatus(
                    state=TaskState.SUBMITTED, # Initial state
                    message=request.message   # Initial message from request
                ),
                history=[request.message], # Start history with the request message
                artifacts=[], # Initialize as an empty list
                metadata=request.metadata # Carry over task metadata from request
            )

            if task_callback:
                # Notify callback about the initial submitted state
                task_callback(current_task_state, self.card)

            async for response_wrapper in self.agent_client.send_task_streaming(
                request.model_dump() # Send original request params
            ):
                event_data = response_wrapper.result # This is TaskStatusUpdateEvent or TaskArtifactUpdateEvent
                
                # It's important that event_data itself (TaskStatusUpdateEvent/TaskArtifactUpdateEvent)
                # does not have its metadata merged from the top-level request,
                # but its sub-objects like status.message might.

                if isinstance(event_data, TaskStatusUpdateEvent):
                    current_task_state.status = event_data.status
                    if current_task_state.status.message:
                        # Merge metadata for the message part of the status
                        merge_metadata(current_task_state.status.message, request.message)
                        m = current_task_state.status.message
                        if not m.metadata:
                            m.metadata = {}
                        # Preserve original message_id if present, then add new one
                        if 'message_id' in m.metadata and m.metadata['message_id'] != request.message.metadata.get('message_id'):
                             m.metadata['last_message_id'] = m.metadata['message_id']
                        m.metadata['message_id'] = str(uuid.uuid4())


                elif isinstance(event_data, TaskArtifactUpdateEvent):
                    if current_task_state.artifacts is None: # Should be initialized as []
                        current_task_state.artifacts = []
                    # TODO: Handle artifact append/index logic if needed by A2A spec for complex artifacts
                    current_task_state.artifacts.append(event_data.artifact)
                    # Artifacts themselves might have metadata, but usually not merged from request.message

                if task_callback:
                    # Callback receives the raw event (TaskStatusUpdateEvent or TaskArtifactUpdateEvent)
                    task_callback(event_data, self.card) 

                if hasattr(event_data, 'final') and event_data.final:
                    break
            
            # After stream, current_task_state should reflect the final state
            return current_task_state
        
        # Non-streaming
        response = await self.agent_client.send_task(request.model_dump())
        # For non-streaming, response.result is already a Task object
        final_task_result = response.result # This is a Task object
        
        # Merge metadata for the task itself
        merge_metadata(final_task_result, request) # Merges request.metadata into final_task_result.metadata

        # Merge metadata for the message within the task's status
        if final_task_result.status and final_task_result.status.message:
            merge_metadata(final_task_result.status.message, request.message)
            m = final_task_result.status.message
            if not m.metadata:
                m.metadata = {}
            if 'message_id' in m.metadata and m.metadata['message_id'] != request.message.metadata.get('message_id'):
                m.metadata['last_message_id'] = m.metadata['message_id']
            m.metadata['message_id'] = str(uuid.uuid4())

        if task_callback:
            # Callback receives the final Task object for non-streaming
            task_callback(final_task_result, self.card)
        
        return final_task_result


def merge_metadata(target, source):
    # Ensure both target and source have 'metadata' attributes and they are dictionaries
    if not hasattr(target, 'metadata') or not isinstance(getattr(target, 'metadata', None), dict):
        # If target has no metadata or it's not a dict, try to initialize it if source has metadata
        if hasattr(source, 'metadata') and isinstance(getattr(source, 'metadata', None), dict) and source.metadata:
            target.metadata = dict(**source.metadata)
            # After initializing, target.metadata is now a dict, so proceed to merge if possible
        else:
            # If source also doesn't have valid metadata, or target can't be initialized, nothing to do.
            return

    # At this point, target.metadata should be a dictionary if it was initializable.
    # If it's still not a dict (e.g. source had no metadata), we can't proceed.
    if not isinstance(getattr(target, 'metadata', None), dict):
        return

    if not hasattr(source, 'metadata') or not isinstance(getattr(source, 'metadata', None), dict) or not source.metadata:
        return # Nothing to merge from source if its metadata is invalid or empty

    # Now, target.metadata is a dict, and source.metadata is a dict and not None/empty
    target.metadata.update(source.metadata)
