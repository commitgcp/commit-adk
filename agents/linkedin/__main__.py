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

from .a2a_task_manager import LinkedinTaskManager
from .a2a_agent_wrapper import LinkedinA2AWrapper

# Import the original agent's name and description for the AgentCard
from agents.linkedin.agent import root_agent as linkedin_adk_agent

load_dotenv() # Load environment variables from .env file, if present

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 10001 # Using a different port than the ADK sample

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

        agent_wrapper_instance = LinkedinA2AWrapper()

        capabilities = AgentCapabilities(streaming=True, pushNotifications=False) # Assuming no push notifications for now
        
        # Define a skill for the People Info Agent
        # Using the description from the LlmAgent
        linkedin_skill = AgentSkill(
            id='linkedin',
            name=linkedin_adk_agent.name, # Using the ADK agent's name ("professional_intelligence_agent")
            description=linkedin_adk_agent.description, # Using the ADK agent's description
            tags=['linkedin_research', 'professional_profiles', 'company_intelligence', 'job_market_analysis', 'educational_institutions', 'meeting_preparation', 'business_analytics', 'proxycurl', 'people', 'company', 'jobs', 'schools'],
            examples=[
                'Find the LinkedIn profile of Satya Nadella.',
                'Get detailed professional information for Tim Cook, including work history and education.',
                "Tell me about Google: its size, industry, and specializations.",
                "List current employees at Microsoft.",
                "Show me recent job postings from Amazon in software engineering.",
                "Get information about Massachusetts Institute of Technology (MIT).",
                "Prepare a meeting brief about Elon Musk focusing on his current ventures.",
                "Who is the CTO of OpenAI?",
                "Find company logo for Apple Inc."
            ],
            # Input/Output modes are derived from the wrapper's SUPPORTED_CONTENT_TYPES
            inputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            outputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
        )

        agent_card = AgentCard(
            name=linkedin_adk_agent.name, # Using the ADK agent's name ("professional_intelligence_agent")
            description=linkedin_adk_agent.description, # Using the ADK agent's description
            url=f'http://{host}:{port}/', # A2A server URL
            version='1.0.0', # Arbitrary version
            defaultInputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[linkedin_skill],
            # provider, documentationUrl, authentication can be added if needed
        )

        task_manager = LinkedinTaskManager(agent_wrapper=agent_wrapper_instance)

        server = A2AServer(
            agent_card=agent_card,
            task_manager=task_manager,
            host=host,
            port=port,
            # Other A2AServer options like base_path, jwks_url if needed
        )
        
        logger.info(f"Starting Linkedin A2A Server at http://{host}:{port}")
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