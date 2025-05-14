import logging
import os
import click
import asyncio

# Assuming a2a library is installed and common.server/types are accessible
from common.server import A2AServer
from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MissingAPIKeyError, # Assuming this might be relevant if GOOGLE_API_KEY is needed
)
from dotenv import load_dotenv

from .a2a_task_manager import BrowserTaskManager
from .a2a_agent_wrapper import BrowserA2AWrapper

# We will get agent details from the wrapper after async initialization
# from agents.notion.agent import root_agent as notion_adk_agent # This line is removed/commented

load_dotenv() # Load environment variables from .env file, if present

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 10005 # Using a different port than the ADK sample

async def _async_setup_operations(host: str, port: int):
    """Performs all asynchronous setup and returns necessary objects."""
    logger.info("Starting asynchronous setup...")
    agent_wrapper_instance = await BrowserA2AWrapper.create()
    logger.info("BrowserA2AWrapper created successfully.")

    underlying_agent = agent_wrapper_instance._underlying_agent
    if not underlying_agent:
        raise RuntimeError("Failed to initialize the underlying ADK agent in the wrapper.")

    capabilities = AgentCapabilities(streaming=True, pushNotifications=False)
    browser_skill = AgentSkill(
        id='browser',
        name=underlying_agent.name,
        description=underlying_agent.description,
        tags=['browser', 'agent', 'collection', 'page', 'block', 'content-management', 'Agent Collection', 'database'],
        examples=[
            'Search for the latest news on the stock market.'
            'Go to this website and provide a full report https://lu.ma/b2o66w71'
            'Subscribe to this event: https://lu.ma/b2o66w71'
        ],
        inputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
        outputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
    )
    agent_card = AgentCard(
        name=underlying_agent.name,
        description=underlying_agent.description,
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=agent_wrapper_instance.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[browser_skill],
    )
    task_manager = BrowserTaskManager(agent_wrapper=agent_wrapper_instance)
    logger.info("Async setup complete. Server arguments prepared.")
    return agent_wrapper_instance, agent_card, task_manager

@click.command()
@click.option('--host', default=DEFAULT_HOST, help=f"Hostname to bind the server to (default: {DEFAULT_HOST})")
@click.option('--port', default=DEFAULT_PORT, type=int, help=f"Port to bind the server to (default: {DEFAULT_PORT})")
def main(host: str, port: int):  # This is now a synchronous function
    agent_wrapper_instance = None
    try:
        # Phase 1: Asynchronous setup
        logger.info(f"Initiating async setup for host={host}, port={port}")
        agent_wrapper_instance, agent_card, task_manager = asyncio.run(
            _async_setup_operations(host, port)
        )

        # Phase 2: Synchronous server start
        # A2AServer.start() calls uvicorn.run(), which internally calls asyncio.run()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=task_manager,
            host=host,
            port=port,
        )
        logger.info(f"Starting Browser A2A Server at http://{host}:{port}")
        logger.info(f"Agent Card will be available at http://{host}:{port}/.well-known/agent.json")
        # This call is blocking and will run its own asyncio event loop.
        # Uvicorn (and thus server.start()) handles KeyboardInterrupt to shut down.
        server.start()

    except MissingAPIKeyError as e:
        logger.error(f'Configuration Error: {e}')
        # No agent_wrapper_instance to clean up if this happens early
        exit(1)
    except ImportError as e:
        logger.error(f"ImportError: {e}. Ensure a2a library and dependencies are installed.")
        exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server setup or while trying to start: {e}', exc_info=True)
        # If agent_wrapper_instance exists, an error happened after its creation but before/during server.start()
        # or server.start() itself raised an unhandled exception (not KeyboardInterrupt).
        if agent_wrapper_instance: # Check if it was created before the error
            logger.info("Attempting to clean up resources due to an error...")
            try:
                asyncio.run(agent_wrapper_instance.close()) # New loop for cleanup
            except Exception as cleanup_e:
                logger.error(f"Error during cleanup: {cleanup_e}", exc_info=True)
        exit(1)
    finally:
        # This block is executed when server.start() returns (e.g., after a clean shutdown from KeyboardInterrupt)
        # or if an error occurred and was handled above (leading to exit, but finally still runs).
        if agent_wrapper_instance:
            logger.info("Server has shut down. Attempting final cleanup of BrowserA2AWrapper...")
            try:
                # Phase 3: Asynchronous cleanup in a new event loop
                asyncio.run(agent_wrapper_instance.close())
            except RuntimeError as e:
                if "cannot be called from a running event loop" in str(e):
                    logger.error("Final cleanup failed: Another event loop is unexpectedly running.")
                else:
                    logger.error(f"Runtime error during final cleanup: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error during final cleanup: {e}", exc_info=True)

if __name__ == '__main__':
    # Click handles the execution of the 'main' function.
    # Since 'main' is now synchronous, Click simply calls it.
    main()
 