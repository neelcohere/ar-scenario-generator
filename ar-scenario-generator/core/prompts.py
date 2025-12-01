from typing import Dict, List, Optional
import json

from .schemas import (
    get_schema_as_text,
    get_denial_catalog_as_text,
    get_constraints_as_text,
    DENIAL_CATALOG,
    ACTION_DEFINITIONS,
    RECORD_SCHEMAS,
)


SYSTEM_PROMPT_BASE = """You are an expert in Healthcare Revenue Cycle Management (RCM), specifically in Accounts Receivable (AR) billing operations. You have deep knowledge of:

- Medical billing codes (CPT, ICD-10, HCPCS)
- Claim Adjustment Reason Codes (CARC) and Remittance Advice Remark Codes (RARC)
- Payer contracts, denials, and appeals processes
- AR billing workflows and operator actions
- Healthcare financial transactions and reconciliation

Your task is to generate realistic AR billing scenarios that represent the lifecycle of an account from when it lands on a billing operator's workqueue through resolution.

Each scenario you generate must:
1. Follow the exact JSON schema provided
2. Be logically consistent (actions have valid preconditions, state changes are correct)
3. Be temporally consistent (dates in chronological order)
4. Be financially consistent (transactions sum correctly)
5. Include realistic, substantive content (detailed notes, proper denial descriptions)
6. Track changes with _delta fields (added, updated, null)
"""

SYSTEM_PROMPT_WITH_SCHEMAS = SYSTEM_PROMPT_BASE + """

## RECORD SCHEMAS

{schemas}

## DENIAL CODE CATALOG

{denial_catalog}

## LOGICAL CONSTRAINTS

{constraints}
"""


def get_system_prompt(include_schemas: bool = True) -> str:
    """Get the system prompt for scenario generation. Optionally include schemas."""
    if include_schemas:
        return SYSTEM_PROMPT_WITH_SCHEMAS.format(
            schemas=get_schema_as_text(),
            denial_catalog=get_denial_catalog_as_text(),
            constraints=get_constraints_as_text(),
        )
    return SYSTEM_PROMPT_BASE


