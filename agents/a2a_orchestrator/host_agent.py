import base64
import json
import uuid
import sys
import os
COMMON_DIR_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if COMMON_DIR_PARENT not in sys.path:
    sys.path.append(COMMON_DIR_PARENT)
from common.client import A2ACardResolver
from common.types import (
    AgentCard,
    DataPart,
    Message,
    Part,
    Task,
    TaskSendParams,
    TaskState,
    TextPart,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.genai.types import GenerateContentConfig, ThinkingConfig

from .remote_agent_connection import RemoteAgentConnections, TaskUpdateCallback


class HostAgent:
    """The host agent.

    This is the agent responsible for choosing which remote agents to send
    tasks to and coordinate their work.
    """

    def __init__(
        self,
        remote_agent_addresses: list[str],
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
        self.cards: dict[str, AgentCard] = {}
        self._update_agents_summary_for_prompt()
        for address in remote_agent_addresses:
            card_resolver = A2ACardResolver(address)
            card = card_resolver.get_agent_card()
            remote_connection = RemoteAgentConnections(card)
            self.remote_agent_connections[card.name] = remote_connection
            self.cards[card.name] = card
        self._update_agents_summary_for_prompt()

    def _update_agents_summary_for_prompt(self):
        agent_descriptions = []
        if not self.cards:
            self.agents_summary_for_prompt = "No remote agents currently registered."
            return

        for card in self.cards.values():
            desc_str = f"Agent Name: {card.name}\\n"
            desc_str += f"  Description: {card.description}\\n"
            if hasattr(card, 'skills') and card.skills:
                desc_str += f"  Skills:\\n"
                for skill in card.skills:
                    skill_name = getattr(skill, 'name', 'Unnamed Skill')
                    skill_desc = getattr(skill, 'description', 'No description')
                    desc_str += f"    - Skill: {skill_name}\\n"
                    desc_str += f"      Description: {skill_desc}\\n"
            else:
                desc_str += "  Skills: Not specified.\\n"
            agent_descriptions.append(desc_str)
        self.agents_summary_for_prompt = "\\n\\n".join(agent_descriptions)

    def register_agent_card(self, card: AgentCard):
        remote_connection = RemoteAgentConnections(card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card
        self._update_agents_summary_for_prompt()

    def create_agent(self) -> Agent:
        return Agent(
            model='gemini-2.5-flash-preview-04-17',
            name='host_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description=(
                'This agent orchestrates the decomposition of the user request into'
                ' tasks that can be performed by the child agents.'
            ),
            tools=[
                self.list_remote_agents,
                self.send_task,
            ],
            planner=BuiltInPlanner(
                thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=8000)
            ),
            generate_content_config=GenerateContentConfig(
                temperature=0,
            ),
        )

    def root_instruction(self, context: ReadonlyContext) -> str:
        current_agent = self.check_state(context)
        return f"""You are an expert delegator and orchestrator that can delegate user requests to the
appropriate remote agents and coordinate their work to fulfill complex objectives.

**Core Responsibilities:**
1.  **Understand the User's Goal:** Carefully analyze the user's request to fully grasp their overall objective.
2.  **Leverage Available Agents:** Use the information below under "Available Agents and their Capabilities" to decide which agent(s) are best suited for each part of the request.
3.  **Plan and Execute:** For non-trivial requests that may involve multiple steps or agents, follow the detailed workflow outlined below.

**Discovery Tool:**
-   `list_remote_agents`: Use this tool if you need a fresh list of available remote agents (provides name and general description). You should primarily rely on the detailed list provided below.

**Execution Tool:**
-   `send_task`: Use this tool to delegate a specific, actionable task to a named remote agent. You MUST specify the `agent_name` and a detailed `message` for the agent.

**Workflow for Complex Requests (requiring multiple agents or steps):**

1.  **Decomposition & Planning:**
    a.  Break down the user's overall request into a series_of actionable, granular tasks.
    b.  For each task, identify the most suitable agent from the "Available Agents" list.
    c.  Organize these tasks hierarchically. Tasks that can be performed in parallel should be at the same level in the hierarchy. Tasks that depend on the output of other tasks must be placed at a subsequent level.
    d.  Present this plan to the user in a clear, structured format (e.g., numbered steps, indicating assigned agent, and noting parallelism or dependencies). Example:
        ```
        Here's my plan:
        1. Task A (Agent: coding_agent) - Input: User request details.
        2. Task B (Agent: deep_research_agent) - Input: User request details.
           (Tasks 1 and 2 can run in parallel)
        3. Task C (Agent: notion_agent) - Input: Output from Task A, Output from Task B.
        ```

2.  **User Confirmation:**
    a.  Explicitly ask the user to confirm the proposed plan *before* initiating any tasks.
    b.  If the user suggests modifications, revise the plan and seek confirmation again.

3.  **Execution (After User Confirmation):**
    a.  Execute the confirmed plan step-by-step, respecting the defined hierarchy and dependencies.
    b.  When a task is ready to be executed, use the `send_task` tool.
    c.  **Context is Key for Sub-Agents:** When constructing the `message` for `send_task`:
        i.  Provide the sub-agent with all necessary context. This includes the relevant part of the original user request, and crucially, any outputs from prerequisite tasks (if this task depends on them).
        ii. Instruct the sub-agent to perform its specific task and to return its *complete output, all generated data, and a clear explanation of its actions and results*. This ensures you have the necessary information for subsequent dependent tasks or for the final response to the user.
    d.  **Parallel Execution:** If your plan includes tasks that can be run in parallel, you can issue `send_task` calls for these tasks concurrently in your response when it's their turn to execute.
    e.  Inform the user about the progress, which tasks are being initiated, and upon completion of all tasks, provide a synthesized final answer.

**General Guidelines:**
-   Rely on your tools. Do not make up responses or assume agent capabilities beyond what is described.
-   If unsure, ask the user for clarification.
-   Focus on the most recent parts of the conversation, but ensure all necessary context from the current request is utilized.
-   If a task is directed at an agent that was already active (indicated by 'Current agent'), using `send_task` to that same agent will attempt to continue or update its existing task with the new message content. Be clear in your message if it's a continuation or a new instruction for an ongoing task.
-   Always provide the full info returned by agents, don't hide any details from the user.
-   Agents do not know about the operations of other agents, so don't ask them to do something that is not in their capabilities.
-   Agents are not aware of the state of the conversation so you must always provide the full context along with the task.

**Available Agents and their Capabilities:**
{self.agents_summary_for_prompt}

Current agent: {current_agent['active_agent']}
"""

    def check_state(self, context: ReadonlyContext):
        state = context.state
        if (
            'session_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'agent' in state
        ):
            return {'active_agent': f'{state["agent"]}'}
        return {'active_agent': 'None'}

    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True

    def list_remote_agents(self):
        """List the available remote agents you can use to delegate the task."""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {'name': card.name, 'description': card.description}
            )
        return remote_agent_info

    async def send_task(
        self, agent_name: str, message: str, tool_context: ToolContext
    ):
        """Sends a task either streaming (if supported) or non-streaming.

        This will send a message to the remote agent named agent_name.

        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.

        Yields:
          A dictionary of JSON data.
        """
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f'Agent {agent_name} not found')
        state = tool_context.state
        state['agent'] = agent_name
        card = self.cards[agent_name]
        client = self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')
        if 'task_id' in state:
            taskId = state['task_id']
        else:
            taskId = str(uuid.uuid4())
        sessionId = state['session_id']
        task: Task
        messageId = ''
        metadata = {}
        if 'input_message_metadata' in state:
            metadata.update(**state['input_message_metadata'])
            if 'message_id' in state['input_message_metadata']:
                messageId = state['input_message_metadata']['message_id']
        if not messageId:
            messageId = str(uuid.uuid4())
        metadata.update(conversation_id=sessionId, message_id=messageId)
        request: TaskSendParams = TaskSendParams(
            id=taskId,
            sessionId=sessionId,
            message=Message(
                role='user',
                parts=[TextPart(text=message)],
                metadata=metadata,
            ),
            acceptedOutputModes=['text', 'text/plain', 'image/png'],
            # pushNotification=None,
            metadata={'conversation_id': sessionId},
        )
        task_result = await client.send_task(request, self.task_callback)

        if task_result is None:
            # If task_result is None, handle the error case
            state['session_active'] = False
            return [{"error": f"Task dispatch to agent '{agent_name}' failed to return a task status."}]

        # Only proceed if task_result is not None
        # Assume completion unless a state returns that isn't complete
        state['session_active'] = task_result.status.state not in [
            TaskState.COMPLETED,
            TaskState.CANCELED,
            TaskState.FAILED,
            TaskState.UNKNOWN,
        ]
        if task_result.status.state == TaskState.INPUT_REQUIRED:
            # Force user input back
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
        elif task_result.status.state == TaskState.CANCELED:
            # Open question, should we return some info for cancellation instead
            raise ValueError(f'Agent {agent_name} task {task_result.id} is cancelled')
        elif task_result.status.state == TaskState.FAILED:
            # Raise error for failure
            raise ValueError(f'Agent {agent_name} task {task_result.id} failed')
        response = []
        if task_result.status.message:
            # Assume the information is in the task message.
            response.extend(
                convert_parts(task_result.status.message.parts, tool_context)
            )
        if task_result.artifacts:
            for artifact in task_result.artifacts:
                response.extend(convert_parts(artifact.parts, tool_context))
        return response


def convert_parts(parts: list[Part], tool_context: ToolContext):
    rval = []
    for p in parts:
        rval.append(convert_part(p, tool_context))
    return rval


def convert_part(part: Part, tool_context: ToolContext):
    if part.type == 'text':
        return part.text
    if part.type == 'data':
        return part.data
    if part.type == 'file':
        # Repackage A2A FilePart to google.genai Blob
        # Currently not considering plain text as files
        file_id = part.file.name
        file_bytes = base64.b64decode(part.file.bytes)
        file_part = types.Part(
            inline_data=types.Blob(
                mime_type=part.file.mimeType, data=file_bytes
            )
        )
        tool_context.save_artifact(file_id, file_part)
        tool_context.actions.skip_summarization = True
        tool_context.actions.escalate = True
        return DataPart(data={'artifact-file-id': file_id})
    return f'Unknown type: {part.type}'
