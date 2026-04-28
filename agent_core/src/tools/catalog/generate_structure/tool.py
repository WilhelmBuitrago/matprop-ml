from __future__ import annotations

from dataclasses import asdict
import logging
from typing import TYPE_CHECKING, Any

from services.agents_client.crystal_client import AgentsCrystalClient
from tools.base import ToolContract, ToolResult

from .parser import DeterministicCrystalParser, missing_critical_fields
from .post_processor import PostProcessor
from .prompt_builder import CrystalPromptBuilder
from .prompt_config import CRYSTAL_PROMPT_CONFIG_V1
from .schema import CrystalSpec
from .validator import PyMatgenValidator
from .cif_generator import structure_to_cif, structure_to_poscar

if TYPE_CHECKING:
    from api.v4.state import AgentState


logger = logging.getLogger(__name__)


class GenerateCrystalStructureTool(ToolContract):
    """Generate physically plausible crystal structures from natural language constraints."""

    name = "generate_crystal_structure"
    description = (
        "Generate, validate, and serialize crystal structures as CIF/POSCAR/JSON."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 4},
            "format": {"type": "string", "enum": ["cif", "poscar", "json"]},
            "generation_mode": {
                "type": "string",
                "enum": [
                    "conditional",
                    "infill",
                    "formula_compute",
                    "element_generation",
                    "unconditional",
                ],
            },
            "include_debug": {"type": "boolean"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "cif": {"type": "string"},
            "structure": {
                "type": "object",
                "properties": {
                    "lattice": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"},
                            "c": {"type": "number"},
                            "alpha": {"type": "number"},
                            "beta": {"type": "number"},
                            "gamma": {"type": "number"},
                        },
                        "required": ["a", "b", "c", "alpha", "beta", "gamma"],
                        "additionalProperties": False,
                    },
                    "atoms": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "element": {"type": "string"},
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "z": {"type": "number"},
                            },
                            "required": ["element", "x", "y", "z"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["lattice", "atoms"],
                "additionalProperties": False,
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "formula": {"type": ["string", "null"]},
                    "space_group": {"type": ["string", "null"]},
                    "generation_mode": {"type": "string"},
                    "output_format": {"type": "string"},
                },
                "required": [
                    "formula",
                    "space_group",
                    "generation_mode",
                    "output_format",
                ],
                "additionalProperties": False,
            },
            "validation": {
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["is_valid", "errors", "warnings"],
                "additionalProperties": False,
            },
            "source": {"type": "string", "enum": ["llm"]},
            "confidence_signals": {
                "type": "object",
                "properties": {
                    "structure_consistency": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "low_entropy": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["structure_consistency", "low_entropy"],
                "additionalProperties": False,
            },
            "debug": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "raw_output": {"type": "string"},
                },
                "required": ["prompt", "raw_output"],
                "additionalProperties": False,
            },
        },
        "required": ["cif", "structure", "metadata", "validation"],
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self._parser = DeterministicCrystalParser()
        self._prompt_builder = CrystalPromptBuilder()
        self._post_processor = PostProcessor()
        self._validator = PyMatgenValidator()
        self._client = AgentsCrystalClient()

    def preconditions(self, state: "AgentState"):
        del state
        return True, ""

    def execute(self, **kwargs: Any) -> ToolResult:
        query = str(kwargs.get("query", "")).strip()
        logger.info("generate_structure execute start query_len=%d", len(query))
        if not query:
            logger.warning("generate_structure validation_error empty_query")
            return ToolResult(
                status="error",
                payload={},
                error_code="VALIDATION_ERROR",
                error_detail="query is required",
                source="llm",
                is_synthetic=True,
                trace="generate_crystal_structure:empty_query",
            )

        output_format = str(kwargs.get("format", "cif")).lower()
        include_debug = bool(kwargs.get("include_debug", False))
        preferred_mode = kwargs.get("generation_mode")
        logger.info(
            "generate_structure options format=%s include_debug=%s preferred_mode=%s",
            output_format,
            include_debug,
            preferred_mode,
        )

        try:
            deterministic_spec = self._parser.parse(query)
            logger.info(
                "generate_structure deterministic_spec formula=%s lattice=%s space_group=%s elements=%d",
                deterministic_spec.formula,
                deterministic_spec.lattice_type,
                deterministic_spec.space_group,
                len(deterministic_spec.elements),
            )
            merged = {
                "formula": deterministic_spec.formula,
                "lattice_type": deterministic_spec.lattice_type,
                "space_group": deterministic_spec.space_group,
                "elements": deterministic_spec.elements,
                "constraints": deterministic_spec.constraints,
            }

            if missing_critical_fields(deterministic_spec):
                logger.info(
                    "generate_structure missing critical fields, calling extract_spec"
                )
                extracted = self._client.extract_spec(
                    query=query,
                    deterministic_spec=merged,
                ).get("spec", {})
                merged = self._merge_spec(merged, extracted)
                logger.info(
                    "generate_structure merged_spec keys=%s", sorted(merged.keys())
                )

            crystal_spec = CrystalSpec.build(
                formula=self._pick_str(merged.get("formula")),
                lattice_type=self._pick_str(merged.get("lattice_type")),
                space_group=self._pick_str(merged.get("space_group")),
                elements=self._pick_elements(merged.get("elements")),
                constraints=self._pick_constraints(merged.get("constraints")),
                preferred_mode=self._pick_str(preferred_mode),
            )
            logger.info(
                "generate_structure crystal_spec mode=%s formula=%s space_group=%s elements=%d",
                crystal_spec.generation_mode.value,
                crystal_spec.formula,
                crystal_spec.space_group,
                len(crystal_spec.elements),
            )

            prompt_bundle = self._prompt_builder.build(
                spec=crystal_spec,
                config=CRYSTAL_PROMPT_CONFIG_V1,
            )
            logger.info(
                "generate_structure prompt built user_prompt_len=%d",
                len(prompt_bundle.user_prompt),
            )

            generation = self._client.generate(
                system_message=prompt_bundle.system_message,
                user_prompt=prompt_bundle.user_prompt,
                temperature=self._config.get("models.cif.temperature", 0.3),  # Use centralized config
                max_tokens=self._config.get("models.cif.max_tokens", 900),  # Use centralized config
                stop_tokens=["\n\n", "# end"],
                model_name="WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M",
            )
            raw_output = str(generation.get("raw_generation", "")).strip()
            logger.info(
                "generate_structure generation received raw_len=%d",
                len(raw_output),
            )

            parsed = self._post_processor.parse(raw_output)
            logger.info(
                "generate_structure parsed atoms=%d",
                len(parsed.atoms),
            )
            validation = self._validator.validate(parsed)
            if not validation.is_valid:
                logger.warning(
                    "generate_structure validation_failed errors=%s warnings=%s",
                    validation.errors,
                    validation.warnings,
                )
                return ToolResult(
                    status="error",
                    payload={
                        "validation": {
                            "is_valid": validation.is_valid,
                            "errors": validation.errors,
                            "warnings": validation.warnings,
                        }
                    },
                    error_code="VALIDATION_ERROR",
                    error_detail="generated structure did not pass validation",
                    source="llm",
                    is_synthetic=True,
                    trace="generate_crystal_structure:validation_failed",
                )

            cif_text = structure_to_cif(parsed.structure)
            payload = {
                "cif": cif_text,
                "structure": {
                    "lattice": parsed.lattice,
                    "atoms": [asdict(site) for site in parsed.atoms],
                },
                "metadata": {
                    "formula": crystal_spec.formula,
                    "space_group": crystal_spec.space_group,
                    "generation_mode": crystal_spec.generation_mode.value,
                    "output_format": output_format,
                },
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                },
            }

            if include_debug:
                payload["debug"] = {
                    "prompt": prompt_bundle.user_prompt,
                    "raw_output": raw_output,
                }

            if output_format == "poscar":
                payload["cif"] = structure_to_poscar(parsed.structure)
            elif output_format == "json":
                payload["cif"] = ""

            atom_count = len(parsed.atoms)
            warning_count = len(validation.warnings)
            errors_count = len(validation.errors)
            structure_consistency = 1.0 if validation.is_valid else 0.4
            low_entropy = 1.0 if atom_count > 0 else 0.5
            payload["source"] = "llm"
            payload["confidence_signals"] = {
                "structure_consistency": structure_consistency,
                "low_entropy": low_entropy,
            }

            logger.info(
                "generate_structure success output_format=%s warnings=%d",
                output_format,
                len(validation.warnings),
            )
            return ToolResult(
                status="success",
                payload=payload,
                source="llm",
                is_synthetic=True,
                trace=(
                    f"formula={crystal_spec.formula or 'unknown'};"
                    f"atoms={atom_count};warnings={warning_count};errors={errors_count}"
                ),
                confidence_signals={
                    "structure_consistency": structure_consistency,
                    "low_entropy": low_entropy,
                },
            )

        except ValueError as exc:
            logger.warning("generate_structure parsing_error=%s", exc)
            return ToolResult(
                status="error",
                payload={},
                error_code="PARSING_ERROR",
                error_detail=str(exc),
                source="llm",
                is_synthetic=True,
                trace="generate_crystal_structure:parsing_error",
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("generate_structure unexpected_error")
            return ToolResult(
                status="error",
                payload={},
                error_code="GENERATION_ERROR",
                error_detail=str(exc),
                source="llm",
                is_synthetic=True,
                trace="generate_crystal_structure:unexpected_error",
            )

    @staticmethod
    def _merge_spec(
        deterministic_spec: dict[str, Any],
        llm_spec: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(deterministic_spec)
        for key in (
            "formula",
            "lattice_type",
            "space_group",
            "elements",
            "constraints",
        ):
            if merged.get(key):
                continue
            value = llm_spec.get(key)
            if value:
                merged[key] = value
        return merged

    @staticmethod
    def _pick_str(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _pick_elements(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @staticmethod
    def _pick_constraints(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}