# Example 1: CO-16 Appeal Scenario (Successful)
EXAMPLE_SCENARIO_CO16_APPEAL = {
    "scenario_metadata": {
        "scenario_id": "SCN-2024-001847",
        "scenario_type": "denial_resolution",
        "denial_code": "CO-16",
        "complexity": "moderate",
        "generated_at": "2024-11-27T14:32:00Z"
    },
    "account": {
        "account_number": "ACC-78234521",
        "facility": "Memorial Regional Hospital",
        "service_date": "2024-08-15"
    },
    "timeline": [
        {
            "timestamp": "2024-09-01T08:00:00Z",
            "frame_id": "F001",
            "event_type": "account_drops_to_workqueue",
            "event": {
                "trigger": "system_automated",
                "description": "Account drops to AR Billing workqueue after claim denial received from UnitedHealthcare. Denial reason code CO-16 indicates the claim lacks information needed for adjudication. Remark code N56 specifies that documentation does not support medical necessity for the EKG procedure.",
                "actor": "system"
            },
            "account_state": {
                "demographics": [
                    {
                        "record_id": "DEM-001",
                        "patient_name": "Johnson, Michael R.",
                        "dob": "1967-03-22",
                        "mrn": "MRN-445521",
                        "insurance_id": "UHC-8834521",
                        "payer_name": "UnitedHealthcare",
                        "payer_code": "UHC",
                        "policy_status": "active",
                        "subscriber_relationship": "self",
                        "_delta": None
                    }
                ],
                "claims": [
                    {
                        "record_id": "CLM-001",
                        "claim_number": "CLM-2024-445521",
                        "service_date": "2024-08-15",
                        "procedure_codes": ["99214", "93000"],
                        "diagnosis_codes": ["I10", "R00.0"],
                        "billed_amount": 425.00,
                        "status": "denied",
                        "submission_date": "2024-08-18",
                        "denial_date": "2024-08-28",
                        "denial_codes": ["CO-16"],
                        "timely_filing_deadline": "2025-08-15",
                        "_delta": None
                    }
                ],
                "remits": [
                    {
                        "record_id": "RMT-001",
                        "remit_date": "2024-08-28",
                        "claim_reference": "CLM-2024-445521",
                        "payer": "UnitedHealthcare",
                        "payment_amount": 0.00,
                        "adjustment_amount": 425.00,
                        "adjustment_reason_codes": ["CO-16"],
                        "remark_codes": ["N56"],
                        "remark_text": "Documentation does not support medical necessity for the service billed",
                        "_delta": None
                    }
                ],
                "transactions": [
                    {
                        "record_id": "TXN-001",
                        "transaction_date": "2024-08-15",
                        "type": "charge",
                        "amount": 425.00,
                        "description": "Office visit - established patient, moderate complexity (99214) + Electrocardiogram (93000)",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-002",
                        "transaction_date": "2024-08-28",
                        "type": "denial_posted",
                        "amount": 0.00,
                        "reference": "RMT-001",
                        "description": "Denial posted - CO-16: Claim lacks information for adjudication",
                        "_delta": None
                    }
                ],
                "notes": []
            },
            "state_summary": "Account has open balance of $425.00 after CO-16 denial from UnitedHealthcare. Payer requests medical necessity documentation for EKG (93000). Patient presented with hypertension (I10) and tachycardia (R00.0). Timely filing deadline: 2025-08-15 (349 days remaining). No prior notes or actions on account."
        },
        {
            "timestamp": "2024-09-01T09:15:00Z",
            "frame_id": "F002",
            "event_type": "operator_action",
            "event": {
                "trigger": "user_initiated",
                "description": "AR Billing operator reviews account and identifies that the denial is for medical necessity documentation. Operator retrieves clinical notes from the 8/15 visit which document the patient's complaint of palpitations and elevated heart rate. Lab results from 8/10 show elevated BNP. Decision made to submit first-level appeal with supporting clinical documentation.",
                "actor": "operator",
                "actor_id": "OPR-2241",
                "action_taken": "submit_appeal",
                "action_details": {
                    "appeal_type": "first_level",
                    "documentation_attached": [
                        "clinical_notes_2024-08-15",
                        "lab_results_2024-08-10"
                    ],
                    "appeal_reason": "Medical necessity supported by clinical documentation showing cardiac symptoms"
                }
            },
            "account_state": {
                "demographics": [
                    {
                        "record_id": "DEM-001",
                        "patient_name": "Johnson, Michael R.",
                        "dob": "1967-03-22",
                        "mrn": "MRN-445521",
                        "insurance_id": "UHC-8834521",
                        "payer_name": "UnitedHealthcare",
                        "payer_code": "UHC",
                        "policy_status": "active",
                        "subscriber_relationship": "self",
                        "_delta": None
                    }
                ],
                "claims": [
                    {
                        "record_id": "CLM-001",
                        "claim_number": "CLM-2024-445521",
                        "service_date": "2024-08-15",
                        "procedure_codes": ["99214", "93000"],
                        "diagnosis_codes": ["I10", "R00.0"],
                        "billed_amount": 425.00,
                        "status": "appeal_submitted",
                        "submission_date": "2024-08-18",
                        "denial_date": "2024-08-28",
                        "denial_codes": ["CO-16"],
                        "appeal_date": "2024-09-01",
                        "appeal_reference": "APL-2024-78821",
                        "timely_filing_deadline": "2025-08-15",
                        "_delta": "updated",
                        "_changed_fields": ["status", "appeal_date", "appeal_reference"]
                    }
                ],
                "remits": [
                    {
                        "record_id": "RMT-001",
                        "remit_date": "2024-08-28",
                        "claim_reference": "CLM-2024-445521",
                        "payer": "UnitedHealthcare",
                        "payment_amount": 0.00,
                        "adjustment_amount": 425.00,
                        "adjustment_reason_codes": ["CO-16"],
                        "remark_codes": ["N56"],
                        "remark_text": "Documentation does not support medical necessity for the service billed",
                        "_delta": None
                    }
                ],
                "transactions": [
                    {
                        "record_id": "TXN-001",
                        "transaction_date": "2024-08-15",
                        "type": "charge",
                        "amount": 425.00,
                        "description": "Office visit - established patient, moderate complexity (99214) + Electrocardiogram (93000)",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-002",
                        "transaction_date": "2024-08-28",
                        "type": "denial_posted",
                        "amount": 0.00,
                        "reference": "RMT-001",
                        "description": "Denial posted - CO-16: Claim lacks information for adjudication",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-003",
                        "transaction_date": "2024-09-01",
                        "type": "appeal_submitted",
                        "amount": 0.00,
                        "reference": "APL-2024-78821",
                        "description": "First-level appeal submitted to UnitedHealthcare",
                        "_delta": "added"
                    }
                ],
                "notes": [
                    {
                        "record_id": "NOTE-001",
                        "note_date": "2024-09-01T09:15:00Z",
                        "author": "OPR-2241",
                        "author_type": "operator",
                        "note_type": "action",
                        "content": "Reviewed CO-16 denial for claim CLM-2024-445521. Denial reason: medical necessity documentation insufficient for EKG (93000). Retrieved clinical notes from 8/15/2024 visit documenting patient's chief complaint of palpitations and HR of 112. Lab results from 8/10/2024 show BNP of 245 pg/mL (elevated). Submitted first-level appeal (APL-2024-78821) with clinical notes and lab results attached. Appeal argues EKG was medically necessary to evaluate cardiac symptoms in context of hypertension and elevated BNP. Follow-up in 30 days if no response from payer.",
                        "_delta": "added"
                    }
                ]
            },
            "state_summary": "Appeal submitted for $425.00 denied claim. Appeal reference: APL-2024-78821. Documentation attached includes clinical notes showing cardiac symptoms (palpitations, elevated HR) and lab results (elevated BNP). Expected payer response within 30 days."
        },
        {
            "timestamp": "2024-10-02T02:00:00Z",
            "frame_id": "F003",
            "event_type": "async_process",
            "event": {
                "trigger": "payer_response",
                "description": "UnitedHealthcare responds to appeal. Appeal approved based on additional clinical documentation demonstrating medical necessity for cardiac evaluation. Payment of $340.00 issued (80% of billed amount per contracted rate). Contractual adjustment of $85.00 applied.",
                "actor": "system"
            },
            "account_state": {
                "demographics": [
                    {
                        "record_id": "DEM-001",
                        "patient_name": "Johnson, Michael R.",
                        "dob": "1967-03-22",
                        "mrn": "MRN-445521",
                        "insurance_id": "UHC-8834521",
                        "payer_name": "UnitedHealthcare",
                        "payer_code": "UHC",
                        "policy_status": "active",
                        "subscriber_relationship": "self",
                        "_delta": None
                    }
                ],
                "claims": [
                    {
                        "record_id": "CLM-001",
                        "claim_number": "CLM-2024-445521",
                        "service_date": "2024-08-15",
                        "procedure_codes": ["99214", "93000"],
                        "diagnosis_codes": ["I10", "R00.0"],
                        "billed_amount": 425.00,
                        "status": "paid",
                        "submission_date": "2024-08-18",
                        "denial_date": "2024-08-28",
                        "denial_codes": ["CO-16"],
                        "appeal_date": "2024-09-01",
                        "appeal_reference": "APL-2024-78821",
                        "paid_amount": 340.00,
                        "contractual_adjustment": 85.00,
                        "timely_filing_deadline": "2025-08-15",
                        "_delta": "updated",
                        "_changed_fields": ["status", "paid_amount", "contractual_adjustment"]
                    }
                ],
                "remits": [
                    {
                        "record_id": "RMT-001",
                        "remit_date": "2024-08-28",
                        "claim_reference": "CLM-2024-445521",
                        "payer": "UnitedHealthcare",
                        "payment_amount": 0.00,
                        "adjustment_amount": 425.00,
                        "adjustment_reason_codes": ["CO-16"],
                        "remark_codes": ["N56"],
                        "remark_text": "Documentation does not support medical necessity for the service billed",
                        "_delta": None
                    },
                    {
                        "record_id": "RMT-002",
                        "remit_date": "2024-10-01",
                        "claim_reference": "CLM-2024-445521",
                        "payer": "UnitedHealthcare",
                        "payment_amount": 340.00,
                        "adjustment_amount": 85.00,
                        "adjustment_reason_codes": ["CO-45"],
                        "remark_codes": [],
                        "check_number": "CHK-99821445",
                        "_delta": "added"
                    }
                ],
                "transactions": [
                    {
                        "record_id": "TXN-001",
                        "transaction_date": "2024-08-15",
                        "type": "charge",
                        "amount": 425.00,
                        "description": "Office visit - established patient, moderate complexity (99214) + Electrocardiogram (93000)",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-002",
                        "transaction_date": "2024-08-28",
                        "type": "denial_posted",
                        "amount": 0.00,
                        "reference": "RMT-001",
                        "description": "Denial posted - CO-16: Claim lacks information for adjudication",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-003",
                        "transaction_date": "2024-09-01",
                        "type": "appeal_submitted",
                        "amount": 0.00,
                        "reference": "APL-2024-78821",
                        "description": "First-level appeal submitted to UnitedHealthcare",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-004",
                        "transaction_date": "2024-10-01",
                        "type": "payment",
                        "amount": -340.00,
                        "reference": "RMT-002",
                        "description": "Payment received from UnitedHealthcare - Check CHK-99821445",
                        "_delta": "added"
                    },
                    {
                        "record_id": "TXN-005",
                        "transaction_date": "2024-10-01",
                        "type": "contractual_adjustment",
                        "amount": -85.00,
                        "reference": "RMT-002",
                        "description": "Contractual adjustment per UHC PPO contract",
                        "_delta": "added"
                    }
                ],
                "notes": [
                    {
                        "record_id": "NOTE-001",
                        "note_date": "2024-09-01T09:15:00Z",
                        "author": "OPR-2241",
                        "author_type": "operator",
                        "note_type": "action",
                        "content": "Reviewed CO-16 denial for claim CLM-2024-445521. Denial reason: medical necessity documentation insufficient for EKG (93000). Retrieved clinical notes from 8/15/2024 visit documenting patient's chief complaint of palpitations and HR of 112. Lab results from 8/10/2024 show BNP of 245 pg/mL (elevated). Submitted first-level appeal (APL-2024-78821) with clinical notes and lab results attached. Appeal argues EKG was medically necessary to evaluate cardiac symptoms in context of hypertension and elevated BNP. Follow-up in 30 days if no response from payer.",
                        "_delta": None
                    },
                    {
                        "record_id": "NOTE-002",
                        "note_date": "2024-10-02T02:00:00Z",
                        "author": "SYSTEM",
                        "author_type": "automated",
                        "note_type": "payment_posting",
                        "content": "Appeal APL-2024-78821 approved by UnitedHealthcare. Payment received: $340.00 (Check CHK-99821445). Contractual adjustment: $85.00 per UHC PPO fee schedule. Account balance: $0.00. Claim resolved - paid in full per contract.",
                        "_delta": "added"
                    }
                ]
            },
            "state_summary": "Appeal successful. Payment of $340.00 received from UnitedHealthcare. Contractual adjustment of $85.00 applied per PPO contract. Account balance: $0.00. Account resolved after 31 days."
        }
    ],
    "resolution": {
        "final_status": "paid",
        "final_balance": 0.00,
        "total_collected": 340.00,
        "total_adjustments": 85.00,
        "days_to_resolution": 31,
        "actions_taken": 1,
        "resolution_path": ["denial_received", "appeal_submitted", "appeal_approved", "payment_posted"]
    }
}

