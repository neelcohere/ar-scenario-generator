from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING = "pending"
    DENIED = "denied"
    PARTIALLY_DENIED = "partially_denied"
    APPEAL_SUBMITTED = "appeal_submitted"
    APPEAL_PENDING = "appeal_pending"
    APPEAL_APPROVED = "appeal_approved"
    APPEAL_DENIED = "appeal_denied"
    PAID = "paid"
    CLOSED = "closed"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class EventType(str, Enum):
    ACCOUNT_CREATED = "account_created"
    CLAIM_SUBMITTED = "claim_submitted"
    DENIAL_RECEIVED = "denial_received"
    ACCOUNT_DROPS_TO_WORKQUEUE = "account_drops_to_workqueue"
    OPERATOR_ACTION = "operator_action"
    ASYNC_PROCESS = "async_process"
    PAYMENT_RECEIVED = "payment_received"
    ACCOUNT_RESOLVED = "account_resolved"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class ActionType(str, Enum):
    SUBMIT_APPEAL = "submit_appeal"
    CORRECT_AND_REBILL = "correct_and_rebill"
    POST_ADJUSTMENT = "post_adjustment"
    TRANSFER_TO_PATIENT = "transfer_to_patient"
    WRITE_OFF = "write_off"
    REQUEST_RECORDS = "request_records"
    CONTACT_PAYER = "contact_payer"
    ESCALATE = "escalate"
    ADD_NOTE = "add_note"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class TransactionType(str, Enum):
    CHARGE = "charge"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    CONTRACTUAL_ADJUSTMENT = "contractual_adjustment"
    WRITE_OFF = "write_off"
    DENIAL_POSTED = "denial_posted"
    APPEAL_SUBMITTED = "appeal_submitted"
    REBILL = "rebill"
    PATIENT_TRANSFER = "patient_transfer"
    REFUND = "refund"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class NoteType(str, Enum):
    ACTION = "action"
    REVIEW = "review"
    PAYMENT_POSTING = "payment_posting"
    SYSTEM = "system"
    CLINICAL = "clinical"
    FOLLOW_UP = "follow_up"
    
    @classmethod
    def values(cls) -> List[str]:
        return [e.value for e in cls]


class DeltaType(str, Enum):
    ADDED = "added"
    UPDATED = "updated"
    UNCHANGED = None  # null in JSON
    
    @classmethod
    def values(cls) -> List[Optional[str]]:
        return ["added", "updated", None]


