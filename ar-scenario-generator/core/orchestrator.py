from typing import Dict, Literal, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import random

from .validator import ScenarioValidator, ValidationResult
from .prompts import (
    get_system_prompt,
    get_generation_prompt,
    get_repair_prompt,
    get_few_shot_examples
)


# Easy enum for generation status types
class GenerationStatus(Enum):
    SUCCESS = "success"
    VALIDATION_FAILED = "validation_failed"
    REPAIR_FAILED = "repair_failed"
    LLM_ERROR = "llm_error"
    PARSE_ERROR = "parse_error"


# Data class to capture generation results into a convenient data obj
@dataclass
class GenerationResult:
    """Result of a single scenario generation attempt."""
    status: GenerationStatus
    scenario: Optional[Dict] = None
    validation_result: Optional[ValidationResult] = None
    attempts: int = 1
    repair_attempts: int = 0
    generation_time_ms: int = 0
    error_message: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == GenerationStatus.SUCCESS
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "is_success": self.is_success,
            "attempts": self.attempts,
            "repair_attempts": self.repair_attempts,
            "generation_time_ms": self.generation_time_ms,
            "error_message": self.error_message,
            "validation_summary": self.validation_result.summary() if self.validation_result else None,
        }


# Generation config class that can be passed into a scenario orchestrator
@dataclass
class GenerationConfig:
    """Configuration for scenario generation."""
    # Validation settings
    strict_validation: bool = False
    max_repair_attempts: int = 2
    
    # Generation settings
    include_few_shot: bool = True
    few_shot_count: int = 1
    include_full_schemas: bool = True
    
    # Diversity settings
    randomize_payer: bool = True
    randomize_complexity: bool = True
    
    # Output settings
    include_validation_metadata: bool = False


# Type alias for LLM call function
LLMCallFn = Callable[[str, str], str]  # (system_prompt, user_prompt) -> response


