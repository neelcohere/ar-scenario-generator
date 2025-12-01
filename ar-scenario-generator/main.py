import os
import openai
from typing import Optional
from dotenv import load_dotenv

from core.orchestrator import ScenarioOrchestrator, GenerationConfig
from core.validator import get_validation_summary

load_dotenv(dotenv_path="../.env", override=True)


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_openai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.choices[0].message.content

# Instantiate orchestrator
orchestrator = ScenarioOrchestrator(
    llm_client=call_openai,
    config=GenerationConfig(include_few_shot=True)
)

# Example: Generate a scenario
scenario = orchestrator.generate_scenario(denial_code="CO-16")

print(scenario.scenario)

if scenario.validation_result:
    print(scenario.validation_result.summary())

# Example: Validate an existing scenario
validation = orchestrator.validate_scenario(scenario.scenario)
print(get_validation_summary(validation))