RECORD_SCHEMAS = {
    "demographics": {
        "description": "Patient and insurance information for the account",
        "fields": {
            "record_id": {"type": "string", "required": True, "pattern": "DEM-\\d+"},
            "patient_name": {"type": "string", "required": True, "format": "LastName, FirstName M."},
            "dob": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "mrn": {"type": "string", "required": True, "pattern": "MRN-\\d+"},
            "insurance_id": {"type": "string", "required": True},
            "payer_name": {"type": "string", "required": True},
            "payer_code": {"type": "string", "required": True},
            "policy_status": {"type": "string", "required": True, "enum": ["active", "inactive", "terminated"]},
            "subscriber_relationship": {"type": "string", "required": False, "enum": ["self", "spouse", "child", "other"]},
            "_delta": {"type": "string|null", "required": False, "enum": ["added", "updated", None]},
        },
    },
    
    "claims": {
        "description": "Claim records submitted to payers",
        "fields": {
            "record_id": {"type": "string", "required": True, "pattern": "CLM-\\d+"},
            "claim_number": {"type": "string", "required": True, "pattern": "CLM-\\d{4}-\\d+"},
            "service_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "procedure_codes": {"type": "array[string]", "required": True, "description": "CPT/HCPCS codes"},
            "diagnosis_codes": {"type": "array[string]", "required": True, "description": "ICD-10 codes"},
            "billed_amount": {"type": "number", "required": True, "min": 0},
            "status": {"type": "string", "required": True, "enum": ClaimStatus.values()},
            "submission_date": {"type": "string", "required": False, "format": "YYYY-MM-DD"},
            "denial_date": {"type": "string", "required": False, "format": "YYYY-MM-DD"},
            "denial_codes": {"type": "array[string]", "required": False, "description": "CARC codes like CO-16, PR-1"},
            "appeal_date": {"type": "string", "required": False, "format": "YYYY-MM-DD"},
            "appeal_reference": {"type": "string", "required": False, "pattern": "APL-\\d{4}-\\d+"},
            "paid_amount": {"type": "number", "required": False, "min": 0},
            "contractual_adjustment": {"type": "number", "required": False, "min": 0},
            "patient_responsibility": {"type": "number", "required": False, "min": 0},
            "timely_filing_deadline": {"type": "string", "required": False, "format": "YYYY-MM-DD"},
            "_delta": {"type": "string|null", "required": False, "enum": ["added", "updated", None]},
            "_changed_fields": {"type": "array[string]", "required": False, "description": "List of fields that changed"},
        },
    },
    
    "remits": {
        "description": "Remittance advice records from payers (ERA/835)",
        "fields": {
            "record_id": {"type": "string", "required": True, "pattern": "RMT-\\d+"},
            "remit_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "claim_reference": {"type": "string", "required": True, "description": "Links to claim_number"},
            "payer": {"type": "string", "required": True},
            "payment_amount": {"type": "number", "required": True},
            "adjustment_amount": {"type": "number", "required": True},
            "adjustment_reason_codes": {"type": "array[string]", "required": True, "description": "CARC codes"},
            "remark_codes": {"type": "array[string]", "required": False, "description": "RARC codes like N56, MA130"},
            "remark_text": {"type": "string", "required": False, "description": "Human-readable denial/adjustment reason"},
            "check_number": {"type": "string", "required": False},
            "_delta": {"type": "string|null", "required": False, "enum": ["added", "updated", None]},
        },
    },
    
    "transactions": {
        "description": "Financial transaction ledger for the account",
        "fields": {
            "record_id": {"type": "string", "required": True, "pattern": "TXN-\\d+"},
            "transaction_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
            "type": {"type": "string", "required": True, "enum": TransactionType.values()},
            "amount": {"type": "number", "required": True, "description": "Positive = increases balance, Negative = decreases balance"},
            "description": {"type": "string", "required": False},
            "reference": {"type": "string", "required": False, "description": "Links to remit, appeal, or other record"},
            "_delta": {"type": "string|null", "required": False, "enum": ["added", "updated", None]},
        },
    },
    
    "notes": {
        "description": "Account notes documenting actions and communications",
        "fields": {
            "record_id": {"type": "string", "required": True, "pattern": "NOTE-\\d+"},
            "note_date": {"type": "string", "required": True, "format": "ISO8601 datetime"},
            "author": {"type": "string", "required": True, "description": "Operator ID or 'SYSTEM'"},
            "author_type": {"type": "string", "required": True, "enum": ["operator", "automated", "clinical"]},
            "note_type": {"type": "string", "required": True, "enum": NoteType.values()},
            "content": {"type": "string", "required": True, "description": "The note text - should be detailed and realistic"},
            "_delta": {"type": "string|null", "required": False, "enum": ["added", "updated", None]},
        },
    },
}


