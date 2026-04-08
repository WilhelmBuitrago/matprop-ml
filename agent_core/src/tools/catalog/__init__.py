__all__ = [
    "QueryMaterialsDatabaseTool",
    "ValidateMaterialConstraintsTool",
    "SearchScientificDocumentsTool",
    "DocumentRAGTool",
    "GenerateCrystalStructureTool",
]


def __getattr__(name: str):
    if name == "QueryMaterialsDatabaseTool":
        from .query_materials import QueryMaterialsDatabaseTool

        return QueryMaterialsDatabaseTool
    if name == "ValidateMaterialConstraintsTool":
        from .validate_material_constraints import ValidateMaterialConstraintsTool

        return ValidateMaterialConstraintsTool
    if name == "SearchScientificDocumentsTool":
        from .search_scientific_documents import SearchScientificDocumentsTool

        return SearchScientificDocumentsTool
    if name == "DocumentRAGTool":
        from .document_rag import DocumentRAGTool

        return DocumentRAGTool
    if name == "GenerateCrystalStructureTool":
        from .generate_structure.tool import GenerateCrystalStructureTool

        return GenerateCrystalStructureTool
    raise AttributeError(f"module 'tools.catalog' has no attribute {name!r}")
