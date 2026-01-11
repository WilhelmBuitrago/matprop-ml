# agent_core/tools/config.py
AVAILABLES_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_materials",
            "description": "Search for materials in the database based on various criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "object",
                        "description": "Search criteria for materials (e.g., material_id, formula, chemsys)",
                        "properties": {
                            "material": {
                                "oneOf": [
                                    {
                                        "type": "string",
                                        "pattern": "^(mp|mvc)-\\d+$",
                                        "description": "Materials Project ID (mp-XXXX)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^\\d+$",
                                        "description": "Numeric material ID (will be mapped to mp-XXXX)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^[A-Z][a-z]?(-[A-Z][a-z]?)+$",
                                        "description": "Chemical system (e.g. Fe-O)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^[A-Z][a-z]?\\d*([A-Z][a-z]?\\d*)*$",
                                        "description": "Chemical formula (e.g. Fe2O3)",
                                    },
                                ],
                                "description": "Material identifier, formula, chemical system, or unique number to search for",
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional filters to refine the search results",
                                "properties": {
                                    "band_gap": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"},
                                        },
                                        "description": "Filter materials by band gap float range",
                                        "required": ["min", "max"],
                                        "additionalProperties": False,
                                    },
                                    "energy_above_hull": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"},
                                        },
                                        "description": "Filter materials by energy above hull float range",
                                        "required": ["min", "max"],
                                        "additionalProperties": False,
                                    },
                                    "formation_energy_per_atom": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"},
                                        },
                                        "description": "Filter materials by formation energy per atom float range",
                                        "required": ["min", "max"],
                                        "additionalProperties": False,
                                    },
                                    "density": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"},
                                        },
                                        "description": "Filter materials by density float range",
                                        "required": ["min", "max"],
                                        "additionalProperties": False,
                                    },
                                    "volume": {
                                        "type": "object",
                                        "properties": {
                                            "min": {"type": "number"},
                                            "max": {"type": "number"},
                                        },
                                        "description": "Filter materials by volume float range",
                                        "required": ["min", "max"],
                                        "additionalProperties": False,
                                    },
                                    "is_stable": {
                                        "type": "boolean",
                                        "description": "Filter materials by stability (true for stable materials, false for unstable)",
                                        "additionalProperties": False,
                                    },
                                    "is_metal": {
                                        "type": "boolean",
                                        "description": "Filter materials by metallicity (true for metals, false for non-metals)",
                                        "additionalProperties": False,
                                    },
                                    "crystal_system": {
                                        "type": "string",
                                        "enum": [
                                            "cubic",
                                            "tetragonal",
                                            "orthorhombic",
                                            "hexagonal",
                                            "trigonal",
                                            "monoclinic",
                                            "triclinic",
                                        ],
                                        "description": "Filter materials by crystal system (e.g., 'cubic', 'tet', etc.)",
                                        "additionalProperties": False,
                                    },
                                    "spacegroup_number": {
                                        "type": "integer",
                                        "description": "Filter materials by spacegroup number",
                                        "additionalProperties": False,
                                    },
                                    "nsites": {
                                        "type": "integer",
                                        "description": "Filter materials by number of sites",
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            "additionalProperties": False,
                        },
                        "required": ["material"],
                        "additionalProperties": False,
                    },
                },
                "required": ["query"],
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
                    "query": {
                        "type": "object",
                        "description": "Identifier for the material to retrieve properties for",
                        "properties": {
                            "material": {
                                "oneOf": [
                                    {
                                        "type": "string",
                                        "pattern": "^(mp|mvc)-\\d+$",
                                        "description": "Materials Project ID (mp-XXXX)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^\\d+$",
                                        "description": "Numeric material ID (will be mapped to mp-XXXX)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^[A-Z][a-z]?(-[A-Z][a-z]?)+$",
                                        "description": "Chemical system (e.g. Fe-O)",
                                    },
                                    {
                                        "type": "string",
                                        "pattern": "^[A-Z][a-z]?\\d*([A-Z][a-z]?\\d*)*$",
                                        "description": "Chemical formula (e.g. Fe2O3)",
                                    },
                                ],
                                "description": "Material identifier, formula, chemical system, or unique number to search for",
                            },
                        },
                        "required": ["material"],
                        "additionalProperties": False,
                    },
                    "propertys": {
                        "type:": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "formula_pretty",
                                "chemsys",
                                "crystal_system",
                                "spacegroup",
                                "density",
                                "volume",
                                "nsites",
                                "energy_above_hull",
                                "formation_energy_per_atom",
                                "is_stable",
                                "is_metal",
                                "band_gap",
                                "efermi",
                            ],
                        },
                    },
                },
                "required": ["query", "propertys"],
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
