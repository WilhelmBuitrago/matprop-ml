from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.v3.state import AgentState, BudgetState, MaterialRecord


pytestmark = [pytest.mark.real_endpoints, pytest.mark.integration_docker]


def _has_mp_api_key() -> bool:
    env_value = os.getenv("MP_API_KEY", "").strip()
    if env_value:
        return True

    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return False

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "MP_API_KEY" and value.strip().strip('"').strip("'"):
            return True
    return False


def _material_rows_to_state(rows: list[dict]) -> AgentState:
    state = AgentState(
        request_id="real-tools-state",
        query="validate constraints",
        intent="constraint_validation",
        budget=BudgetState(),
    )
    for row in rows:
        state.materials_found.append(
            MaterialRecord(
                material_id=str(row["material_id"]),
                formula=str(row["formula"]),
                properties={
                    "band_gap": row["band_gap"],
                    "density": row["density"],
                    "is_stable": row["is_stable"],
                    "is_metal": row["is_metal"],
                    "energy_above_hull": row["energy_above_hull"],
                    "formation_energy": row["formation_energy"],
                    "volume": row["volume"],
                },
            )
        )
    return state


def test_query_materials_real(require_real_services, report_extra):
    report_extra(
        suite="tools",
        tool="query_materials_database",
        case_name="query_materials_real",
    )

    if not _has_mp_api_key():
        pytest.skip("MP_API_KEY is required for real query_materials validation")

    from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool

    tool = QueryMaterialsDatabaseTool()
    first = tool.execute(formula="Si", limit=5)
    assert first.status == "success", f"query_materials failed: {first.error_detail}"
    assert first.payload["count"] >= 1

    first_ids = [row["material_id"] for row in first.payload["materials"]]

    second = tool.execute(formula="Si", limit=5)
    assert second.status == "success", f"query_materials failed: {second.error_detail}"
    second_ids = [row["material_id"] for row in second.payload["materials"]]

    assert (
        first_ids == second_ids
    ), "Ranking/order should be deterministic for same input"
    report_extra(observed=f"count={first.payload['count']}", expected="count>=1")


def test_validate_constraints_real(require_real_services, report_extra):
    report_extra(
        suite="tools",
        tool="validate_material_constraints",
        case_name="validate_constraints_real",
    )

    if not _has_mp_api_key():
        pytest.skip("MP_API_KEY is required for validate_constraints real validation")

    from tools.catalog.query_materials.tool import QueryMaterialsDatabaseTool
    from tools.catalog.validate_material_constraints.tool import (
        ValidateMaterialConstraintsTool,
    )

    query_tool = QueryMaterialsDatabaseTool()
    query_result = query_tool.execute(formula="Si", limit=3)
    assert query_result.status == "success", query_result.error_detail
    assert query_result.payload["count"] >= 1

    state = _material_rows_to_state(query_result.payload["materials"])
    constraints = {
        "band_gap": [0.0, 4.0],
        "is_metal": False,
    }
    state.constraints = constraints

    tool = ValidateMaterialConstraintsTool()
    result = tool.execute(constraints=constraints, agent_state=state)

    assert result.status == "success", f"validate failed: {result.error_detail}"
    summary = result.payload["summary"]
    assert summary["total_materials"] == len(state.materials_found)
    assert (
        summary["passing_count"] + summary["failing_count"]
        == summary["total_materials"]
    )


def test_search_scientific_documents_real(require_real_services, report_extra):
    report_extra(
        suite="tools",
        tool="search_scientific_documents",
        case_name="search_scientific_documents_real",
    )

    from tools.catalog.search_scientific_documents.tool import (
        SearchScientificDocumentsTool,
    )

    tool = SearchScientificDocumentsTool(use_embeddings=True)
    result = tool.execute(
        query="silicon semiconductor band gap literature",
        providers=["arxiv", "semantic_scholar", "crossref"],
        max_results=8,
    )

    assert (
        result.status == "success"
    ), f"search_scientific_documents failed: {result.error_code} {result.error_detail}"
    assert result.payload["count"] >= 1

    documents = result.payload["documents"]
    seen = set()
    allowed_sources = {"arxiv", "semantic_scholar", "crossref"}
    for doc in documents:
        key = (str(doc.get("document_id")), str(doc.get("title", "")).strip().lower())
        assert key not in seen, f"Duplicate document detected: {key}"
        seen.add(key)
        assert doc["source"] in allowed_sources


def test_document_rag_real(require_real_services, report_extra):
    report_extra(
        suite="tools",
        tool="document_rag",
        case_name="document_rag_real",
    )

    from tools.catalog.document_rag.tool import DocumentRAGTool
    from tools.catalog.search_scientific_documents.tool import (
        SearchScientificDocumentsTool,
    )

    search_tool = SearchScientificDocumentsTool(use_embeddings=False)
    search = search_tool.execute(
        query="silicon crystal structure arxiv",
        providers=["arxiv"],
        max_results=3,
    )
    assert search.status == "success", f"search pre-step failed: {search.error_detail}"
    assert search.payload["count"] >= 1

    docs = search.payload["documents"][:1]
    rag_tool = DocumentRAGTool()
    rag = rag_tool.execute(
        documents=docs,
        query="extract key crystal structure findings",
        top_k=2,
        max_documents=1,
        max_chunks_per_document=12,
    )

    assert (
        rag.status == "success"
    ), f"document_rag failed: {rag.error_code} {rag.error_detail}"
    assert rag.payload["results"], "document_rag should return at least one result"
    first = rag.payload["results"][0]
    assert "score" in first
    assert "extracted_info" in first


def test_generate_crystal_structure_real(require_real_services, report_extra):
    report_extra(
        suite="tools",
        tool="generate_crystal_structure",
        case_name="generate_crystal_structure_real",
    )

    pytest.importorskip("pymatgen")
    from tools.catalog.generate_structure.tool import GenerateCrystalStructureTool

    tool = GenerateCrystalStructureTool()
    result = tool.execute(
        query="Generate a silicon diamond cubic crystal structure in CIF format",
        format="cif",
        include_debug=False,
    )

    assert (
        result.status == "success"
    ), f"generate_structure failed: {result.error_code} {result.error_detail}"
    payload = result.payload
    assert "cif" in payload and isinstance(payload["cif"], str)
    assert "structure" in payload
    assert "validation" in payload
    assert payload["validation"]["is_valid"] is True
    assert "metadata" in payload
    assert payload["metadata"]["output_format"] == "cif"
