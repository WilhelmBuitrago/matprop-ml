import logging

import pytest

from tools.catalog.generate_structure.parser import PartialCrystalSpec
from tools.catalog.generate_structure.post_processor import AtomSite, ParsedStructure
from tools.catalog.generate_structure.prompt_builder import PromptBundle
from tools.catalog.generate_structure.tool import GenerateCrystalStructureTool
from tools.catalog.generate_structure.validator import ValidationResult


pytestmark = pytest.mark.integration_docker


class _FakePromptBuilder:
    def __init__(self):
        self.last_spec = None

    def build(self, spec, config):
        del config
        self.last_spec = spec
        return PromptBundle(
            system_message="system-message",
            user_prompt="user-prompt-with-constraints",
        )


class _FakeCrystalClient:
    def __init__(self, extracted_spec=None, generation=None):
        self.extracted_spec = extracted_spec or {}
        self.generation = generation or {"raw_generation": "data_test"}
        self.extract_calls = 0
        self.generate_calls = 0

    def extract_spec(self, query: str, deterministic_spec: dict):
        del query, deterministic_spec
        self.extract_calls += 1
        return {"spec": self.extracted_spec}

    def generate(self, **kwargs):
        del kwargs
        self.generate_calls += 1
        return self.generation


class _FakePostProcessor:
    def __init__(self, parsed: ParsedStructure | Exception):
        self._parsed = parsed

    def parse(self, raw_output: str):
        del raw_output
        if isinstance(self._parsed, Exception):
            raise self._parsed
        return self._parsed


class _FakeValidator:
    def __init__(self, result: ValidationResult):
        self._result = result

    def validate(self, parsed):
        del parsed
        return self._result


def _parsed_structure() -> ParsedStructure:
    return ParsedStructure(
        lattice={
            "a": 4.12,
            "b": 4.12,
            "c": 9.51,
            "alpha": 90.0,
            "beta": 90.0,
            "gamma": 120.0,
        },
        atoms=[
            AtomSite(element="Bi", x=0.0, y=0.0, z=0.0),
            AtomSite(element="Se", x=0.333, y=0.667, z=0.25),
        ],
        structure=object(),
    )


def test_preconditions_always_pass(docker_env_for_tools, tool_test_logger):
    del docker_env_for_tools
    tool = GenerateCrystalStructureTool()

    ok, reason = tool.preconditions(state=object())
    tool_test_logger.info("generate_structure preconditions validated")

    assert ok is True
    assert reason == ""


def test_execute_returns_validation_error_when_query_missing(
    docker_env_for_tools,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)
    tool = GenerateCrystalStructureTool()

    tool_test_logger.info("generate_structure validating empty query")
    result = tool.execute(query="  ")

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert result.error_detail == "query is required"
    assert "generate_structure validating empty query" in caplog.text


