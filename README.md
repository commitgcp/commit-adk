# Multi-Agent System for "The Next Wave of AI Innovation"

This repository showcases a sophisticated multi-agent system built with Python and Google's Agent Development Kit (ADK). It demonstrates how specialized AI agents can collaborate to perform complex tasks, featuring two primary orchestration approaches: a native ADK orchestration and an Agent-to-Agent (A2A) communication protocol. This system was prepared for the event "𝗧𝗵𝗲 𝗡𝗲𝘅𝘁 𝗪𝗮𝘃𝗲 𝗼𝗳 𝗔𝗜 𝗜𝗻𝗻𝗼𝘃𝗮𝘁𝗶𝗼𝗻".

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
  - [Common A2A Framework (`common/`)](#common-a2a-framework-common)
  - [Specialized Agents (`agents/`)](#specialized-agents-agents)
  - [Orchestration Approaches](#orchestration-approaches)
    - [1. ADK-Native Orchestration (`adk_orchestrator`)](#1-adk-native-orchestration-adk_orchestrator)
    - [2. A2A Protocol Orchestration (`a2a_orchestrator`)](#2-a2a-protocol-orchestration-a2a_orchestrator)
- [Setup and Installation](#setup-and-installation)
  - [Prerequisites](#prerequisites)
  - [Cloning the Repository](#cloning-the-repository)
  - [Setting up the Python Environment](#setting-up-the-python-environment)
  - [Environment Variables](#environment-variables)
- [Running the System](#running-the-system)
  - [1. Running Individual A2A Agents](#1-running-individual-a2a-agents)
  - [2. Running All A2A Agents Simultaneously](#2-running-all-a2a-agents-simultaneously)
  - [3. Interacting with the A2A Orchestrator](#3-interacting-with-the-a2a-orchestrator)
  - [4. Interacting with the ADK-Native Orchestrator](#4-interacting-with-the-adk-native-orchestrator)
- [Agent Details](#agent-details)
  - [Python Developer Agent](#python-developer-agent)
  - [LinkedIn Agent](#linkedin-agent)
  - [Google Calendar Agent](#google-calendar-agent)
  - [Deep Research Agent](#deep-research-agent)
  - [Notion Agent](#notion-agent)
- [Development](#development)

## Overview

The core purpose of this repository is to provide a framework and a reference implementation of a multi-agent system. It highlights how a central orchestrator can delegate tasks to specialized AI agents, each an expert in a particular domain (e.g., coding, research, calendar management). The system is designed to be modular and extensible.

## Features

*   **Modular Agent Architecture**: Composed of independent, specialized agents.
*   **Dual Orchestration Models**:
    *   **ADK-Native**: An orchestrator directly manages internal ADK sub-agents and agent-tools.
    *   **A2A Protocol**: A robust agent-to-agent communication protocol enabling remote discovery and task execution.
*   **Specialized Agent Capabilities**:
    *   **Python Development**: Execute Python code, write scripts.
    *   **LinkedIn Research**: Gather professional profiles and company information.
    *   **Google Calendar Management**: Search events, get calendar info.
    *   **Deep Research**: Conduct multi-step research and generate reports.
    *   **Notion Interaction**: Manage Notion pages and databases.
*   **LLM-Powered**: Leverages Large Language Models (primarily Google's Gemini) for planning, delegation, and task execution within agents.

## System Architecture

The system is organized into several key components:

### Common A2A Framework (`common/`)

This directory contains the foundational elements for the Agent-to-Agent (A2A) communication protocol.
*   **`common/types.py`**: Defines Pydantic models for all A2A messages, including `Task`, `Message`, `AgentCard`, `AgentSkill`, RPC structures, and error types. This forms the communication contract.
*   **`common/client/`**: Includes the `A2AClient` for sending requests to A2A agents and `A2ACardResolver` for discovering agent capabilities via their Agent Cards.
*   **`common/server/`**: Provides the `A2AServer` (a Starlette-based server) to host A2A agents and a `TaskManager` base class for handling task lifecycles.

### Specialized Agents (`agents/`)

Each subdirectory within `agents/` typically houses a specialized agent. These agents are built using Google ADK and can be run independently. For A2A communication, they are wrapped to expose an A2A-compliant interface.
*   **`agent.py`**: Core Google ADK agent logic (e.g., `LlmAgent`) with instructions, tools, and LLM configuration.
*   **`tools.py` (if applicable)**: Functions to create or fetch tools used by the ADK agent.
*   **`a2a_agent_wrapper.py`**: Bridges the ADK agent with the A2A protocol, implementing `invoke` and `stream` methods.
*   **`a2a_task_manager.py`**: A task manager that uses the agent's wrapper to handle incoming A2A tasks.
*   **`__main__.py`**: Script to launch the agent as an A2A service. It instantiates the `A2AServer`, defines the agent's `AgentCard`, and starts the server.

### Orchestration Approaches

This repository implements two distinct ways to orchestrate these specialized agents:

#### 1. ADK-Native Orchestration (`adk_orchestrator`)

*   **Location**: `agents/adk_orchestrator/`
*   **Mechanism**: This is a self-contained Google ADK `LlmAgent` that directly orchestrates a suite of *internal* ADK agents.
*   **How it works**:
    *   It uses the **sub-agent (transfer)** mechanism to delegate tasks to agents like `notion_agent`, `scrape_profile_agent` (for LinkedIn), `calendar_agent`, and `coding_agent`. These are declared in its `sub_agents` list.
    *   It uses the **`agent_tool.AgentTool`** mechanism to treat more complex agents/sequences as callable tools. An example is the `deep_research_tool` (a `SequentialAgent` for multi-step research).
    *   The `adk_orchestrator`'s `root_agent` (defined in `agents/adk_orchestrator/agent.py`) contains detailed instructions guiding its LLM on when and how to use these sub-agents and agent-tools based on the user's request.

#### 2. A2A Protocol Orchestration (`a2a_orchestrator`)

*   **Location**: `agents/a2a_orchestrator/`
*   **Mechanism**: This orchestrator is a Google ADK `HostAgent` that discovers and communicates with *remote* A2A-enabled agents over the network.
*   **How it works**:
    *   **Discovery via Agent Cards**:
        *   The `HostAgent` is initialized with a list of URLs for the remote A2A agents.
        *   It uses an `A2ACardResolver` to fetch an `AgentCard` from each remote agent's `/.well-known/agent.json` endpoint.
        *   The `AgentCard` describes the remote agent's capabilities, skills, and API endpoint.
        *   This information is compiled into a summary and provided to the `HostAgent`'s LLM, allowing it to make informed decisions about task delegation.
    *   **Task Delegation**:
        *   The `HostAgent`'s LLM, guided by its `root_instruction`, decomposes user requests and plans task execution.
        *   It uses a dedicated `send_task(agent_name: str, message: str)` tool to dispatch tasks to the appropriate remote A2A agent.
        *   The `RemoteAgentConnections` class manages communication with each remote agent, utilizing an `A2AClient` to send requests (supporting both streaming and non-streaming responses based on the remote agent's capabilities).
    *   **Remote A2A Agents**: Each specialized agent (e.g., `python_developer`, `linkedin`) runs its own `A2AServer`, serves its `AgentCard`, and uses an `A2AWrapper` to translate A2A requests into actions for its underlying ADK agent logic.

*   **Customizing A2A Agent Composition**:
    *   Not all listed A2A agents are strictly required to run the A2A orchestration system. You can select which agents the `a2a_orchestrator` attempts to connect to.
    *   The list of remote agent addresses is defined in `agents/a2a_orchestrator/agent.py`.
    *   To exclude an agent, simply remove or comment out its address from the list passed to the `HostAgent` constructor in this file.
    *   To add a new A2A-compliant agent:
        1.  Ensure your new agent correctly implements the A2A server protocol, including serving an `AgentCard` at its `/.well-known/agent.json` endpoint.
        2.  Add the address (URL) of your new agent to the list in `agents/a2a_orchestrator/agent.py`.
        The `a2a_orchestrator` will then attempt to discover and use it.

## Setup and Installation

### Prerequisites

*   Python 3.11+
*   `pip` and `venv`
*   Access to Google AI services (e.g., Gemini API via [Google AI Studio](https://aistudio.google.com/) or Google Cloud Vertex AI). An API key from Google AI Studio is sufficient for many core functionalities.
*   `gcloud` CLI (recommended for Google Cloud authentication if using specific GCP services like Calendar API or Vertex AI managed services).
*   `npm` and `npx` (for the Notion agent's MCP server dependency)

### Cloning the Repository

```bash
git clone <repository_url>
cd commit-adk
```

### Setting up the Python Environment

It's highly recommended to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Several agents require API keys or specific configurations set via environment variables. These are typically loaded from a `.env` file in the root of the project or in the respective agent's directory.

Create a `.env` file in the root of the project (`commit-adk/.env`) and add the necessary variables.

**Commonly Required Variables:**

*   **`NOTION_API_KEY`**: Required for the Notion Agent. Get this from your [Notion](https://www.notion.com/) integration settings.
    ```env
    NOTION_API_KEY="your_notion_api_key"
    ```
*   **`PROXYCURL_API_KEY`**: Required for the LinkedIn Agent. Get this from [Proxycurl](https://nubela.co/proxycurl).
    ```env
    PROXYCURL_API_KEY="your_proxycurl_api_key"
    ```

**Google Cloud Configuration / Google AI Studio API Keys:**

*   Several agents leverage Google's AI capabilities. You can use API keys obtained from [Google AI Studio](https://aistudio.google.com/) for Gemini models, or configure access to Google Cloud Platform services.
    *   **Using Google AI Studio API Key**: If you are primarily using Gemini models, obtain an API key from AI Studio and set it as the `GOOGLE_API_KEY` environment variable. This key can enable features like generative text, and for some Gemini models, grounded search capabilities and code generation (which the ADK then executes).
    *   **Using Google Cloud Platform (GCP)**: If you intend to use specific GCP services (like the Google Calendar API, Vertex AI for model hosting, or the Vertex AI Code Executor as a managed service), you'll typically use Application Default Credentials (ADC).
        *   Authenticate using the gcloud CLI. For Google Calendar access, ensure the calendar scope is included:
        ```bash
        gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/calendar
        ```
        *   Ensure your GCP project (if used) has the necessary APIs enabled (e.g., Google Calendar API, Vertex AI API). Specifically, the **Google Calendar API must be enabled** for the calendar agent to function if you are using this method of authentication for it.
        *   You might also need to set `GOOGLE_CLOUD_PROJECT="your-gcp-project-id"` if using GCP services.
*   **Environment Variable Priority**:
    *   `GOOGLE_API_KEY`: Primarily used for accessing Gemini models (e.g., via AI Studio).
    *   `GOOGLE_GENAI_USE_VERTEXAI`: Set to `"TRUE"` (default, or if variable is absent) to prefer Vertex AI for generative models if ADC is configured. Set to `"FALSE"` to explicitly use the `GOOGLE_API_KEY` for generative models.

**Example `.env` file structure:**

```env
# commit-adk/.env

# Notion
NOTION_API_KEY="secret_..."

# LinkedIn (via Proxycurl)
PROXYCURL_API_KEY="your_proxycurl_api_key"

# Google AI (Gemini API Key from AI Studio is often sufficient)
GOOGLE_API_KEY="your_gemini_api_key_from_ai_studio"

# Optional: If using Google Cloud Platform specific services
# GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
# GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json" # Alternative to ADC login for GCP

# Optional: To force non-Vertex AI for Gemini models if both API key and ADC are available
# GOOGLE_GENAI_USE_VERTEXAI="FALSE"
```

**Note**: Individual agents look for `.env` files within their own directories (e.g., `agents/notion/.env`).

## Running the System

Make sure your Python virtual environment is activated (`source .venv/bin/activate`).

### 1. Running Individual A2A Agents

You can run each A2A-enabled agent as a separate service. They will typically start a web server on a specific port.

From the root of the repository:

*   **Notion Agent** (Default Port: 10005):
    ```bash
    python -m agents.notion
    ```
    *(This agent also requires `npx @notionhq/notion-mcp-server` to be runnable, which its tools will attempt to invoke).*
*   **Deep Research Agent** (Default Port: 10003):
    ```bash
    python -m agents.deep_research
    ```
*   **Google Calendar Agent** (Default Port: 10002):
    ```bash
    python -m agents.google_calendar
    ```
*   **LinkedIn Agent** (Default Port: 10001):
    ```bash
    python -m agents.linkedin
    ```
*   **Python Developer Agent** (Default Port: 10000):
    ```bash
    python -m agents.python_developer
    ```

Each agent will output logs to the console, including the URL where its Agent Card is available (e.g., `http://localhost:10000/.well-known/agent.json`).

### 2. Running All A2A Agents Simultaneously

A utility script is provided to start all the primary A2A agents at once.

From the root of the repository:

```bash
python run_all_agents.py
```

This script will launch each agent in a separate process and stream their logs to the console. Press `Ctrl+C` to shut down all agents gracefully.

### 3. Interacting with the A2A Orchestrator

Once the individual A2A agents are running (either started individually or via `run_all_agents.py`), you can interact with the A2A Orchestrator.

1.  **Navigate to the `agents` directory**:
    ```bash
    cd agents
    ```
2.  **Start the ADK Web UI**:
    ```bash
    adk web
    ```
3.  Open your web browser and go to the URL provided by the `adk web` command (usually `http://localhost:8080`).
4.  From the dropdown menu in the ADK Web UI, select the `a2a_orchestrator` agent.
5.  You can now chat with the `a2a_orchestrator`. It will discover the running A2A agents and delegate tasks to them based on your requests.

### 4. Interacting with the ADK-Native Orchestrator

The ADK-Native Orchestrator runs as a single ADK agent that internally manages its sub-agents and tools.

1.  **Navigate to the `agents` directory**:
    ```bash
    cd agents
    ```
2.  **Start the ADK Web UI**:
    ```bash
    adk web
    ```
3.  Open your web browser and go to the URL provided by the `adk web` command.
4.  From the dropdown menu, select the `adk_orchestrator` agent.
5.  You can now chat with it. It will use its internal agents and tools to fulfill your requests.

## Agent Details

All agents require in the `.env` file the details for Google Cloud or AI Studio API keys. Below, only specific additional requirements are mentioned.
Here's a brief overview of the specialized agents:

### Python Developer Agent
*   **A2A Name (in Agent Card)**: `coding_agent`
*   **A2A Port**: `10000`
*   **Purpose**: Writes and executes Python code. By default, it's configured to potentially use Google's Vertex AI Code Executor if available and `GOOGLE_GENAI_USE_VERTEXAI` is not `"FALSE"`. Capable of generating scripts, performing calculations, and general Python-based tasks.
*   **Vertex AI Code Executor Setup (If using Vertex AI for code execution)**:
    *   If you choose to use the managed Vertex AI Code Executor service with this agent:
    *   This agent utilizes a Vertex AI Code Executor extension for code execution.
    *   The `resource_name` for this extension might be hardcoded in `agents/python_developer/agent.py`.
    *   To create and use your own extension in your GCP project:
        1.  In `agents/python_developer/agent.py`, locate the `VertexAiCodeExecutor` instantiation.
        2.  Temporarily comment out the `resource_name` parameter.
        3.  Run the Python Developer agent (e.g., `cd agents && adk run python_developer`).
        4.  The first time it runs, it will create a new Code Executor extension in your configured GCP project.
        5.  Check the agent's logs for a message indicating the created extension ID (e.g., "Created new code executor extension with resource name: projects/your-project/locations/us-central1/extensions/extension-id").
        6.  Copy this full `resource_name`.
        7.  Uncomment the `resource_name` parameter in `agents/python_developer/agent.py` and set its value to the copied ID.
    *   This will ensure the agent reuses your specific extension for subsequent executions, avoiding the creation of a new one each time.
*   **Alternative Code Execution Setup**:
    *   The Python Developer agent requires a code execution mechanism.
    *   If not using the Vertex AI Code Executor Extension, you will need to configure an alternative. The ADK supports various ways to implement code execution, either as a standalone tool or by providing a `code_executor` instance to the `LlmAgent`.
    *   For detailed guidance on setting up code executors, refer to the official ADK documentation:
        *   [ADK Docs: Built-in Tools (Code Execution)](https://google.github.io/adk-docs/tools/built-in-tools/#code-execution)
        *   [ADK Docs: LLM Agents (Planning Code Execution)](https://google.github.io/adk-docs/agents/llm-agents/#planning-code-execution)
        *   [ADK API Reference: google.adk.code_executors](https://google.github.io/adk-docs/api-reference/google-adk.html#module-google.adk.code_executors)

### LinkedIn Agent
*   **A2A Name (in Agent Card)**: `professional_intelligence_agent` (referred to as `people_info_agent` by `a2a_orchestrator`'s default config)
*   **A2A Port**: `10001`
*   **Purpose**: Gathers professional information (people profiles, company details) from LinkedIn. Uses the Proxycurl API via an OpenAPI toolset.
*   **Requires**: `PROXYCURL_API_KEY` environment variable.

### Google Calendar Agent
*   **A2A Name (in Agent Card)**: `calendar_agent`
*   **A2A Port**: `10002`
*   **Purpose**: Interacts with Google Calendar. Can search events, get calendar information, list attendees, and fetch current datetime.
*   **Requires**: Google Cloud authentication (e.g., `gcloud auth application-default login`) and the Google Calendar API enabled.

### Deep Research Agent
*   **A2A Name (in Agent Card)**: `deep_research_agent`
*   **A2A Port**: `10003`
*   **Purpose**: Performs multi-step research using web searches and generates reports. Search capabilities can be provided by the underlying Gemini model (if it supports grounding/search and is accessed with an appropriate API key, e.g., from AI Studio) or by configuring specific search tools. It can formulate research questions, iteratively search, and compile findings.
*   **Requires**: N/A

### Notion Agent
*   **A2A Name (in Agent Card)**: `notion_agent`
*   **A2A Port**: `10005`
*   **Purpose**: Interacts with Notion pages and databases. Uses the Notion MCP (Model-Component-Protocol) server.
*   **Requires**: `NOTION_API_KEY` environment variable and ability to run `npx @notionhq/notion-mcp-server`.