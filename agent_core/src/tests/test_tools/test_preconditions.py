from api.v3.state import AgentState, BudgetState, MaterialRecord, DocumentRecord
from tools.config import TOOL_REGISTRY


def _state() -> AgentState:
    return AgentState(
        request_id="r-pre",
        query="test",
        intent="material_lookup",
        budget=BudgetState(),
    )


def test_document_rag_requires_documents():
    state = _state()
    assert TOOL_REGISTRY.can_run("document_rag", state) is False

    state.documents.append(
        DocumentRecord(title="paper", source="arXiv", relevance_score=0.9, abstract="a")
    )
    assert TOOL_REGISTRY.can_run("document_rag", state) is True


def test_constraints_tool_requires_constraints_and_materials():
    state = _state()
    assert TOOL_REGISTRY.can_run("validate_material_constraints", state) is False

    state.constraints = {"band_gap": [0.5, 2.0]}
    state.materials_found.append(
        MaterialRecord(material_id="mp-149", formula="Si", properties={})
    )
    assert TOOL_REGISTRY.can_run("validate_material_constraints", state) is True