def test_execute_success_with_poscar_and_debug_payload(
    docker_env_for_tools,
    monkeypatch,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    tool = GenerateCrystalStructureTool()
    tool._parser.parse = lambda query: PartialCrystalSpec(
        formula="Bi2Se3",
        lattice_type="hexagonal",
        space_group="R-3m",
        elements=["Bi", "Se"],
        constraints={},
    )
    tool._prompt_builder = _FakePromptBuilder()
    tool._client = _FakeCrystalClient(generation={"raw_generation": "data_bi2se3"})
    tool._post_processor = _FakePostProcessor(parsed=_parsed_structure())
    tool._validator = _FakeValidator(
        ValidationResult(is_valid=True, errors=[], warnings=["short_distance:Bi-Se"])
    )

    monkeypatch.setattr(
        "tools.catalog.generate_structure.tool.structure_to_cif",
        lambda structure: "CIF_TEXT",
    )
    monkeypatch.setattr(
        "tools.catalog.generate_structure.tool.structure_to_poscar",
        lambda structure: "POSCAR_TEXT",
    )

    tool_test_logger.info("generate_structure executing success path for poscar output")
    result = tool.execute(
        query="Generate Bi2Se3 in R-3m",
        format="poscar",
        generation_mode="conditional",
        include_debug=True,
    )

    assert result.status == "success"
    assert result.payload["cif"] == "POSCAR_TEXT"
    assert result.payload["metadata"]["formula"] == "Bi2Se3"
    assert result.payload["metadata"]["output_format"] == "poscar"
    assert result.payload["metadata"]["generation_mode"] == "conditional"
    assert result.payload["validation"]["is_valid"] is True
    assert result.payload["debug"]["prompt"] == "user-prompt-with-constraints"
    assert result.payload["debug"]["raw_output"] == "data_bi2se3"
    assert "generate_structure executing success path for poscar output" in caplog.text


def test_execute_uses_extracted_spec_when_critical_fields_missing(
    docker_env_for_tools,
    monkeypatch,
    caplog,
    tool_test_logger,
):
    del docker_env_for_tools
    caplog.set_level(logging.INFO)

    prompt_builder = _FakePromptBuilder()
    client = _FakeCrystalClient(
        extracted_spec={
            "formula": "GaN",
            "space_group": "P63mc",
            "elements": ["Ga", "N"],
            "constraints": {"compute_only": False},
        },
        generation={"raw_generation": "data_gan"},
    )

    tool = GenerateCrystalStructureTool()
    tool._parser.parse = lambda query: PartialCrystalSpec(
        formula=None,
        lattice_type=None,
        space_group=None,
        elements=[],
        constraints={},
    )
    tool._prompt_builder = prompt_builder
    tool._client = client
    tool._post_processor = _FakePostProcessor(parsed=_parsed_structure())
    tool._validator = _FakeValidator(
        ValidationResult(is_valid=True, errors=[], warnings=[])
    )

    monkeypatch.setattr(
        "tools.catalog.generate_structure.tool.structure_to_cif",
        lambda structure: "CIF_FROM_EXTRACTED_SPEC",
    )

    tool_test_logger.info("generate_structure executing extracted-spec merge path")
    result = tool.execute(query="Generate nitride crystal with Ga and N", format="cif")

    assert result.status == "success"
    assert client.extract_calls == 1
    assert client.generate_calls == 1
    assert prompt_builder.last_spec is not None
    assert prompt_builder.last_spec.formula == "GaN"
    assert sorted(prompt_builder.last_spec.elements) == ["Ga", "N"]
    assert result.payload["metadata"]["formula"] == "GaN"
    assert result.payload["cif"] == "CIF_FROM_EXTRACTED_SPEC"
    assert "generate_structure executing extracted-spec merge path" in caplog.text


def test_execute_returns_validation_error_when_generated_structure_is_invalid(
    docker_env_for_tools,
    monkeypatch,
):
    del docker_env_for_tools

    tool = GenerateCrystalStructureTool()
    tool._parser.parse = lambda query: PartialCrystalSpec(formula="Si", elements=["Si"])
    tool._prompt_builder = _FakePromptBuilder()
    tool._client = _FakeCrystalClient(generation={"raw_generation": "data_invalid"})
    tool._post_processor = _FakePostProcessor(parsed=_parsed_structure())
    tool._validator = _FakeValidator(
        ValidationResult(
            is_valid=False,
            errors=["severe_overlap:Si-Si"],
            warnings=["short_distance:Si-Si"],
        )
    )

    monkeypatch.setattr(
        "tools.catalog.generate_structure.tool.structure_to_cif",
        lambda structure: "UNUSED",
    )

    result = tool.execute(query="Generate Si crystal")

    assert result.status == "error"
    assert result.error_code == "VALIDATION_ERROR"
    assert result.error_detail == "generated structure did not pass validation"
    assert result.payload["validation"]["is_valid"] is False
    assert result.payload["validation"]["errors"] == ["severe_overlap:Si-Si"]


def test_execute_maps_value_error_to_parsing_error(docker_env_for_tools):
    del docker_env_for_tools

    tool = GenerateCrystalStructureTool()
    tool._parser.parse = lambda query: PartialCrystalSpec(formula="Si", elements=["Si"])
    tool._prompt_builder = _FakePromptBuilder()
    tool._client = _FakeCrystalClient(generation={"raw_generation": "bad-cif"})
    tool._post_processor = _FakePostProcessor(parsed=ValueError("cif_header_not_found"))

    result = tool.execute(query="Generate Si crystal")

    assert result.status == "error"
    assert result.error_code == "PARSING_ERROR"
    assert result.error_detail == "cif_header_not_found"


def test_execute_maps_unexpected_error_to_generation_error(docker_env_for_tools):
    del docker_env_for_tools

    tool = GenerateCrystalStructureTool()
    tool._parser.parse = lambda query: PartialCrystalSpec(formula="Si", elements=["Si"])
    tool._prompt_builder = _FakePromptBuilder()
    tool._client = _FakeCrystalClient(generation={"raw_generation": "data"})
    tool._post_processor = _FakePostProcessor(parsed=_parsed_structure())

    def _raise_unexpected(parsed):
        del parsed
        raise RuntimeError("validator_internal_failure")

    tool._validator.validate = _raise_unexpected

    result = tool.execute(query="Generate Si crystal")

    assert result.status == "error"
    assert result.error_code == "GENERATION_ERROR"
    assert result.error_detail == "validator_internal_failure"