DENIAL_CATALOG = {
    "CO-4": {
        "code": "CO-4",
        "group": "CO",  # Contractual Obligation
        "description": "The procedure code is inconsistent with the modifier used or a required modifier is missing",
        "category": "coding_error",
        "common_causes": [
            "Modifier missing on procedure code",
            "Incorrect modifier applied",
            "Modifier not supported for procedure",
        ],
        "typical_actions": ["correct_and_rebill", "submit_appeal"],
        "documentation_needed": ["Corrected claim form", "Modifier guidelines from payer"],
        "appeal_success_rate": 0.7,
        "avg_resolution_days": 14,
        "urgency": "medium",
    },
    
    "CO-16": {
        "code": "CO-16",
        "group": "CO",
        "description": "Claim/service lacks information which is needed for adjudication",
        "category": "missing_information",
        "common_causes": [
            "Missing clinical documentation",
            "Incomplete prior authorization",
            "Missing referral information",
            "Insufficient medical necessity documentation",
        ],
        "typical_actions": ["submit_appeal", "request_records"],
        "documentation_needed": ["Clinical notes", "Lab results", "Imaging reports", "Prior authorization"],
        "appeal_success_rate": 0.65,
        "avg_resolution_days": 30,
        "urgency": "medium",
    },
    
    "CO-18": {
        "code": "CO-18",
        "group": "CO",
        "description": "Exact duplicate claim/service",
        "category": "duplicate",
        "common_causes": [
            "Claim submitted twice in error",
            "System resubmission glitch",
            "Incorrect date of service on rebill",
        ],
        "typical_actions": ["write_off", "correct_and_rebill"],
        "documentation_needed": [],
        "appeal_success_rate": 0.2,
        "avg_resolution_days": 7,
        "urgency": "low",
    },
    
    "CO-45": {
        "code": "CO-45",
        "group": "CO",
        "description": "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement",
        "category": "contractual",
        "common_causes": [
            "Billed amount exceeds contracted rate",
            "Fee schedule maximum applied",
        ],
        "typical_actions": ["post_adjustment"],
        "documentation_needed": [],
        "appeal_success_rate": 0.05,
        "avg_resolution_days": 1,
        "urgency": "low",
    },
    
    "CO-97": {
        "code": "CO-97",
        "group": "CO",
        "description": "The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated",
        "category": "bundling",
        "common_causes": [
            "Procedure bundled with primary service",
            "Inclusive service not separately payable",
            "NCCI edit applied",
        ],
        "typical_actions": ["submit_appeal", "post_adjustment"],
        "documentation_needed": ["Operative report", "Documentation of distinct service"],
        "appeal_success_rate": 0.4,
        "avg_resolution_days": 45,
        "urgency": "medium",
    },
    
    "CO-109": {
        "code": "CO-109",
        "group": "CO",
        "description": "Claim/service not covered by this payer/contractor",
        "category": "coverage",
        "common_causes": [
            "Service not in benefit plan",
            "Out of network provider",
            "Coordination of benefits issue",
        ],
        "typical_actions": ["transfer_to_patient", "submit_appeal"],
        "documentation_needed": ["Benefit verification", "Network status documentation"],
        "appeal_success_rate": 0.3,
        "avg_resolution_days": 21,
        "urgency": "medium",
    },
    
    "CO-167": {
        "code": "CO-167",
        "group": "CO",
        "description": "This (these) diagnosis(es) is (are) not covered",
        "category": "coverage",
        "common_causes": [
            "Diagnosis not covered under plan",
            "Pre-existing condition exclusion",
            "Cosmetic/elective procedure",
        ],
        "typical_actions": ["submit_appeal", "transfer_to_patient"],
        "documentation_needed": ["Medical necessity letter", "Clinical documentation"],
        "appeal_success_rate": 0.35,
        "avg_resolution_days": 30,
        "urgency": "medium",
    },
    
    "PR-1": {
        "code": "PR-1",
        "group": "PR",  # Patient Responsibility
        "description": "Deductible amount",
        "category": "patient_responsibility",
        "common_causes": [
            "Patient deductible not yet met",
            "Annual deductible reset",
        ],
        "typical_actions": ["transfer_to_patient"],
        "documentation_needed": [],
        "appeal_success_rate": 0.05,
        "avg_resolution_days": 60,
        "urgency": "low",
    },
    
    "PR-2": {
        "code": "PR-2",
        "group": "PR",
        "description": "Coinsurance amount",
        "category": "patient_responsibility",
        "common_causes": [
            "Patient responsible for coinsurance percentage",
            "Out-of-pocket maximum not met",
        ],
        "typical_actions": ["transfer_to_patient"],
        "documentation_needed": [],
        "appeal_success_rate": 0.05,
        "avg_resolution_days": 45,
        "urgency": "low",
    },
    
    "PR-3": {
        "code": "PR-3",
        "group": "PR",
        "description": "Co-payment amount",
        "category": "patient_responsibility",
        "common_causes": [
            "Patient copay not collected at time of service",
        ],
        "typical_actions": ["transfer_to_patient"],
        "documentation_needed": [],
        "appeal_success_rate": 0.05,
        "avg_resolution_days": 30,
        "urgency": "low",
    },
    
    "CO-22": {
        "code": "CO-22",
        "group": "CO",
        "description": "This care may be covered by another payer per coordination of benefits",
        "category": "coordination_of_benefits",
        "common_causes": [
            "Primary payer not billed first",
            "Incorrect payer sequence",
            "Medicare Secondary Payer situation",
        ],
        "typical_actions": ["correct_and_rebill"],
        "documentation_needed": ["Primary payer EOB", "COB information"],
        "appeal_success_rate": 0.8,
        "avg_resolution_days": 21,
        "urgency": "high",
    },
    
    "CO-29": {
        "code": "CO-29",
        "group": "CO",
        "description": "The time limit for filing has expired",
        "category": "timely_filing",
        "common_causes": [
            "Claim submitted after filing deadline",
            "Appeal submitted late",
            "Corrected claim past deadline",
        ],
        "typical_actions": ["submit_appeal", "write_off"],
        "documentation_needed": ["Proof of timely submission", "Extenuating circumstances documentation"],
        "appeal_success_rate": 0.15,
        "avg_resolution_days": 30,
        "urgency": "high",
    },
}


