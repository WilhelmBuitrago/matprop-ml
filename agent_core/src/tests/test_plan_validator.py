from api.v4.contracts import Plan, PlanStep
from api.v4.plan_validator import (
    build_minimal_plan,
    is_plan_coherent,
    validate_step_input,
)


def test_plan_validator_accepts_coherent_plan():
    plan = Plan(
        steps=[
            PlanStep(
                tool="search_scientific_documents",
                target="Si",
                purpose="Collect papers",
            ),
            PlanStep(
                tool="document_rag",
                target=None,
                purpose="Extract evidence",
            ),
        ],
        cursor=0,
        status="active",
    )

    assert is_plan_coherent(
        plan,
        available_tools={"search_scientific_documents", "document_rag"},
    )


def test_plan_validator_rejects_too_many_steps():
    plan = Plan(
        steps=[
            PlanStep(tool=f"tool_{idx}", target=None, purpose=f"step {idx}")
            for idx in range(9)
        ],
        cursor=0,
        status="active",
    )

    assert (
        is_plan_coherent(plan, available_tools={f"tool_{idx}" for idx in range(9)})
        is False
    )


def test_plan_validator_rejects_document_rag_without_search():
    plan = Plan(
        steps=[
            PlanStep(tool="document_rag", target=None, purpose="Extract evidence"),
        ],
        cursor=0,
        status="active",
    )

    assert is_plan_coherent(plan, available_tools={"document_rag"}) is False


def test_build_minimal_plan_uses_first_available_tool():
    plan = build_minimal_plan(
        query="find stable Si",
        available_tools=[
            {"name": "query_materials_database"},
            {"name": "search_scientific_documents"},
        ],
    )

    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "query_materials_database"


def test_plan_validator_dependency_graph_requires_query_before_constraints():
    plan = Plan(
        steps=[
            PlanStep(
                tool="validate_material_constraints",
                target=None,
                purpose="Validate user constraints",
            ),
            PlanStep(
                tool="query_materials_database",
                target="mp-149",
                purpose="Fetch candidate",
            ),
        ],
        cursor=0,
        status="active",
    )

    assert (
        is_plan_coherent(
            plan,
            available_tools={
                "validate_material_constraints",
                "query_materials_database",
            },
        )
        is False
    )


def test_validate_step_input_rejects_wrong_shape_against_schema():
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 3},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    assert validate_step_input({"max_results": 5}, schema) is False
    assert validate_step_input({"query": "find Si", "max_results": 5}, schema) is True