# Example 2: PR-1 Patient Responsibility Scenario
EXAMPLE_SCENARIO_PR1_PATIENT = {
    "scenario_metadata": {
        "scenario_id": "SCN-2024-002156",
        "scenario_type": "denial_resolution",
        "denial_code": "PR-1",
        "complexity": "simple",
        "generated_at": "2024-11-27T15:45:00Z"
    },
    "account": {
        "account_number": "ACC-91234567",
        "facility": "Community Medical Center",
        "service_date": "2024-09-10"
    },
    "timeline": [
        {
            "timestamp": "2024-09-25T10:00:00Z",
            "frame_id": "F001",
            "event_type": "account_drops_to_workqueue",
            "event": {
                "trigger": "system_automated",
                "description": "Account drops to AR Billing workqueue after partial payment received from Aetna. PR-1 adjustment indicates patient responsibility for deductible amount of $250.00. Patient's annual deductible has not been met.",
                "actor": "system"
            },
            "account_state": {
                "demographics": [
                    {
                        "record_id": "DEM-001",
                        "patient_name": "Williams, Sarah K.",
                        "dob": "1985-07-14",
                        "mrn": "MRN-667788",
                        "insurance_id": "AET-5567234",
                        "payer_name": "Aetna",
                        "payer_code": "AET",
                        "policy_status": "active",
                        "_delta": None
                    }
                ],
                "claims": [
                    {
                        "record_id": "CLM-001",
                        "claim_number": "CLM-2024-667788",
                        "service_date": "2024-09-10",
                        "procedure_codes": ["99213"],
                        "diagnosis_codes": ["J06.9"],
                        "billed_amount": 185.00,
                        "status": "partially_denied",
                        "submission_date": "2024-09-12",
                        "denial_date": "2024-09-22",
                        "denial_codes": ["PR-1"],
                        "paid_amount": 0.00,
                        "patient_responsibility": 185.00,
                        "_delta": None
                    }
                ],
                "remits": [
                    {
                        "record_id": "RMT-001",
                        "remit_date": "2024-09-22",
                        "claim_reference": "CLM-2024-667788",
                        "payer": "Aetna",
                        "payment_amount": 0.00,
                        "adjustment_amount": 185.00,
                        "adjustment_reason_codes": ["PR-1"],
                        "remark_codes": ["N130"],
                        "remark_text": "Deductible amount - patient responsibility",
                        "_delta": None
                    }
                ],
                "transactions": [
                    {
                        "record_id": "TXN-001",
                        "transaction_date": "2024-09-10",
                        "type": "charge",
                        "amount": 185.00,
                        "description": "Office visit - established patient, low complexity (99213)",
                        "_delta": None
                    }
                ],
                "notes": []
            },
            "state_summary": "Account has patient responsibility balance of $185.00 after PR-1 (deductible) from Aetna. Full billed amount applied to patient deductible. Patient statement needs to be generated."
        },
        {
            "timestamp": "2024-09-25T10:30:00Z",
            "frame_id": "F002",
            "event_type": "operator_action",
            "event": {
                "trigger": "user_initiated",
                "description": "AR Billing operator reviews account and confirms the PR-1 adjustment is correct - patient's annual deductible has not been met. Balance transferred to patient responsibility and patient statement generated.",
                "actor": "operator",
                "actor_id": "OPR-3315",
                "action_taken": "transfer_to_patient",
                "action_details": {
                    "amount": 185.00,
                    "statement_type": "initial",
                    "payment_plan_offered": False
                }
            },
            "account_state": {
                "demographics": [
                    {
                        "record_id": "DEM-001",
                        "patient_name": "Williams, Sarah K.",
                        "dob": "1985-07-14",
                        "mrn": "MRN-667788",
                        "insurance_id": "AET-5567234",
                        "payer_name": "Aetna",
                        "payer_code": "AET",
                        "policy_status": "active",
                        "_delta": None
                    }
                ],
                "claims": [
                    {
                        "record_id": "CLM-001",
                        "claim_number": "CLM-2024-667788",
                        "service_date": "2024-09-10",
                        "procedure_codes": ["99213"],
                        "diagnosis_codes": ["J06.9"],
                        "billed_amount": 185.00,
                        "status": "partially_denied",
                        "submission_date": "2024-09-12",
                        "denial_date": "2024-09-22",
                        "denial_codes": ["PR-1"],
                        "paid_amount": 0.00,
                        "patient_responsibility": 185.00,
                        "_delta": None
                    }
                ],
                "remits": [
                    {
                        "record_id": "RMT-001",
                        "remit_date": "2024-09-22",
                        "claim_reference": "CLM-2024-667788",
                        "payer": "Aetna",
                        "payment_amount": 0.00,
                        "adjustment_amount": 185.00,
                        "adjustment_reason_codes": ["PR-1"],
                        "remark_codes": ["N130"],
                        "remark_text": "Deductible amount - patient responsibility",
                        "_delta": None
                    }
                ],
                "transactions": [
                    {
                        "record_id": "TXN-001",
                        "transaction_date": "2024-09-10",
                        "type": "charge",
                        "amount": 185.00,
                        "description": "Office visit - established patient, low complexity (99213)",
                        "_delta": None
                    },
                    {
                        "record_id": "TXN-002",
                        "transaction_date": "2024-09-25",
                        "type": "patient_transfer",
                        "amount": 0.00,
                        "description": "Balance transferred to patient responsibility - deductible",
                        "_delta": "added"
                    }
                ],
                "notes": [
                    {
                        "record_id": "NOTE-001",
                        "note_date": "2024-09-25T10:30:00Z",
                        "author": "OPR-3315",
                        "author_type": "operator",
                        "note_type": "action",
                        "content": "Reviewed PR-1 adjustment on claim CLM-2024-667788. Confirmed patient deductible not met per Aetna EOB. Full balance of $185.00 is patient responsibility. Transferred to patient AR and generated initial patient statement. Statement mailed to patient address on file.",
                        "_delta": "added"
                    }
                ]
            },
            "state_summary": "Balance of $185.00 transferred to patient responsibility. Initial patient statement generated and mailed. Account moved to patient collections workflow."
        }
    ],
    "resolution": {
        "final_status": "transferred_to_patient",
        "final_balance": 185.00,
        "total_collected": 0.00,
        "total_adjustments": 0.00,
        "days_to_resolution": 0,
        "actions_taken": 1,
        "resolution_path": ["deductible_applied", "transferred_to_patient"]
    }
}