ACTION_DEFINITIONS = {
    "submit_appeal": {
        "action": "submit_appeal",
        "description": "Submit a formal appeal to the payer contesting the denial",
        "actor": "operator",
        "preconditions": {
            "claim_status": {
                "must_be_in": ["denied", "partially_denied", "appeal_denied"],
                "description": "Claim must be in a denied state to appeal",
            },
            "timely_filing": {
                "check": "appeal_deadline_not_passed",
                "description": "Must be within appeal filing window",
            },
            "no_pending_appeal": {
                "check": "appeal_reference_is_null",
                "description": "Cannot submit appeal if one is already pending",
            },
        },
        "postconditions": {
            "claim_updates": {
                "status": "appeal_submitted",
                "appeal_date": "SET_TO_EVENT_DATE",
                "appeal_reference": "GENERATE_NEW",
                "_delta": "updated",
                "_changed_fields": ["status", "appeal_date", "appeal_reference"],
            },
            "new_transaction": {
                "type": "appeal_submitted",
                "amount": 0,
                "reference": "APPEAL_REFERENCE",
                "_delta": "added",
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["denial_code", "appeal_reference", "documentation_attached"],
                "_delta": "added",
            },
        },
        "typical_documentation": ["clinical_notes", "lab_results", "imaging_reports", "medical_necessity_letter"],
    },
    
    "correct_and_rebill": {
        "action": "correct_and_rebill",
        "description": "Correct the claim error and resubmit to payer",
        "actor": "operator",
        "preconditions": {
            "claim_status": {
                "must_be_in": ["denied"],
                "description": "Claim must be denied to correct and rebill",
            },
            "correctable_error": {
                "check": "denial_code_is_correctable",
                "correctable_codes": ["CO-4", "CO-22", "CO-16"],
                "description": "Denial must be for a correctable error",
            },
            "timely_filing": {
                "check": "timely_filing_deadline_not_passed",
                "description": "Must be within timely filing window",
            },
        },
        "postconditions": {
            "claim_updates": {
                "status": "submitted",
                "_delta": "updated",
                "_changed_fields": ["status"],
            },
            "new_transaction": {
                "type": "rebill",
                "amount": 0,
                "description": "CORRECTION_DESCRIPTION",
                "_delta": "added",
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["correction_type", "original_error"],
                "_delta": "added",
            },
        },
    },
    
    "post_adjustment": {
        "action": "post_adjustment",
        "description": "Post a financial adjustment to the account balance",
        "actor": "operator",
        "preconditions": {
            "has_balance": {
                "check": "account_balance_not_zero",
                "description": "Account must have a balance to adjust",
            },
            "valid_reason": {
                "check": "adjustment_reason_provided",
                "description": "Must have valid adjustment reason",
            },
        },
        "postconditions": {
            "new_transaction": {
                "type": "adjustment",
                "amount": "NEGATIVE_ADJUSTMENT_AMOUNT",
                "description": "ADJUSTMENT_REASON",
                "_delta": "added",
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["adjustment_amount", "adjustment_reason"],
                "_delta": "added",
            },
            "balance_change": {
                "check": "balance_reduced_by_adjustment_amount",
            },
        },
    },
    
    "transfer_to_patient": {
        "action": "transfer_to_patient",
        "description": "Transfer remaining balance to patient responsibility",
        "actor": "operator",
        "preconditions": {
            "patient_responsibility_confirmed": {
                "check": "denial_is_patient_responsibility",
                "pr_codes": ["PR-1", "PR-2", "PR-3"],
                "description": "Balance must be confirmed as patient responsibility",
            },
        },
        "postconditions": {
            "new_transaction": {
                "type": "patient_transfer",
                "amount": 0,
                "description": "Transferred to patient responsibility",
                "_delta": "added",
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["transfer_amount", "patient_statement"],
                "_delta": "added",
            },
        },
    },
    
    "write_off": {
        "action": "write_off",
        "description": "Write off the remaining balance as uncollectible",
        "actor": "operator",
        "preconditions": {
            "has_balance": {
                "check": "account_balance_not_zero",
                "description": "Account must have a balance to write off",
            },
            "meets_criteria": {
                "check": "writeoff_criteria_met",
                "valid_reasons": ["bad_debt", "small_balance", "timely_filing_expired", "charity"],
                "description": "Must meet write-off criteria",
            },
        },
        "postconditions": {
            "claim_updates": {
                "status": "closed",
                "_delta": "updated",
                "_changed_fields": ["status"],
            },
            "new_transaction": {
                "type": "write_off",
                "amount": "NEGATIVE_BALANCE",
                "description": "WRITEOFF_REASON",
                "_delta": "added",
            },
            "new_note": {
                "required": True,
                "note_type": "action",
                "must_contain": ["writeoff_amount", "writeoff_reason"],
                "_delta": "added",
            },
            "balance_change": {
                "check": "balance_is_zero",
            },
        },
    },
}


