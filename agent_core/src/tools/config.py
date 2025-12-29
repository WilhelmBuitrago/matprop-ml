# agent_core/tools/config.py
AVAILABLES_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_materials_by_id",
            "description": "Search for materials using their unique identifiers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_ids": {
                        "oneOf": [
                            {
                                "type": "integer",
                                "description": "Single material unique identifier",
                            },
                            {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "List of material unique identifiers",
                            },
                        ]
                    }
                },
                "required": ["material_ids"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_materials_by_keyword",
            "description": "Search for materials using keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "Single keyword for material search",
                            },
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of keywords for material search",
                            },
                        ]
                    }
                },
                "required": ["keywords"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_materials_by_structure",
            "description": "Search for materials using structural information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "structure_data": {
                        "type": "object",
                        "properties": {
                            "format": {"enum": ["cif", "poscar"]},
                            "data": {"type": "string"},
                        },
                        "required": ["format", "data"],
                        "additionalProperties": False,
                    }
                },
                "required": ["structure_data"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_material_properties",
            "description": "Retrieve detailed properties of a specified material.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {
                        "type": "integer",
                        "description": "Unique identifier of the material",
                    },
                },
                "required": ["material_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_material_properties",
            "description": "Predict properties of a material based on its structure or composition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "structure_data": {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "format": {
                                        "type": "string",
                                        "enum": ["cif", "poscar"],
                                    },
                                    "data": {"type": "string"},
                                },
                                "required": ["format", "data"],
                                "additionalProperties": False,
                            },
                            {
                                "type": "integer",
                                "description": "Unique identifier of the material",
                            },
                            {
                                "type": "string",
                                "description": "Material name, formula or Chemical composition of the material",
                            },
                        ]
                    },
                    "property": {
                        "description": "Specific property or properties to predict (e.g., band gap, conductivity)",
                        "oneOf": [
                            {
                                "type": "string",
                                "enum": [
                                    "band_gap",
                                    "efermi",
                                ],
                                "description": "Single property to predict",
                            },
                            {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "band_gap",
                                        "efermi",
                                    ],
                                },
                                "description": "List of properties to predict",
                            },
                        ],
                    },
                },
                "required": ["structure_data", "property"],
                "additionalProperties": False,
            },
        },
    },
    # "optimize_material_structure": {},
    # "synthesize_material": {},
    # "analyze_material_performance": {},
    {
        "type": "function",
        "function": {
            "name": "visualize_material_structure",
            "description": "Generate a visual representation of the material's structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material": {
                        "type": "object",
                        "description": "Material structure data in a recognized format (e.g., CIF, POSCAR or ID)",
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "format": {
                                        "type": "string",
                                        "enum": ["cif", "poscar"],
                                    },
                                    "data": {"type": "string"},
                                },
                                "required": ["format", "data"],
                                "additionalProperties": False,
                            },
                            {
                                "type": "integer",
                                "description": "Unique identifier of the material",
                            },
                        ],
                    },
                    "visualization_type": {
                        "type": "string",
                        "description": "Type of visualization (e.g., 3D model, 2D projection)",
                    },
                },
                "required": ["material", "visualization_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_materials",
            "description": "Compare properties of multiple materials.",
            "parameters": {
                "type": "object",
                "properties": {
                    "materials": {
                        "type": "array",
                        "items": {
                            "oneOf": [
                                {"type": "integer"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "format": {
                                            "type": "string",
                                            "enum": ["cif", "poscar"],
                                        },
                                        "data": {"type": "string"},
                                    },
                                    "required": ["format", "data"],
                                    "additionalProperties": False,
                                },
                            ]
                        },
                        "description": "List of material structure data or unique identifiers to compare",
                    },
                    "properties": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "Single property to compare",
                            },
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of properties to compare",
                            },
                        ]
                    },
                },
                "required": ["materials", "properties"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_material_report",
            "description": "Generate a comprehensive report on a specified material.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material": {
                        "type": "integer",
                        "description": "Material structure data in a recognized format (e.g., CIF, POSCAR) or unique identifier",
                        "oneOf": [
                            {
                                "type": "integer",
                                "description": "Unique identifier of the material",
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "format": {
                                        "type": "string",
                                        "enum": ["cif", "poscar"],
                                    },
                                    "data": {"type": "string"},
                                },
                                "required": ["format", "data"],
                                "additionalProperties": False,
                            },
                        ],
                    },
                    "report_type": {
                        "type": "string",
                        "description": "Type of report to generate (e.g., summary, detailed analysis)",
                    },
                },
                "required": ["material", "report_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documentation_by_topic",
            "description": "Search for documentation using specific topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topics": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "Single topic for documentation search",
                            },
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of topics for documentation search",
                            },
                        ]
                    }
                },
                "required": ["topics"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documentation_by_keyword",
            "description": "Search for documentation using keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "oneOf": [
                            {
                                "type": "string",
                                "description": "Single keyword for documentation search",
                            },
                            {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of keywords for documentation search",
                            },
                        ]
                    }
                },
                "required": ["keywords"],
                "additionalProperties": False,
            },
        },
    },
    # "get_documentation_summary": {},
    # "generate_documentation_report": {},
    {
        "type": "function",
        "function": {
            "name": "delegate_to_reasoner",
            "description": "Use this function when the user asks for explanations, definitions, descriptions, conceptual overviews, comparisons, opinions, or general questions such as 'what is', 'explain', 'how does', or 'tell me about'.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