class ScenarioOrchestrator:
    """
    Orchestrates LLM-guided scenario generation with validation.
    
    Usage:
        ```
        # Define your LLM client
        def call_llm(system_prompt: str, user_prompt: str) -> str:
            # Your LLM API call here
            return response_text
        
        orchestrator = ScenarioOrchestrator(llm_client=call_llm)
        result = orchestrator.generate_scenario(denial_code="CO-16")
        
        if result.is_success:
            scenario = result.scenario
        ```
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMCallFn] = None,
        config: Optional[GenerationConfig] = None,
    ):
        """Initialize the orchestrator."""
        self.llm_client = llm_client
        self.config = config or GenerationConfig()
        self.validator = ScenarioValidator(strict_mode=self.config.strict_validation)
    
    def _mock_llm_client(self, system_prompt: str, user_prompt: str) -> str:
        """Mock LLM client for testing - returns a simple valid scenario."""
        # This is just for testing without an actual LLM
        from .prompts import FEW_SHOT_EXAMPLES
        return json.dumps(FEW_SHOT_EXAMPLES[0])
    
    def generate_scenario(
        self,
        denial_code: str,
        complexity: Optional[Literal["simple", "moderate", "complex"]] = None,
        service_type: Literal["outpatient", "inpatient"] = "outpatient",
        additional_instructions: str = "",
    ) -> GenerationResult:
        """Generate a single scenario."""
        start_time = datetime.now()
        
        # Randomize complexity if its not defined
        if self.config.randomize_complexity and not complexity:
            complexity = random.choice(["simple", "moderate", "complex"])
        else:
            complexity = complexity or "moderate"
        
        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_generation_prompt(
            denial_code=denial_code,
            complexity=complexity,
            service_type=service_type,
            additional_instructions=additional_instructions,
        )
        
        # Call LLM and capture output or error
        try:
            response = self.llm_client(system_prompt, user_prompt)

        except Exception as e:
            return GenerationResult(
                status=GenerationStatus.LLM_ERROR,
                error_message=str(e),
                generation_time_ms=self._elapsed_ms(start_time),
            )
        
        # Parse response
        scenario, parse_error = self._parse_response(response)
        if parse_error:
            return GenerationResult(
                status=GenerationStatus.PARSE_ERROR,
                error_message=parse_error,
                generation_time_ms=self._elapsed_ms(start_time),
            )
        
        # Validate
        validation_result = self.validator.validate(scenario)
        
        if validation_result.is_valid:
            return GenerationResult(
                status=GenerationStatus.SUCCESS,
                scenario=scenario,
                validation_result=validation_result,
                generation_time_ms=self._elapsed_ms(start_time),
            )
        
        # Attempt repair if validation failed
        if self.config.max_repair_attempts > 0:
            repair_result = self._attempt_repair(
                scenario=scenario,
                validation_result=validation_result,
                start_time=start_time,
            )
            return repair_result
        
        return GenerationResult(
            status=GenerationStatus.VALIDATION_FAILED,
            scenario=scenario,
            validation_result=validation_result,
            generation_time_ms=self._elapsed_ms(start_time),
        )
    
    def validate_scenario(self, scenario: Dict) -> ValidationResult:
        """
        Validate an externally-generated scenario.
        
        Args:
            scenario: The scenario dict to validate
            
        Returns:
            ValidationResult
        """
        return self.validator.validate(scenario)
    
    def repair_scenario(
        self,
        scenario: Dict,
        validation_result: Optional[ValidationResult] = None,
    ) -> GenerationResult:
        """
        Attempt to repair a scenario with validation errors.
        
        Args:
            scenario: The scenario to repair
            validation_result: Pre-computed validation result (will compute if None)
            
        Returns:
            GenerationResult with repaired scenario
        """
        if validation_result is None:
            validation_result = self.validator.validate(scenario)
        
        if validation_result.is_valid:
            return GenerationResult(
                status=GenerationStatus.SUCCESS,
                scenario=scenario,
                validation_result=validation_result,
            )
        
        start_time = datetime.now()
        return self._attempt_repair(
            scenario=scenario,
            validation_result=validation_result,
            start_time=start_time,
        )
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with optional schemas and examples."""
        parts = [get_system_prompt(include_schemas=self.config.include_full_schemas)]
        
        if self.config.include_few_shot:
            examples = get_few_shot_examples(count=self.config.few_shot_count)
            if examples:
                parts.append("\n\n## EXAMPLES\nHere are examples of correctly formatted scenarios:\n")
                for i, example in enumerate(examples, 1):
                    parts.append(f"\n### Example {i}\n```json\n{json.dumps(example, indent=2)}\n```\n")
        
        return "".join(parts)
    
    def _build_generation_prompt(
        self,
        denial_code: str,
        complexity: str,
        service_type: str,
        additional_instructions: str,
    ) -> str:
        """Build the generation prompt with seed parameters."""
        return get_generation_prompt(
            denial_code=denial_code,
            complexity=complexity,
            service_type=service_type,
            additional_instructions=additional_instructions,
        )
    
    def _parse_response(self, response: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Parse LLM response to extract JSON scenario."""
        # Try to extract JSON from response first
        response = response.strip()
        
        # Handle markdown code blocks by remove backticks and json tag
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                response = response[start:end].strip()
        
        try:
            scenario = json.loads(response)
            return scenario, None
        except json.JSONDecodeError as e:
            return None, f"JSON parse error: {str(e)}"
    
    def _attempt_repair(
        self,
        scenario: Dict,
        validation_result: ValidationResult,
        start_time: datetime,
    ) -> GenerationResult:
        """Attempt to repair a scenario using the LLM."""
        for attempt in range(self.config.max_repair_attempts):
            # Build repair prompt
            system_prompt = get_system_prompt(include_schemas=True)
            user_prompt = get_repair_prompt(
                scenario=scenario,
                validation_errors=[e.to_dict() for e in validation_result.errors],
            )
            
            # Call LLM for repair
            try:
                response = self.llm_client(system_prompt, user_prompt)
            except Exception as e:
                continue  # Try again
            
            # Parse repaired scenario
            repaired, parse_error = self._parse_response(response)
            if parse_error:
                continue
            
            # Validate repaired scenario
            new_validation = self.validator.validate(repaired)
            
            if new_validation.is_valid:
                return GenerationResult(
                    status=GenerationStatus.SUCCESS,
                    scenario=repaired,
                    validation_result=new_validation,
                    repair_attempts=attempt + 1,
                    generation_time_ms=self._elapsed_ms(start_time),
                )
            
            # Update for next attempt
            scenario = repaired
            validation_result = new_validation
        
        return GenerationResult(
            status=GenerationStatus.REPAIR_FAILED,
            scenario=scenario,
            validation_result=validation_result,
            repair_attempts=self.config.max_repair_attempts,
            generation_time_ms=self._elapsed_ms(start_time),
            error_message=f"Repair failed after {self.config.max_repair_attempts} attempts",
        )
    
    def _elapsed_ms(self, start_time: datetime) -> int:
        """Calculate elapsed milliseconds since start time."""
        return int((datetime.now() - start_time).total_seconds() * 1000)
    
    def export_validation_rules(self) -> Dict:
        """Export validation rules in a structured format."""
        from .schemas import (
            LOGICAL_CONSTRAINTS,
            ACTION_DEFINITIONS,
            ASYNC_EVENT_DEFINITIONS,
        )
        
        return {
            "logical_constraints": LOGICAL_CONSTRAINTS,
            "action_definitions": ACTION_DEFINITIONS,
            "async_event_definitions": ASYNC_EVENT_DEFINITIONS,
        }