ASYNC_EVENT_DEFINITIONS = {
    "appeal_approved": {
        "event_type": "async_process",
        "trigger": "payer_response",
        "description": "Payer approves the appeal and issues payment",
        "preconditions": {
            "claim_status": {
                "must_be_in": ["appeal_submitted", "appeal_pending"],
            },
        },
        "postconditions": {
            "claim_updates": {
                "status": "paid",
                "paid_amount": "PAYMENT_AMOUNT",
                "contractual_adjustment": "BILLED_MINUS_PAID",
                "_delta": "updated",
            },
            "new_remit": {
                "payment_amount": "PAYMENT_AMOUNT",
                "adjustment_reason_codes": ["CO-45"],  # Contractual if applicable
                "_delta": "added",
            },
            "new_transactions": [
                {"type": "payment", "amount": "NEGATIVE_PAYMENT", "_delta": "added"},
                {"type": "contractual_adjustment", "amount": "NEGATIVE_ADJUSTMENT", "_delta": "added"},
            ],
            "new_note": {
                "author": "SYSTEM",
                "author_type": "automated",
                "note_type": "payment_posting",
                "_delta": "added",
            },
        },
    },
    
    "appeal_denied": {
        "event_type": "async_process",
        "trigger": "payer_response",
        "description": "Payer denies the appeal, upholding original denial",
        "preconditions": {
            "claim_status": {
                "must_be_in": ["appeal_submitted", "appeal_pending"],
            },
        },
        "postconditions": {
            "claim_updates": {
                "status": "appeal_denied",
                "_delta": "updated",
            },
            "new_note": {
                "author": "SYSTEM",
                "author_type": "automated",
                "note_type": "system",
                "must_contain": ["appeal_denied", "denial_reason"],
                "_delta": "added",
            },
        },
    },
    
    "payment_received": {
        "event_type": "payment_received",
        "trigger": "system_automated",
        "description": "Payment posted to the account",
        "postconditions": {
            "new_remit": {
                "payment_amount": "PAYMENT_AMOUNT",
                "_delta": "added",
            },
            "new_transaction": {
                "type": "payment",
                "amount": "NEGATIVE_PAYMENT",
                "_delta": "added",
            },
            "new_note": {
                "author": "SYSTEM",
                "author_type": "automated",
                "note_type": "payment_posting",
                "_delta": "added",
            },
        },
    },
}


