import logging
import os
import click

# Assuming a2a library is installed and common.server/types are accessible
from common.server import A2AServer
from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MissingAPIKeyError, # Assuming this might be relevant if GOOGLE_API_KEY is needed
)
from dotenv import load_dotenv

from .a2a_task_manager import DeepResearchTaskManager
from .a2a_agent_wrapper import DeepResearchA2AWrapper

# Import the original agent's name and description for the AgentCard
from agents.deep_research.agent import root_agent as deep_research_adk_agent

load_dotenv() # Load environment variables from .env file, if present

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 10003 # Using a different port than the ADK sample

@click.command()
@click.option('--host', default=DEFAULT_HOST, help=f"Hostname to bind the server to (default: {DEFAULT_HOST})")
@click.option('--port', default=DEFAULT_PORT, type=int, help=f"Port to bind the server to (default: {DEFAULT_PORT})")
def main(host: str, port: int):
    try:
        # Example: Check for API keys if your ADK agent relies on them directly 
        # and they are not handled by ADC or other means.
        # This is just a placeholder, adapt if necessary based on python_dev_adk_agent's needs.
        # if not os.getenv('GOOGLE_GENAI_USE_VERTEXAI') == 'TRUE':
        #     if not os.getenv('GOOGLE_API_KEY'):
        #         raise MissingAPIKeyError(
        #             'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        #         )

        agent_wrapper_instance = DeepResearchA2AWrapper()

        capabilities = AgentCapabilities(streaming=True, pushNotifications=False) # Assuming no push notifications for now
        
        # Define a skill for the Python Developer Agent
        # Using the description from the LlmAgent
        deep_research_skill = AgentSkill(
            id='deep_research_agent',
            name=deep_research_adk_agent.name, # Using the ADK agent's name ("deep_research_agent")
            description=deep_research_adk_agent.description, # Using the ADK agent's description
            tags=['research', 'deep_dive', 'quick_search', 'context_gathering', 'report_generation', 'information_synthesis', 'google_search', 'multi_step_processing'],
            examples=[
                'Conduct a deep research investigation into the future of renewable energy and provide a comprehensive report.',
                'Perform a quick search on the main competitors of Tesla Inc. and summarize the findings with sources.',
                "Gather initial context on the topic of 'quantum computing applications in medicine'.",
                "Generate a detailed report on the impact of AI on the job market, including references.",
                "What are the latest developments in gene editing? (quick search)"
            ],
            # Input/Output modes are derived from the wrapper's SUPPORTED_CONTENT_TYPES
            inputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            outputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
        )

        agent_card = AgentCard(
            name=deep_research_adk_agent.name, # Using the ADK agent's name ("deep_research_agent")
            description=deep_research_adk_agent.description, # Using the ADK agent's description
            url=f'http://{host}:{port}/', # A2A server URL
            version='1.0.0', # Arbitrary version
            defaultInputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[deep_research_skill],
            # provider, documentationUrl, authentication can be added if needed
        )

        task_manager = DeepResearchTaskManager(agent_wrapper=agent_wrapper_instance)

        server = A2AServer(
            agent_card=agent_card,
            task_manager=task_manager,
            host=host,
            port=port,
            # Other A2AServer options like base_path, jwks_url if needed
        )
        
        logger.info(f"Starting Deep Research A2A Server at http://{host}:{port}")
        logger.info(f"Agent Card will be available at http://{host}:{port}/.well-known/agent.json")
        server.start()

    except MissingAPIKeyError as e: # Example error handling
        logger.error(f'Configuration Error: {e}')
        exit(1)
    except ImportError as e:
        logger.error(f"ImportError: {e}. Please ensure the 'a2a' library and its dependencies are installed.")
        logger.error("You might need to run: pip install google-a2a") # Or however it's installed
        exit(1)
    except Exception as e:
        logger.error(f'An unexpected error occurred during server startup: {e}', exc_info=True)
        exit(1)

if __name__ == '__main__':
    main() 