# All few-shot examples
FEW_SHOT_EXAMPLES = [
    EXAMPLE_SCENARIO_CO16_APPEAL,
    EXAMPLE_SCENARIO_PR1_PATIENT,
]


def get_few_shot_examples(
    count: int = 2,
    denial_codes: Optional[List[str]] = None
) -> List[Dict]:
    """Get few-shot examples for in-context learning. Optionally filter by denial codes."""
    examples = FEW_SHOT_EXAMPLES
    
    if denial_codes:
        examples = [
            e for e in examples 
            if e.get("scenario_metadata", {}).get("denial_code") in denial_codes
        ]
    
    return examples[:count]


GENERATION_PROMPT_TEMPLATE = """Generate a realistic AR billing scenario based on the following seed:

## SEED PARAMETERS
- Denial Code: {denial_code}
- Denial Description: {denial_description}
- Complexity: {complexity}
- Service Type: {service_type}

## DENIAL CODE DETAILS
{denial_details}

## TYPICAL RESOLUTION PATH
Based on this denial code, here are the typical actions and outcomes:
- Typical Actions: {typical_actions}
- Documentation Needed: {documentation_needed}
- Appeal Success Rate: {appeal_success_rate}
- Average Resolution Days: {avg_resolution_days}

## REQUIREMENTS

1. **Structure**: Follow the exact JSON schema provided in the system prompt.

2. **Timeline**: Generate a realistic timeline with:
   - Frame 1: Account drops to workqueue (initial state after denial)
   - Frame 2+: Operator actions and/or async events leading to resolution
   - Include realistic time gaps between frames (hours to weeks depending on action)

3. **Logical Consistency**:
   - Actions must satisfy preconditions (e.g., can't appeal a paid claim)
   - State changes must reflect action postconditions
   - Financial transactions must balance correctly

4. **Content Quality**:
   - Generate realistic patient demographics (use diverse names, ages)
   - Use appropriate CPT codes for the service type
   - Write detailed, realistic notes that an actual billing operator would write
   - Include specific details like check numbers, appeal references

5. **Delta Tracking**:
   - New records: _delta = "added"
   - Modified records: _delta = "updated" with _changed_fields
   - Unchanged records: _delta = null

## OUTPUT FORMAT
Return ONLY valid JSON matching the scenario schema. Do not include any text before or after the JSON.

{additional_instructions}

Generate the scenario now:
"""