PAYER_CATALOG = [
    {"name": "Aetna", "code": "AET"},
    {"name": "Alignment Healthcare", "code": "ALG"},
    {"name": "Aloha Care", "code": "ALC"},
    {"name": "AmeriHealth", "code": "AMH"},
    {"name": "Arkansas Blue Cross", "code": "ABC"},
    {"name": "AultCare Corporation", "code": "AUC"},
    {"name": "Aultman Health", "code": "AUH"},
    {"name": "Avera Health Plans", "code": "AVH"},
    {"name": "AvMed Health Plan", "code": "AVM"},
    {"name": "Baylor Scott & White Health Plan", "code": "BSW"},
    {"name": "Baystate Health", "code": "BSH"},
    {"name": "Blue Cross and Blue Shield of New Mexico", "code": "BCBSNM"},
    {"name": "Blue Cross and Blue Shield of Georgia", "code": "BCBSGA"},
    {"name": "Blue Cross and Blue Shield of Illinois", "code": "BCBSIL"},
    {"name": "Blue Cross and Blue Shield of Montana", "code": "BCBSMT"},
    {"name": "Blue Cross Blue Shield of Alabama", "code": "BCBSAL"},
    {"name": "Blue Cross Blue Shield of Arizona", "code": "BCBSAZ"},
    {"name": "Blue Cross Blue Shield of Kansas City", "code": "BCBSKC"},
    {"name": "Blue Cross Blue Shield of Louisiana", "code": "BCBSLA"},
    {"name": "Blue Cross Blue Shield of Massachusetts", "code": "BCBSMA"},
    {"name": "Blue Cross Blue Shield of Michigan", "code": "BCBSMI"},
    {"name": "Blue Cross Blue Shield of Minnesota", "code": "BCBSMN"},
    {"name": "Blue Cross Blue Shield of Mississippi", "code": "BCBSMS"},
    {"name": "Blue Cross Blue Shield of Nebraska", "code": "BCBSNE"},
    {"name": "Blue Cross Blue Shield of North Carolina", "code": "BCBSNC"},
    {"name": "Blue Cross Blue Shield of North Dakota", "code": "BCBSND"},
    {"name": "Blue Cross Blue Shield of South Carolina", "code": "BCBSSC"},
    {"name": "Blue Cross Blue Shield of Tennessee", "code": "BCBSTN"},
    {"name": "Blue Cross Blue Shield of Vermont", "code": "BCBSVT"},
    {"name": "Blue Cross Blue Shield of Wyoming", "code": "BCBSWY"},
    {"name": "Blue Cross Blue Shield Rhode Island", "code": "BCBSRI"},
    {"name": "Blue Cross of Idaho", "code": "BCID"},
    {"name": "Blue Shield of California", "code": "BSC"},
    {"name": "BlueCross BlueShield of Oklahoma", "code": "BCBSOK"},
    {"name": "BlueCross BlueShield of Texas", "code": "BCBSTX"},
    {"name": "Boston Medical Center", "code": "BMC"},
    {"name": "Bright Health", "code": "BRH"},
    {"name": "Capital Blue Cross", "code": "CBC"},
    {"name": "Capital District Physicians Health Plan", "code": "CDPHP"},
    {"name": "Carefirst", "code": "CRF"},
    {"name": "CareOregon", "code": "COR"},
    {"name": "Caresource", "code": "CRS"},
    {"name": "Carle Health", "code": "CHL"},
    {"name": "Celtic Insurance Company", "code": "CEL"},
    {"name": "Centene", "code": "CEN"},
    {"name": "Chorus Health Plans", "code": "CHP"},
    {"name": "Cigna", "code": "CIG"},
    {"name": "Clever Care Health Plan", "code": "CCH"},
    {"name": "Clover Health", "code": "CLV"},
    {"name": "Colorado Access", "code": "COA"},
    {"name": "Common Ground Healthcare Cooperative", "code": "CGHC"},
    {"name": "Commonwealth Care Alliance", "code": "CCA"},
    {"name": "Community Care", "code": "CMC"},
    {"name": "Community First Health Plans", "code": "CFH"},
    {"name": "Community Health Network", "code": "CHN"},
    {"name": "Cook Children's Health Plan", "code": "CCK"},
    {"name": "Corewell", "code": "CWL"},
    {"name": "Curative", "code": "CUR"},
    {"name": "Dean Health Plan", "code": "DHP"},
    {"name": "Denver Health Medical Plan", "code": "DHM"},
    {"name": "Devoted Health", "code": "DVT"},
    {"name": "Driscoll Children's Health Plan", "code": "DCH"},
    {"name": "El Paso First Health Plans", "code": "EPF"},
    {"name": "Elderplan", "code": "ELD"},
    {"name": "Elevance", "code": "ELV"},
    {"name": "Emblem Health", "code": "EMB"},
    {"name": "Empower Healthcare Solutions", "code": "EMP"},
    {"name": "Essence Healthcare", "code": "ESS"},
    {"name": "Excellus Blue Cross Blue Shield", "code": "EXC"},
    {"name": "Fallon Health", "code": "FAL"},
    {"name": "First Choice Health", "code": "FCH"},
    {"name": "Florida Blue", "code": "FLB"},
    {"name": "Geisinger", "code": "GEI"},
    {"name": "Group Health Cooperative of Eau Claire", "code": "GHC"},
    {"name": "Gunderson Health System", "code": "GHS"},
    {"name": "Harris Health System", "code": "HHS"},
    {"name": "Harvard Pilgrim Health Care", "code": "HPH"},
    {"name": "Hawaii Medical Service Association", "code": "HMSA"},
    {"name": "Health Alliance Medical Plan", "code": "HAM"},
    {"name": "Health Care Service Corporation", "code": "HCSC"},
    {"name": "Health First", "code": "HF1"},
    {"name": "Health Plan of San Joaquin", "code": "HPSJ"},
    {"name": "HealthEquity", "code": "HEQ"},
    {"name": "HealthFirst", "code": "HF2"},
    {"name": "Hennepin Health", "code": "HNH"},
    {"name": "Henry Ford Hospital", "code": "HFH"},
    {"name": "Highmark", "code": "HMK"},
    {"name": "Hometown Health Plan", "code": "HTH"},
    {"name": "Horizon Blue Cross Blue Shield", "code": "HOR"},
    {"name": "Humana", "code": "HUM"},
    {"name": "Independence Blue Cross", "code": "IBC"},
    {"name": "Independent Health", "code": "INH"},
    {"name": "Indiana University Health Plans", "code": "IUH"},
    {"name": "Jefferson Health Plans", "code": "JEF"},
    {"name": "Johns Hopkins Health Plans", "code": "JHH"},
    {"name": "Kaiser Permanente", "code": "KP"},
    {"name": "L.A. Care", "code": "LAC"},
    {"name": "LEON Health", "code": "LEO"},
    {"name": "Lifepoint Health", "code": "LFP"},
    {"name": "Martin's Point Health Care", "code": "MPH"},
    {"name": "Mass General Brigham Health Plan", "code": "MGB"},
    {"name": "Mclaren Health Plan", "code": "MCL"},
    {"name": "Medica Health Plan", "code": "MED"},
    {"name": "Medical Mutual", "code": "MMU"},
    {"name": "Medstar Health", "code": "MST"},
    {"name": "Meridian Health Plan", "code": "MER"},
    {"name": "MetroPlusHealth", "code": "MPL"},
    {"name": "Moda Health", "code": "MOD"},
    {"name": "Molina", "code": "MOL"},
    {"name": "MVP Health Care", "code": "MVP"},
    {"name": "Neighborhood Health Plan of Rhode Island", "code": "NHP"},
    {"name": "Network Health", "code": "NWH"},
    {"name": "OhioHealthy Medical Plan", "code": "OHM"},
    {"name": "Oscar", "code": "OSC"},
    {"name": "PacificSource Health Plans", "code": "PSH"},
    {"name": "Paramount Health Care", "code": "PHC"},
    {"name": "Parkland Community Health Plan", "code": "PKL"},
    {"name": "Point32Health", "code": "P32"},
    {"name": "Premera Blue Cross", "code": "PBC"},
    {"name": "Presbyterian Healthcare Services", "code": "PHS"},
    {"name": "Promedica", "code": "PRO"},
    {"name": "Providence Health Plans", "code": "PVD"},
    {"name": "Quartz Health Solutions", "code": "QTZ"},
    {"name": "Regence", "code": "REG"},
    {"name": "Renown Health", "code": "REN"},
    {"name": "Samaritan Health Plans", "code": "SAM"},
    {"name": "San Francisco Health Plan", "code": "SFH"},
    {"name": "Sanford Health Plan", "code": "SAN"},
    {"name": "SCAN Health Plan", "code": "SCN"},
    {"name": "Security Health Plan", "code": "SEC"},
    {"name": "Sentara", "code": "SEN"},
    {"name": "Sharp Health Plan", "code": "SHP"},
    {"name": "South Florida Community Care Network", "code": "SFC"},
    {"name": "St. Luke's Health Plan", "code": "STL"},
    {"name": "SummaCare", "code": "SUM"},
    {"name": "Sutter Health Plus", "code": "SUT"},
    {"name": "Texas Children's Health Plan", "code": "TCH"},
    {"name": "Trinity Health", "code": "TRN"},
    {"name": "Trustmark Insurance Company", "code": "TRS"},
    {"name": "Tufts Health Plan", "code": "THP"},
    {"name": "Ucare", "code": "UCA"},
    {"name": "UNICARE Life & Health Insurance Company", "code": "UNI"},
    {"name": "United Health Group", "code": "UHG"},
    {"name": "Universal Health Service", "code": "UHS"},
    {"name": "University Health Alliance", "code": "UHA"},
    {"name": "UPMC Health Plan", "code": "UPM"},
    {"name": "Viva Health", "code": "VIV"},
    {"name": "Wellmark", "code": "WMK"},
    {"name": "Western Health Advantage", "code": "WHA"},
    {"name": "WPS Health Solutions", "code": "WPS"},
]


