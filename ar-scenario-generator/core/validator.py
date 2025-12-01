from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import json

from .schemas import (
    RECORD_SCHEMAS, ACTION_DEFINITIONS, DENIAL_CATALOG, EventType
)


class ValidationSeverity(Enum):
    ERROR = "error"      # Must fix - scenario is invalid
    WARNING = "warning"  # Should fix - scenario may cause issues
    INFO = "info"        # Suggestion for improvement


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    category: str  # schema, temporal, financial, state, referential, content
    path: str      # JSON path to the issue (e.g., "timeline[0].account_state.claims[0].status")
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        result = {
            "severity": self.severity.value,
            "category": self.category,
            "path": self.path,
            "message": self.message,
        }
        if self.expected is not None:
            result["expected"] = self.expected
        if self.actual is not None:
            result["actual"] = self.actual
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def all_issues(self) -> List[ValidationIssue]:
        return self.errors + self.warnings + self.info
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def add_issue(self, issue: ValidationIssue):
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
        }
    
    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return f"{status} - {self.error_count} errors, {self.warning_count} warnings"


class ScenarioValidator:
    """
    Comprehensive validator for AR Billing Scenarios.
    
    Usage:
        validator = ScenarioValidator()
        result = validator.validate(scenario_dict)
        
        if not result.is_valid:
            for error in result.errors:
                print(f"ERROR: {error.message} at {error.path}")
    """
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
    
    def validate(self, scenario: Dict) -> ValidationResult:
        """Run all validations on a scenario."""
        result = ValidationResult(is_valid=True)
        
        # Run all validation checks
        self._validate_schema(scenario, result)
        self._validate_temporal(scenario, result)
        self._validate_financial(scenario, result)
        self._validate_state_transitions(scenario, result)
        self._validate_referential_integrity(scenario, result)
        self._validate_delta_tracking(scenario, result)
        self._validate_content_quality(scenario, result)
        
        # In strict mode, warnings become errors
        if self.strict_mode:
            for warning in result.warnings:
                warning.severity = ValidationSeverity.ERROR
                result.errors.append(warning)
            result.warnings = []
            if result.errors:
                result.is_valid = False
        
        return result
    
    def _validate_schema(self, scenario: Dict, result: ValidationResult):
        """Validate basic structure and required fields."""
        
        # Check top-level required fields
        for field in ["scenario_metadata", "account", "timeline"]:
            if field not in scenario:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path=field,
                    message=f"Missing required top-level field: {field}",
                ))
        
        # Validate scenario_metadata
        if "scenario_metadata" in scenario:
            self._validate_metadata(scenario["scenario_metadata"], result)
        
        # Validate account
        if "account" in scenario:
            self._validate_account(scenario["account"], result)
        
        # Validate timeline
        if "timeline" in scenario:
            self._validate_timeline_schema(scenario["timeline"], result)
    
    def _validate_metadata(self, metadata: Dict, result: ValidationResult):
        """Validate scenario_metadata structure."""
        required = ["scenario_id", "scenario_type", "denial_code", "complexity"]
        for field in required:
            if field not in metadata:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path=f"scenario_metadata.{field}",
                    message=f"Missing required field: {field}",
                ))
        
        # Validate scenario_id format
        if "scenario_id" in metadata:
            if not re.match(r"SCN-\d{4}-\d+", metadata["scenario_id"]):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="schema",
                    path="scenario_metadata.scenario_id",
                    message="scenario_id should match pattern SCN-YYYY-NNNNNN",
                    actual=metadata["scenario_id"],
                    expected="SCN-2024-123456",
                ))
        
        # Validate denial_code
        if "denial_code" in metadata:
            if metadata["denial_code"] not in DENIAL_CATALOG:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="schema",
                    path="scenario_metadata.denial_code",
                    message=f"Unknown denial code: {metadata['denial_code']}",
                    suggestion=f"Known codes: {list(DENIAL_CATALOG.keys())}",
                ))
    
    def _validate_account(self, account: Dict, result: ValidationResult):
        """Validate account structure."""
        required = ["account_number", "facility", "service_date"]
        for field in required:
            if field not in account:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path=f"account.{field}",
                    message=f"Missing required field: {field}",
                ))
        
        # Validate date format
        if "service_date" in account:
            if not self._is_valid_date(account["service_date"]):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path="account.service_date",
                    message="Invalid date format",
                    expected="YYYY-MM-DD",
                    actual=account["service_date"],
                ))
    
    def _validate_timeline_schema(self, timeline: List, result: ValidationResult):
        """Validate timeline array structure."""
        if not timeline:
            result.add_issue(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema",
                path="timeline",
                message="Timeline must contain at least one frame",
            ))
            return
        
        for i, frame in enumerate(timeline):
            path = f"timeline[{i}]"
            
            # Check required frame fields
            required = ["timestamp", "frame_id", "event_type", "event", "account_state", "state_summary"]
            for field in required:
                if field not in frame:
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="schema",
                        path=f"{path}.{field}",
                        message=f"Missing required field: {field}",
                    ))
            
            # Validate event_type
            if "event_type" in frame:
                if frame["event_type"] not in EventType.values():
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="schema",
                        path=f"{path}.event_type",
                        message=f"Invalid event_type",
                        actual=frame["event_type"],
                        expected=EventType.values(),
                    ))
            
            # Validate account_state structure
            if "account_state" in frame:
                self._validate_account_state(frame["account_state"], f"{path}.account_state", result)
    
    def _validate_account_state(self, state: Dict, path: str, result: ValidationResult):
        """Validate account_state structure and record schemas."""
        expected_tables = ["demographics", "claims", "remits", "transactions", "notes"]
        
        for table in expected_tables:
            if table not in state:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="schema",
                    path=f"{path}.{table}",
                    message=f"Missing table: {table}",
                    suggestion="All account state tables should be present (can be empty arrays)",
                ))
                continue
            
            if not isinstance(state[table], list):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path=f"{path}.{table}",
                    message=f"Table must be an array",
                    actual=type(state[table]).__name__,
                ))
                continue
            
            # Validate each record against schema
            schema = RECORD_SCHEMAS.get(table, {})
            for j, record in enumerate(state[table]):
                self._validate_record(record, schema, f"{path}.{table}[{j}]", result)
    
    def _validate_record(self, record: Dict, schema: Dict, path: str, result: ValidationResult):
        """Validate a single record against its schema."""
        if "fields" not in schema:
            return
        
        for field_name, field_spec in schema["fields"].items():
            # Check required fields
            if field_spec.get("required") and field_name not in record:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema",
                    path=f"{path}.{field_name}",
                    message=f"Missing required field: {field_name}",
                ))
                continue
            
            if field_name not in record:
                continue
            
            value = record[field_name]
            
            # Check enum values
            if "enum" in field_spec and value is not None:
                if value not in field_spec["enum"]:
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="schema",
                        path=f"{path}.{field_name}",
                        message=f"Invalid enum value",
                        actual=value,
                        expected=field_spec["enum"],
                    ))
    
    
    def _validate_temporal(self, scenario: Dict, result: ValidationResult):
        """Validate temporal consistency."""
        timeline = scenario.get("timeline", [])
        if not timeline:
            return
        
        service_date = scenario.get("account", {}).get("service_date")
        
        # Check chronological order
        prev_timestamp = None
        for i, frame in enumerate(timeline):
            timestamp = frame.get("timestamp")
            if not timestamp:
                continue
            
            current_ts = self._parse_datetime(timestamp)
            if current_ts is None:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="temporal",
                    path=f"timeline[{i}].timestamp",
                    message="Invalid timestamp format",
                    actual=timestamp,
                ))
                continue
            
            if prev_timestamp and current_ts < prev_timestamp:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="temporal",
                    path=f"timeline[{i}].timestamp",
                    message="Timestamps must be in chronological order",
                    actual=timestamp,
                    suggestion="Each frame's timestamp must be >= previous frame's timestamp",
                ))
            
            prev_timestamp = current_ts
        
        # Check service_date is before other dates
        if service_date:
            service_dt = self._parse_date(service_date)
            if service_dt:
                for i, frame in enumerate(timeline):
                    claims = frame.get("account_state", {}).get("claims", [])
                    for j, claim in enumerate(claims):
                        for date_field in ["denial_date", "appeal_date", "submission_date"]:
                            date_val = claim.get(date_field)
                            if date_val:
                                dt = self._parse_date(date_val)
                                if dt and dt < service_dt:
                                    result.add_issue(ValidationIssue(
                                        severity=ValidationSeverity.ERROR,
                                        category="temporal",
                                        path=f"timeline[{i}].account_state.claims[{j}].{date_field}",
                                        message=f"{date_field} cannot be before service_date",
                                        actual=date_val,
                                        expected=f"Date >= {service_date}",
                                    ))

    
    def _validate_financial(self, scenario: Dict, result: ValidationResult):
        """Validate financial consistency."""
        timeline = scenario.get("timeline", [])
        
        for i, frame in enumerate(timeline):
            state = frame.get("account_state", {})
            claims = state.get("claims", [])
            transactions = state.get("transactions", [])
            
            if not claims or not transactions:
                continue
            
            # Check that charge transaction matches billed amount
            for j, claim in enumerate(claims):
                billed = claim.get("billed_amount", 0)
                charge_txns = [t for t in transactions if t.get("type") == "charge"]
                
                if charge_txns:
                    total_charges = sum(t.get("amount", 0) for t in charge_txns)
                    if abs(total_charges - billed) > 0.01:
                        result.add_issue(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="financial",
                            path=f"timeline[{i}].account_state",
                            message="Total charge transactions should equal billed_amount",
                            expected=billed,
                            actual=total_charges,
                        ))
            
            # Check balance calculation
            balance = sum(t.get("amount", 0) for t in transactions)
            
            # Check that payments are negative
            for j, txn in enumerate(transactions):
                if txn.get("type") in ["payment", "adjustment", "contractual_adjustment", "write_off"]:
                    if txn.get("amount", 0) > 0:
                        result.add_issue(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="financial",
                            path=f"timeline[{i}].account_state.transactions[{j}]",
                            message=f"Transaction type '{txn.get('type')}' should have negative amount (reduces balance)",
                            actual=txn.get("amount"),
                        ))

    
    def _validate_state_transitions(self, scenario: Dict, result: ValidationResult):
        """Validate state machine transitions and action pre/postconditions."""
        timeline = scenario.get("timeline", [])
        
        for i in range(1, len(timeline)):
            prev_frame = timeline[i - 1]
            curr_frame = timeline[i]
            
            event = curr_frame.get("event", {})
            action = event.get("action_taken")
            
            if action and action in ACTION_DEFINITIONS:
                self._validate_action_preconditions(
                    prev_frame.get("account_state", {}),
                    action,
                    f"timeline[{i}]",
                    result
                )
                self._validate_action_postconditions(
                    prev_frame.get("account_state", {}),
                    curr_frame.get("account_state", {}),
                    action,
                    f"timeline[{i}]",
                    result
                )
    
    def _validate_action_preconditions(
        self,
        prev_state: Dict,
        action: str,
        path: str,
        result: ValidationResult
    ):
        """Validate that preconditions were met before action."""
        action_def = ACTION_DEFINITIONS.get(action, {})
        preconditions = action_def.get("preconditions", {})
        
        claims = prev_state.get("claims", [])
        claim = claims[0] if claims else {}
        
        # Check claim_status precondition
        if "claim_status" in preconditions:
            expected_statuses = preconditions["claim_status"].get("must_be_in", [])
            actual_status = claim.get("status")
            
            if expected_statuses and actual_status not in expected_statuses:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="state",
                    path=path,
                    message=f"Action '{action}' requires claim status to be in {expected_statuses}",
                    actual=actual_status,
                    expected=expected_statuses,
                ))
        
        # Check no_pending_appeal precondition
        if "no_pending_appeal" in preconditions:
            if claim.get("appeal_reference"):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="state",
                    path=path,
                    message=f"Action '{action}' cannot be taken when appeal is already pending",
                    actual=f"appeal_reference={claim.get('appeal_reference')}",
                ))
    
    def _validate_action_postconditions(
        self,
        prev_state: Dict,
        curr_state: Dict,
        action: str,
        path: str,
        result: ValidationResult
    ):
        """Validate that postconditions were satisfied after action."""
        action_def = ACTION_DEFINITIONS.get(action, {})
        postconditions = action_def.get("postconditions", {})
        
        curr_claims = curr_state.get("claims", [])
        curr_claim = curr_claims[0] if curr_claims else {}
        
        # Check claim_updates postcondition
        if "claim_updates" in postconditions:
            expected_status = postconditions["claim_updates"].get("status")
            if expected_status and curr_claim.get("status") != expected_status:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="state",
                    path=path,
                    message=f"After '{action}', claim status should be '{expected_status}'",
                    actual=curr_claim.get("status"),
                    expected=expected_status,
                ))
        
        # Check new_note postcondition
        if "new_note" in postconditions and postconditions["new_note"].get("required"):
            prev_notes = prev_state.get("notes", [])
            curr_notes = curr_state.get("notes", [])
            
            if len(curr_notes) <= len(prev_notes):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="state",
                    path=path,
                    message=f"Action '{action}' requires a new note to be added",
                    suggestion="Add a note documenting the action taken",
                ))
        
        # Check new_transaction postcondition
        if "new_transaction" in postconditions:
            prev_txns = prev_state.get("transactions", [])
            curr_txns = curr_state.get("transactions", [])
            
            expected_type = postconditions["new_transaction"].get("type")
            new_txns = [t for t in curr_txns if t not in prev_txns]
            
            if not any(t.get("type") == expected_type for t in new_txns):
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="state",
                    path=path,
                    message=f"Action '{action}' should add a '{expected_type}' transaction",
                ))
    
    
    def _validate_delta_tracking(self, scenario: Dict, result: ValidationResult):
        """Validate that deltas are correctly tracked between frames."""
        timeline = scenario.get("timeline", [])
        
        for i in range(1, len(timeline)):
            prev_frame = timeline[i - 1]
            curr_frame = timeline[i]
            
            prev_state = prev_frame.get("account_state", {})
            curr_state = curr_frame.get("account_state", {})
            
            for table in ["demographics", "claims", "remits", "transactions", "notes"]:
                prev_records = {r.get("record_id"): r for r in prev_state.get(table, [])}
                curr_records = curr_state.get(table, [])
                
                for j, record in enumerate(curr_records):
                    record_id = record.get("record_id")
                    delta = record.get("_delta")
                    
                    if record_id not in prev_records:
                        # New record - should have _delta = "added"
                        if delta != "added":
                            result.add_issue(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                category="delta",
                                path=f"timeline[{i}].account_state.{table}[{j}]",
                                message="New record should have _delta='added'",
                                actual=delta,
                                expected="added",
                            ))
                    else:
                        # Existing record - check if changed
                        prev_record = prev_records[record_id]
                        has_changes = self._record_has_changes(prev_record, record)
                        
                        if has_changes and delta != "updated":
                            result.add_issue(ValidationIssue(
                                severity=ValidationSeverity.WARNING,
                                category="delta",
                                path=f"timeline[{i}].account_state.{table}[{j}]",
                                message="Modified record should have _delta='updated'",
                                actual=delta,
                                expected="updated",
                            ))
                        
                        # Check _changed_fields if updated
                        if delta == "updated":
                            changed_fields = record.get("_changed_fields", [])
                            if not changed_fields:
                                result.add_issue(ValidationIssue(
                                    severity=ValidationSeverity.INFO,
                                    category="delta",
                                    path=f"timeline[{i}].account_state.{table}[{j}]",
                                    message="Updated record should specify _changed_fields",
                                    suggestion="Add _changed_fields array listing which fields changed",
                                ))
    
    def _record_has_changes(self, prev: Dict, curr: Dict) -> bool:
        """Check if a record has meaningful changes (ignoring delta fields)."""
        skip_fields = {"_delta", "_changed_fields"}
        
        for key, value in curr.items():
            if key in skip_fields:
                continue
            if key not in prev or prev[key] != value:
                return True
        
        return False
    
    
    def _validate_referential_integrity(self, scenario: Dict, result: ValidationResult):
        """Validate cross-references between records."""
        timeline = scenario.get("timeline", [])
        
        for i, frame in enumerate(timeline):
            state = frame.get("account_state", {})
            
            claims = state.get("claims", [])
            remits = state.get("remits", [])
            
            claim_numbers = {c.get("claim_number") for c in claims}
            
            # Check remit.claim_reference points to valid claim
            for j, remit in enumerate(remits):
                claim_ref = remit.get("claim_reference")
                if claim_ref and claim_ref not in claim_numbers:
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="referential",
                        path=f"timeline[{i}].account_state.remits[{j}].claim_reference",
                        message="Remit references non-existent claim",
                        actual=claim_ref,
                        expected=f"One of: {claim_numbers}",
                    ))
    
    
    def _validate_content_quality(self, scenario: Dict, result: ValidationResult):
        """Validate content quality and realism."""
        timeline = scenario.get("timeline", [])
        denial_code = scenario.get("scenario_metadata", {}).get("denial_code")
        
        for i, frame in enumerate(timeline):
            state = frame.get("account_state", {})
            event = frame.get("event", {})
            notes = state.get("notes", [])
            
            # Check event description is substantive
            description = event.get("description", "")
            if len(description) < 20:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="content",
                    path=f"timeline[{i}].event.description",
                    message="Event description should be more detailed",
                    actual=f"{len(description)} characters",
                    suggestion="Provide a detailed description of what happened",
                ))
            
            # Check state_summary is present and substantive
            summary = frame.get("state_summary", "")
            if len(summary) < 30:
                result.add_issue(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="content",
                    path=f"timeline[{i}].state_summary",
                    message="State summary should be more detailed",
                    suggestion="Summarize the current account state including balance, status, and next steps",
                ))
            
            # Check notes content
            for j, note in enumerate(notes):
                content = note.get("content", "")
                if len(content) < 20:
                    result.add_issue(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="content",
                        path=f"timeline[{i}].account_state.notes[{j}].content",
                        message="Note content should be more detailed",
                        suggestion="Notes should document the action taken and relevant details",
                    ))
                
                # Check that action notes mention the denial code
                if note.get("note_type") == "action" and denial_code:
                    if denial_code not in content:
                        result.add_issue(ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            category="content",
                            path=f"timeline[{i}].account_state.notes[{j}].content",
                            message="Action note should reference the denial code being addressed",
                            suggestion=f"Consider mentioning {denial_code} in the note",
                        ))

    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string is a valid YYYY-MM-DD date."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            return False
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse a datetime string (ISO8601)."""
        try:
            # Handle various ISO8601 formats
            for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    return datetime.strptime(dt_str.replace("Z", ""), fmt.replace("Z", ""))
                except ValueError:
                    continue
            return None
        except (ValueError, TypeError):
            return None


def validate_scenario(scenario: Dict, strict: bool = False) -> ValidationResult:
    """
    Quick validation function.
    
    Args:
        scenario: The scenario dict to validate
        strict: If True, treat warnings as errors
        
    Returns:
        ValidationResult
    """
    validator = ScenarioValidator(strict_mode=strict)
    return validator.validate(scenario)


def validate_scenario_json(json_str: str, strict: bool = False) -> ValidationResult:
    """
    Validate a scenario from JSON string.
    
    Args:
        json_str: JSON string of the scenario
        strict: If True, treat warnings as errors
        
    Returns:
        ValidationResult
    """
    try:
        scenario = json.loads(json_str)
    except json.JSONDecodeError as e:
        result = ValidationResult(is_valid=False)
        result.add_issue(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category="schema",
            path="",
            message=f"Invalid JSON: {str(e)}",
        ))
        return result
    
    return validate_scenario(scenario, strict=strict)


def get_validation_summary(result: ValidationResult) -> str:
    """Get a human-readable validation summary."""
    lines = [result.summary(), ""]
    
    if result.errors:
        lines.append("ERRORS:")
        for error in result.errors:
            lines.append(f"  ❌ [{error.category}] {error.path}: {error.message}")
            if error.suggestion:
                lines.append(f"     💡 {error.suggestion}")
    
    if result.warnings:
        lines.append("\nWARNINGS:")
        for warning in result.warnings:
            lines.append(f"  ⚠️  [{warning.category}] {warning.path}: {warning.message}")
    
    return "\n".join(lines)
