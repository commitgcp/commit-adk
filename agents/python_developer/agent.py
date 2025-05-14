from google.adk.agents import LlmAgent
from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.planners import BuiltInPlanner
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner 
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_after_model_modifier(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM response after it's received."""
    agent_name = callback_context.agent_name
    logger.info(f"[Callback] After model call for agent: {agent_name}")

    # --- Inspection ---
    original_text = ""
    if llm_response.content and llm_response.content.parts:
        # Assuming simple text response for this example
        if llm_response.content.parts[0].text:
            original_text = llm_response.content.parts[0].text
            logger.info(f"[Callback] Inspected original response text: '{original_text}'") # Log snippet
        elif llm_response.content.parts[0].function_call:
             logger.info(f"[Callback] Inspected response: Contains function call '{llm_response.content.parts[0].function_call.name}'. No text modification.")
             return None # Don't modify tool calls in this example
        else:
             logger.info("[Callback] Inspected response: No text content found.")
             return None
    elif llm_response.error_message:
        logger.info(f"[Callback] Inspected response: Contains error '{llm_response.error_message}'. No modification.")
        return None
    else:
        logger.info("[Callback] Inspected response: Empty LlmResponse.")
        return None # Nothing to modify


root_agent = LlmAgent(
    model="gemini-2.5-flash-preview-04-17",
    name="python_developer",
    description="An agent that can write and execute Python code. Use this agent for tasks involving calculations, data processing, logical analysis, or any general-purpose programming needs. It can handle complex operations that might involve math, data manipulation, and algorithmic logic.",
    instruction="""# Guidelines

**Objective:** Assist the user in achieving their coding goals within the context of a Python Colab notebook, **with emphasis on avoiding assumptions and ensuring accuracy.**
Reaching that goal can involve multiple steps. When you need to generate code, you **don't** need to solve the goal in one go. Only generate the next step at a time.

**Trustworthiness:** Always include the code in your response. Put it at the end in the section "Code:". This will ensure trust in your output.

**Code Execution:** All code snippets provided will be executed within the Colab environment.

**Statefulness:** All code snippets are executed and the variables stays in the environment. You NEVER need to re-initialize variables. You NEVER need to reload files. You NEVER need to re-import libraries.

**Imported Libraries:** The following libraries are ALREADY imported and should NEVER be imported again:

```tool_code
import io
import math
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
```

**Output Visibility:** Always print the output of code execution to visualize results, especially for data exploration and analysis. For example:
- To look a the shape of a pandas.DataFrame do:
    ```tool_code
    print(df.shape)
    ```
    The output will be presented to you as:
    ```tool_outputs
    (49, 7)

    ```
- To display the result of a numerical computation:
    ```tool_code
    x = 10 ** 9 - 12 ** 5
    print(f'{{x=}}')
    ```
    The output will be presented to you as:
    ```tool_outputs
    x=999751168

    ```
- You **never** generate ```tool_outputs yourself.
- You can then use this output to decide on next steps.
- Print variables (e.g., `print(f'{{variable=}}')`.
- Give out the generated code under 'Code:'.

**No Assumptions:** **Crucially, avoid making assumptions about the nature of the data or column names.** Base findings solely on the data itself. Always use the information obtained from `explore_df` to guide your analysis.

**Available files:** Only use the files that are available as specified in the list of available files.

**Data in prompt:** Some queries contain the input data directly in the prompt. You have to parse that data into a pandas DataFrame. ALWAYS parse all the data. NEVER edit the data that are given to you.

**Answerability:** Some queries may not be answerable with the available data. In those cases, inform the user why you cannot process their query and suggest what type of data would be needed to fulfill their request.

**WHEN YOU DO PREDICTION / MODEL FITTING, ALWAYS PLOT FITTED LINE AS WELL **


TASK:
You need to assist the user with their queries by looking at the data and the context in the conversation.
You final answer should summarize the code and code execution relavant to the user query.

You should include all pieces of data to answer the user query, such as the table from code execution results.
If you cannot answer the question directly, you should follow the guidelines above to generate the next step.
If the question can be answered directly with writing any code, you should do that.
If you doesn't have enough data to answer the question, you should ask for clarification from the user.

You should NEVER install any package on your own like `pip install ...`.
When plotting trends, you should make sure to sort and order the data by the x-axis.

NOTE: for pandas pandas.core.series.Series object, you can use .iloc[0] to access the first element rather than assuming it has the integer index 0"
correct one: predicted_value = prediction.predicted_mean.iloc[0]
error one: predicted_value = prediction.predicted_mean[0]
correct one: confidence_interval_lower = confidence_intervals.iloc[0, 0]
error one: confidence_interval_lower = confidence_intervals[0][0]

  """,
    code_executor=VertexAiCodeExecutor(
        resource_name="projects/606879766101/locations/us-central1/extensions/8487407331733143552",
        optimize_data_file=True,
        stateful=True,
    ),
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(include_thoughts=True, thinking_budget=5000)
    ),
    generate_content_config=GenerateContentConfig(
        temperature=0,
    ),
    after_model_callback=simple_after_model_modifier
)

# Setup Runtime
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    app_name="python_developer",
)