SCENARIO_SCHEMA = {
    "scenario_metadata": {
        "description": "Metadata about the generated scenario",
        "fields": {
            "scenario_id": {"type": "string", "required": True, "pattern": "SCN-\\d{4}-\\d+"},
            "scenario_type": {"type": "string", "required": True, "enum": ["denial_resolution", "payment_posting", "patient_collections"]},
            "denial_code": {"type": "string", "required": True, "description": "Primary denial code driving scenario"},
            "complexity": {"type": "string", "required": True, "enum": ["simple", "moderate", "complex"]},
            "generated_at": {"type": "string", "required": True, "format": "ISO8601"},
        },
    },
    "account": {
        "description": "Account identifiers",
        "fields": {
            "account_number": {"type": "string", "required": True, "pattern": "ACC-\\d+"},
            "facility": {"type": "string", "required": True},
            "service_date": {"type": "string", "required": True, "format": "YYYY-MM-DD"},
        },
    },
    "timeline": {
        "description": "Array of timeline frames representing account state evolution",
        "type": "array",
        "items": {
            "timestamp": {"type": "string", "required": True, "format": "ISO8601"},
            "frame_id": {"type": "string", "required": True, "pattern": "F\\d{3}"},
            "event_type": {"type": "string", "required": True, "enum": EventType.values()},
            "event": {"type": "object", "required": True, "description": "See EVENT_SCHEMA"},
            "account_state": {"type": "object", "required": True, "description": "See RECORD_SCHEMAS"},
            "state_summary": {"type": "string", "required": True, "description": "Brief natural language summary"},
        },
        "constraints": [
            "Timestamps must be in chronological order",
            "frame_id must increment (F001, F002, F003...)",
            "First frame should typically be 'account_drops_to_workqueue'",
            "Each frame's account_state must be consistent with prior frames plus event effects",
        ],
    },
    "resolution": {
        "description": "Final resolution outcome",
        "fields": {
            "final_status": {"type": "string", "required": True},
            "final_balance": {"type": "number", "required": True},
            "total_collected": {"type": "number", "required": True},
            "total_adjustments": {"type": "number", "required": True},
            "days_to_resolution": {"type": "integer", "required": True},
            "actions_taken": {"type": "integer", "required": True},
        },
    },
}


