"""Prompt builder for deterministic + conditional crystal generation prompts."""

from __future__ import annotations

from dataclasses import dataclass

from .prompt_config import CrystalGenPromptConfig
from .schema import CrystalSpec


@dataclass(frozen=True)
class PromptBundle:
    system_message: str
    user_prompt: str


class CrystalPromptBuilder:
    """Builds semantically chunked prompts from CrystalSpec."""

    def build(
        self,
        spec: CrystalSpec,
        config: CrystalGenPromptConfig,
    ) -> PromptBundle:
        mode = spec.generation_mode.value
        system_message = config.SYSTEM_MESSAGES[mode]
        task_block = config.INPUT_TEMPLATES[mode]

        material_block = self._material_description_block(spec, config)
        constraints_block = config.CONSTRAINTS_BLOCK
        output_block = config.OUTPUT_FORMAT_BLOCK

        sections = [
            "[Task Instruction Block]",
            task_block,
            "",
            "[Material Description Block]",
            material_block,
            "",
            "[Constraints Block]",
            constraints_block,
            "",
            "[Output Format Block]",
            output_block,
        ]
        user_prompt = "\n".join(sections).strip()
        return PromptBundle(system_message=system_message, user_prompt=user_prompt)

    def _material_description_block(
        self,
        spec: CrystalSpec,
        config: CrystalGenPromptConfig,
    ) -> str:
        elements_text = ", ".join(spec.elements) if spec.elements else "not specified"

        if spec.has_lattice:
            return config.CONDITIONAL_TEMPLATES["lattice_atoms"].format(
                lattice_type=spec.lattice_type,
            )

        if spec.formula and spec.space_group:
            return config.CONDITIONAL_TEMPLATES["composition_spacegroup"].format(
                formula=spec.formula,
                space_group=spec.space_group,
            )

        if spec.formula:
            return config.CONDITIONAL_TEMPLATES["composition"].format(
                formula=spec.formula,
                elements=elements_text,
            )

        return config.CONDITIONAL_TEMPLATES["elements"].format(elements=elements_text)