def get_generation_prompt(
    denial_code: str,
    complexity: str = "moderate",
    service_type: str = "outpatient",
    additional_instructions: str = "",
) -> str:
    """
    Generate a prompt for scenario generation.
    
    Args:
        denial_code: The denial code to seed the scenario
        complexity: "simple", "moderate", or "complex"
        service_type: "outpatient" or "inpatient"
        additional_instructions: Any additional constraints or instructions
        
    Returns:
        Formatted generation prompt
    """
    denial_info = DENIAL_CATALOG.get(denial_code, {})
    
    return GENERATION_PROMPT_TEMPLATE.format(
        denial_code=denial_code,
        denial_description=denial_info.get("description", "Unknown denial code"),
        complexity=complexity,
        service_type=service_type,
        denial_details=json.dumps(denial_info, indent=2),
        typical_actions=", ".join(denial_info.get("typical_actions", [])),
        documentation_needed=", ".join(denial_info.get("documentation_needed", ["None"])),
        appeal_success_rate=f"{denial_info.get('appeal_success_rate', 0.5) * 100:.0f}%",
        avg_resolution_days=denial_info.get("avg_resolution_days", 30),
        additional_instructions=additional_instructions,
    )


REPAIR_PROMPT_TEMPLATE = """The following AR billing scenario has validation errors that need to be fixed.

## ORIGINAL SCENARIO
```json
{scenario_json}
```

## VALIDATION ERRORS
The following issues were found:

{errors}

## REPAIR INSTRUCTIONS
Please fix ALL the validation errors above while:
1. Maintaining the overall narrative and intent of the scenario
2. Preserving all correct data and structure
3. Making minimal changes necessary to fix each error
4. Ensuring the repaired scenario passes all validation checks

## OUTPUT FORMAT
Return ONLY the corrected JSON. Do not include any explanation or text outside the JSON.

Corrected scenario:
"""


def get_repair_prompt(scenario: Dict, validation_errors: List[Dict]) -> str:
    """Generate a prompt to repair validation errors."""
    error_lines = []
    for i, error in enumerate(validation_errors, 1):
        error_lines.append(f"{i}. [{error['category']}] {error['path']}: {error['message']}")
        if error.get('expected'):
            error_lines.append(f"   Expected: {error['expected']}")
        if error.get('actual'):
            error_lines.append(f"   Actual: {error['actual']}")
        if error.get('suggestion'):
            error_lines.append(f"   Suggestion: {error['suggestion']}")
    
    return REPAIR_PROMPT_TEMPLATE.format(
        scenario_json=json.dumps(scenario, indent=2),
        errors="\n".join(error_lines),
    )


def export_prompt_context() -> str:
    """Export all context needed for LLM prompting as a single string."""
    sections = [
        get_system_prompt(include_schemas=True),
        "\n\n## FEW-SHOT EXAMPLES\n",
        "Here are examples of correctly formatted scenarios:\n",
    ]
    
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        sections.append(f"\n### Example {i}: {example['scenario_metadata']['denial_code']}\n")
        sections.append(f"```json\n{json.dumps(example, indent=2)}\n```\n")
    
    return "\n".join(sections)