EVENT_SCHEMA = {
    "description": "Event that triggers state transition",
    "fields": {
        "trigger": {"type": "string", "required": True, "enum": ["system_automated", "user_initiated", "payer_response"]},
        "description": {"type": "string", "required": True, "description": "Detailed description of what happened"},
        "actor": {"type": "string", "required": True, "enum": ["system", "operator", "payer"]},
        "actor_id": {"type": "string", "required": False, "description": "Operator ID if actor is operator"},
        "action_taken": {"type": "string", "required": False, "enum": ActionType.values(), "description": "Required if event_type is operator_action"},
        "action_details": {"type": "object", "required": False, "description": "Action-specific parameters"},
    },
}


LOGICAL_CONSTRAINTS = {
    "temporal": [
        "All timestamps must be in chronological order",
        "service_date must be before all other dates",
        "denial_date must be after submission_date",
        "appeal_date must be after denial_date",
        "timely_filing_deadline must be after service_date (typically 90-365 days)",
    ],
    
    "financial": [
        "Initial charge transaction amount must equal billed_amount",
        "Sum of all transactions must equal current account balance",
        "payment amounts in transactions should be negative (reduces balance)",
        "adjustment amounts in transactions should be negative (reduces balance)",
        "paid_amount + contractual_adjustment + patient_responsibility should equal billed_amount when resolved",
    ],
    
    "state_transitions": [
        "Claim status can only transition through valid paths (denied -> appeal_submitted -> appeal_approved/appeal_denied)",
        "Cannot submit appeal if claim is not in denied state",
        "Cannot post payment if claim is not approved/paid",
        "Cannot write off if account balance is already zero",
    ],
    
    "delta_tracking": [
        "Records that change between frames must have _delta='updated' and _changed_fields populated",
        "New records must have _delta='added'",
        "Unchanged records should have _delta=null or be omitted",
        "If claim.status changes, _changed_fields must include 'status'",
    ],
    
    "referential_integrity": [
        "remit.claim_reference must match an existing claim.claim_number",
        "transaction.reference should match a valid remit, appeal, or other record",
        "notes should reference relevant claims or actions",
    ],
    
    "content_requirements": [
        "Notes must be substantive and describe the action taken",
        "Action notes must mention the denial code being addressed",
        "Appeal notes must include what documentation was attached",
        "Event descriptions should explain what triggered the event",
    ],
}


def get_schema_as_text() -> str:
    """Export all schemas as formatted text for LLM context."""
    sections = []
    
    sections.append("# AR BILLING SCENARIO SCHEMAS\n")
    
    # Record schemas
    sections.append("## RECORD SCHEMAS\n")
    for name, schema in RECORD_SCHEMAS.items():
        sections.append(f"### {name.upper()}\n")
        sections.append(f"{schema['description']}\n\nFields:")
        for field, spec in schema['fields'].items():
            req = "required" if spec.get('required') else "optional"
            sections.append(f"  - {field}: {spec['type']} ({req})")
            if 'description' in spec:
                sections.append(f"    Description: {spec['description']}")
            if 'enum' in spec:
                sections.append(f"    Valid values: {spec['enum']}")
        sections.append("")
    
    # Action definitions
    sections.append("## ACTION DEFINITIONS\n")
    for name, action in ACTION_DEFINITIONS.items():
        sections.append(f"### {name}\n")
        sections.append(f"Description: {action['description']}")
        sections.append(f"Actor: {action['actor']}\n")
        sections.append("Preconditions:")
        for cond, spec in action['preconditions'].items():
            sections.append(f"  - {cond}: {spec['description']}")
        sections.append("\nPostconditions:")
        for cond, spec in action['postconditions'].items():
            sections.append(f"  - {cond}: {spec}")
        sections.append("")
    
    return "\n".join(sections)


def get_denial_catalog_as_text() -> str:
    """Export denial catalog as formatted text for LLM context."""
    lines = ["# DENIAL CODE CATALOG\n"]
    
    for code, info in DENIAL_CATALOG.items():
        lines.append(f"## {code}: {info['description']}")
        lines.append(f"Category: {info['category']}")
        lines.append(f"Common causes: {', '.join(info['common_causes'])}")
        lines.append(f"Typical actions: {', '.join(info['typical_actions'])}")
        lines.append(f"Documentation needed: {', '.join(info['documentation_needed']) if info['documentation_needed'] else 'None'}")
        lines.append(f"Appeal success rate: {info['appeal_success_rate']*100:.0f}%")
        lines.append(f"Avg resolution days: {info['avg_resolution_days']}")
        lines.append("")
    
    return "\n".join(lines)


def get_constraints_as_text() -> str:
    """Export logical constraints as formatted text for LLM context."""
    lines = ["# LOGICAL CONSTRAINTS\n"]
    lines.append("The generated scenario MUST satisfy all of these constraints:\n")
    
    for category, rules in LOGICAL_CONSTRAINTS.items():
        lines.append(f"## {category.upper()}")
        for rule in rules:
            lines.append(f"  - {rule}")
        lines.append("")
    
    return "\n".join(lines)
