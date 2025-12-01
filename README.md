# AR Billing Scenario Generator

Generate realistic Healthcare Accounts Receivable (AR) billing scenarios with built-in validation from denial to resolution with proper state transitions, temporal and financial consistency.

## Setup

### Requirements
- Python >= 3.12
- API key(s) for all LLM services that would be used to generate the scenarios.

### Installation

```bash
# Clone repository
git clone <repo-url>
cd ar-scenario-generator

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -e .

# Configure API key
echo "COHERE_API_KEY=your-key-here" > .env
```

## Quick Start

```python
from core.orchestrator import ScenarioOrchestrator, GenerationConfig

# Define your LLM client
def call_llm(system_prompt: str, user_prompt: str) -> str:
    # Your LLM API call here
    # You should ONLY return the raw text from the content body of your LLM response
    return response_text

# Create orchestrator
orchestrator = ScenarioOrchestrator(
    llm_client=call_llm,
    config=GenerationConfig(include_few_shot=True)
)

# Generate a scenario
result = orchestrator.generate_scenario(
    denial_code="CO-16",
    payer_category="commercial",
    complexity="moderate"
)

print(result.scenario)
print(result.validation_result.summary())
```

## Architecture

The system uses the following generation-validation pattern:

![](assets/architecture.png)

## Configuring Actions & Preconditions
- When generating scenarios, the action definitions are included in the system prompt to teach the LLM what actions are valid and how they should work
- After a scenario is generated, the validator checks that all actions follow their rules

This works as follows:

1. LLM sees this in the system prompt and learns the rules
2. Validator checks preconditions against Frame N-1
3. Validator checks postconditions against Frame N
4. Attempt fix in repair step

### Adding a New Action

Edit `core/schemas.py` → `ACTION_DEFINITIONS`:

```python
ACTION_DEFINITIONS = {
    "your_action_name": {
        "action": "your_action_name",
        "description": "What this action does",
        "actor": "operator",  # or "system"
        
        # Conditions that must be true BEFORE action
        "preconditions": {
            "claim_status": {
                "must_be_in": ["denied", "pending"],
                "description": "Claim must be denied or pending"
            },
            "has_balance": {
                "check": "account_balance_not_zero",
                "description": "Account must have a balance"
            }
        },
        
        # Changes that must occur AFTER action
        "postconditions": {
            "claim_updates": {
                "status": "new_status",
                "_delta": "updated",
                "_changed_fields": ["status"]
            },
            "new_transaction": {
                "type": "your_transaction_type",
                "amount": 0,
                "_delta": "added"
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["denial_code", "action_taken"],
                "_delta": "added"
            }
        }
    }
}
```

### Supported Precondition Checks

| Check Type | Example | Validated By |
|------------|---------|--------------|
| `claim_status` | `must_be_in: ["denied"]` | `validator.py` |
| `no_pending_appeal` | `appeal_reference_is_null` | `validator.py` |
| `timely_filing` | `deadline_not_passed` | Not yet implemented |
| `has_balance` | `account_balance_not_zero` | Not yet implemented |

**Note:** Some checks are currently validated by the LLM understanding the description. You can add custom validation logic in `validator.py` → `_validate_action_preconditions()`.

## Adding to Schemas

> [!NOTE]
> This will be updated in future versions to connect to stored references for denial codes and payer catalogs to avoid user burden.


### Add a Denial Code

Edit `core/schemas.py` → `DENIAL_CATALOG`:

```python
DENIAL_CATALOG = {
    "CO-123": {
        "code": "CO-123",
        "group": "CO",  # CO, PR, or OA
        "description": "Your denial description",
        "category": "coding_error",
        "common_causes": [
            "Cause 1",
            "Cause 2"
        ],
        "typical_actions": ["submit_appeal", "correct_and_rebill"],
        "documentation_needed": ["Clinical notes", "Lab results"],
        "appeal_success_rate": 0.65,  # 0-1 scale
        "avg_resolution_days": 30,
        "urgency": "high"  # low, medium, high
    }
}
```

### Add a Payer

Edit `core/schemas.py` → `PAYER_CATALOG`:

```python
PAYER_CATALOG = [
    {"name": "New Insurance Co", "code": "NIC"},
    # ... existing payers
]
```

### Add a Record Field

1. Edit `core/schemas.py` → `RECORD_SCHEMAS`:

```python
RECORD_SCHEMAS = {
    "claims": {
        "description": "Claim records submitted to payers",
        "fields": {
            "your_new_field": {
                "type": "string",
                "required": False,
                "description": "What this field represents"
            },
            # ... existing fields
        }
    }
}
```

2. Update few-shot examples in `prompts.py` to include the new field

## Configuration Options

```python
config = GenerationConfig(
    max_retries=3,           # Repair attempts before giving up
    include_few_shot=True,   # Include examples in prompt
    temperature=0.7,         # LLM temperature (not used if you control client)
    include_schemas=True     # Include full schemas in system prompt
)
```
