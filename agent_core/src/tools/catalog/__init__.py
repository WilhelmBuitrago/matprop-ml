__all__ = [
    "QueryMaterialsDatabaseTool",
    "CompareMaterialsTool",
    "ValidateMaterialConstraintsTool",
    "SearchScientificDocumentsTool",
    "ExtractDocumentInsightsTool",
    "GenerateCrystalStructureTool",
]


def __getattr__(name: str):
    if name == "QueryMaterialsDatabaseTool":
        from .query_materials import QueryMaterialsDatabaseTool

        return QueryMaterialsDatabaseTool
    if name == "CompareMaterialsTool":
        from .compare_materials import CompareMaterialsTool

        return CompareMaterialsTool
    if name == "ValidateMaterialConstraintsTool":
        from .validate_material_constraints import ValidateMaterialConstraintsTool

        return ValidateMaterialConstraintsTool
    if name == "SearchScientificDocumentsTool":
        from .search_documents import SearchScientificDocumentsTool

        return SearchScientificDocumentsTool
    if name == "ExtractDocumentInsightsTool":
        from .extract_insights import ExtractDocumentInsightsTool

        return ExtractDocumentInsightsTool
    if name == "GenerateCrystalStructureTool":
        from .generate_structure import GenerateCrystalStructureTool

        return GenerateCrystalStructureTool
    raise AttributeError(f"module 'tools.catalog' has no attribute {name!r}")
