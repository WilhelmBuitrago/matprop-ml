# agent_policy_ollama/src/api/v1/service.py
import ollama
from .scheme import (
    IntentionRequest,
    PlanStep,
    ExecutionPlan,
    PolicyOutputError,
    CompletionRequest,
)
import json
from jsonschema import validate as jsonschema_validate
from jsonschema.exceptions import ValidationError as JSONSchemaError
import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, List
import requests
import time
import numpy as np
import threading

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


_OLLAMA_MODEL_LOCK = threading.Lock()
_DEFAULT_KEEP_ALIVE = "0s"


def resolve_keep_alive() -> str:
    raw = os.getenv("AGENTS_OLLAMA_KEEP_ALIVE", _DEFAULT_KEEP_ALIVE).strip()
    return raw if raw else _DEFAULT_KEEP_ALIVE


def _ollama_chat_with_runtime(*, model: str, messages: List[Dict[str, Any]], **kwargs):
    keep_alive = resolve_keep_alive()
    start = time.perf_counter()
    logger.info(
        "[ollama-runtime] waiting_lock model=%s keep_alive=%s",
        model,
        keep_alive,
    )
    with _OLLAMA_MODEL_LOCK:
        logger.info(
            "[ollama-runtime] lock_acquired model=%s keep_alive=%s",
            model,
            keep_alive,
        )
        response = ollama.chat(
            model=model,
            messages=messages,
            keep_alive=keep_alive,
            **kwargs,
        )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "[ollama-runtime] lock_released model=%s elapsed_ms=%s keep_alive=%s",
        model,
        elapsed_ms,
        keep_alive,
    )
    return response


@dataclass
class ExecutionPlan:
    steps: List[PlanStep]


class LoadModelsService:
    def __init__(
        self,
        names: list = None,
    ):
        if names is None:
            self.names = [
                "yasserrmd/Qwen2.5-7B-Instruct-1M",
                "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M",
                "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M",
            ]
        else:
            self.names = names

    def download_models(self):
        installed_models = []
        max_retries = 5
        for i in range(max_retries):
            try:
                # ollama.list() devuelve un dict con una lista de modelos
                response = ollama.list()
                # Creamos un set con los nombres para buscar rápido
                installed_models = {m["name"] for m in response.get("models", [])}
                break
            except Exception:
                time.sleep(2)

        # 2. Iterar solo sobre los modelos necesarios
        for model_name in self.names:
            # Normalizamos nombres (a veces Ollama guarda 'model:latest' aunque pidas 'model')
            # Si el nombre exacto ya está en la lista, saltamos
            if model_name in installed_models:
                logger.info(f"✅ Modelo ya existe (omitido): {model_name}")
                continue

            # Si no está, entonces sí descargamos
            logger.info(f"⬇️ El modelo no existe, descargando: {model_name}...")
            try:
                ollama.pull(model_name)
                logger.info(f"✅ Descarga completada: {model_name}")
            except Exception as e:
                logger.info(f"❌ Error descargando modelo {model_name}: {e}")


class ChatService:
    def __init__(self, name: str = "WilhelmBuitrago/llamat-3-chat-8b:Q5_K_M"):
        self.name = name

    def chat(self, request: CompletionRequest) -> Dict[str, Any]:
        options = {
            "temperature": (
                request.temperature if request.temperature is not None else 0.7
            ),
            "num_predict": (
                request.max_tokens if request.max_tokens is not None else 512
            ),
        }
        try:
            logger.info(f"menssages: {request.history}")
            response = _ollama_chat_with_runtime(
                model=self.name,
                messages=request.history,
                options=options,
            )
            logger.info(f"Chat model response: {response['message']['content']}")
            return response["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Chat model invocation failed: {e}") from e


class CifService:
    def __init__(self, name: str = "WilhelmBuitrago/llamat-3-cif-8b:Q5_K_M"):
        self.name = name

    def get_cif(self, compound_name: str, max_tokens: int = 512) -> str:
        prompt = f"Provide the CIF file content for the compound: {compound_name}. Only return the CIF content without any additional text."
        messages = [{"role": "user", "content": prompt}]
        options = {
            "temperature": 0.0,
            "num_predict": max_tokens,
        }
        try:
            response = _ollama_chat_with_runtime(
                model=self.name,
                messages=messages,
                options=options,
            )
            return response["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"CIF retrieval failed: {e}") from e


class PlanningService:
    def __init__(self):
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are a PLANNING POLICY MODEL specialized in materials science.\n"
                "Your task is to decompose the user request into an ordered sequence of function calls.\n"
                "\n"
                "PLANNING RULES:\n"
                "- You MAY call ONE OR MORE functions.\n"
                "- Each function call represents a single execution step.\n"
                "- The order of function calls matters.\n"
                "- You MUST ONLY use the provided tools.\n"
                "- You MUST NOT answer the user in natural language.\n"
                "- You MUST NOT include explanations or reasoning text.\n"
                "- You MUST output ONLY function calls.\n"
                "- You MUST use argument names exactly as defined in the tool schema.\n"
                "- You MUST use enum values exactly as written.\n"
                "- If a parameter accepts an array, group related requests into one call.\n"
                "\n"
                "DECOMPOSITION RULES:\n"
                "- If the request contains multiple intents, decompose them into multiple steps.\n"
                "- If a step requires explanation, reasoning, or natural language output, you MUST include delegate_to_reasoner as a step.\n"
                "- Structured actions (search, prediction, retrieval) MUST appear before explanatory steps.\n"
                "\n"
                "DOMAIN CONSTRAINT:\n"
                "- All planning decisions must be within materials science and materials engineering.\n"
                "\n"
                "OUTPUT CONSTRAINT:\n"
                "- The output MUST consist ONLY of valid tool calls.\n"
                "- Any text outside tool calls is an error.\n"
            ),
        }

    def feedback(self, error_code: str) -> dict:
        feedback_mapping = {
            "NO_TOOL_CALLS": "The plan did not include any tool calls. YOu MUST ensure at least one tool is used.",
            "TOOL_NOT_FOUND": "One or more tools in the plan are not recognized.",
            "INVALID_ARGUMENTS": "The arguments provided for a tool are invalid or do not conform to the expected schema.",
            "MISSING_ARGUMENTS": "Required arguments for a tool are missing in the plan.",
            "EXCEEDED_STEP_LIMIT": "The number of steps in the plan exceeds the allowed limit.",
            "GENERAL_PLANNING_ERROR": "An unspecified error occurred during the planning process.",
            "EMPTY_PLAN": "The generated plan is empty. You MUST include at least one tool call.",
            "INVALID_SCHEMA": "One or more tool calls do not conform to the required schema.",
        }
        return {
            "role": "user",
            "content": feedback_mapping.get(error_code, "Unknown error code."),
        }

    def plan(self, payload: IntentionRequest, attempts: int = 5) -> ExecutionPlan:
        self.name = payload.model_name
        try:
            response = requests.get(
                f"http://agent-core:8004/v1/health",
                timeout=20,
            )
            if response.status_code != 200:
                raise PolicyOutputError("Error checking tool service health.")

            response = requests.get(
                f"http://agent-core:8004/v1/tools",
                headers={"content-type": "application/json"},
                timeout=20,
            )
            tools_response = response.json()["tools"]
        except Exception as e:
            raise PolicyOutputError(f"Failed to retrieve available tools: {e}") from e

        allowed_tool_names = {tool["function"]["name"] for tool in tools_response}

        self.schemas = {tool["function"]["name"]: tool for tool in tools_response}
        options = {
            "temperature": 0.0,
            "num_predict": payload.max_tokens,
        }

        messages = [
            self.system_prompt,
            {"role": "user", "content": payload.prompt},
        ]

        try:
            response = _ollama_chat_with_runtime(
                model=self.name,
                messages=messages,
                tools=tools_response,
                options=options,
            )
            tool_calls = response["message"].get("tool_calls")
        except Exception as e:
            raise PolicyOutputError(f"Planner model invocation failed: {e}") from e

        steps: List[PlanStep] = []
        if tool_calls:
            for call in tool_calls:
                name = call.function.name
                arguments = call.function.arguments

                steps.append(
                    PlanStep(
                        tool=name,
                        arguments=arguments,
                    )
                )
        else:
            raise PolicyOutputError("NO_TOOL_CALLS")

        steps = self._parse_steps(steps)
        logger.info(f"Parsed steps: {steps}")

        if not steps:
            raise PolicyOutputError("EMPTY_PLAN")

        return ExecutionPlan(steps=steps)

    def is_valid(self, instance: dict, schema: dict) -> bool:
        try:
            jsonschema_validate(instance=instance, schema=schema)
            return True
        except JSONSchemaError:
            return False

    def _parse_steps(self, steps: List[PlanStep]) -> List[PlanStep]:
        logger.info(f"Validating steps: {steps}")
        system = {
            "role": "system",
            "content": (
                "You are a JSON ARGUMENT COMPILER.\n\n"
                "TASK:\n"
                "- Transform the provided arguments so they STRICTLY match the given JSON Schema.\n\n"
                "RULES:\n"
                "- Do NOT change semantic intent.\n"
                "- Do NOT invent values.\n"
                "- Do NOT remove required fields.\n"
                "- Do NOT add new fields.\n"
                "- Normalize ONLY keys, structure, and enum values.\n"
                "- Enum normalization is allowed ONLY via case-insensitive and separator normalization.\n"
                "- If a value cannot be mapped unambiguously, FAIL.\n\n"
                "OUTPUT:\n"
                "- Output ONLY valid JSON matching the schema.\n"
                "- No explanations. No extra text."
            ),
        }
        for _ in range(3):
            parsed_steps: List[PlanStep] = []
            valids = []
            for step in steps:
                tool_name = step.tool
                raw_arguments = step.arguments
                schema = self.schemas.get(tool_name)

                if schema is None:
                    raise PolicyOutputError(f"TOOL_NOT_FOUND: {tool_name}")

                if self.is_valid(
                    instance=raw_arguments, schema=schema["function"]["parameters"]
                ):
                    parsed_steps.append(
                        PlanStep(tool=tool_name, arguments=raw_arguments)
                    )
                    valids.append(True)
                    continue

                user_message = {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "tool": tool_name,
                            "arguments": raw_arguments,
                            "schema": schema,
                        }
                    ),
                }

                response = _ollama_chat_with_runtime(
                    model=self.name,
                    messages=[system, user_message],
                    options={"temperature": 0.2, "num_predict": 256},
                    format="json",
                )

                try:
                    compiled_arguments = json.loads(response["message"]["content"])
                except Exception as e:
                    break

                try:
                    jsonschema_validate(
                        instance=compiled_arguments.get("arguments", {}),
                        schema=schema["function"]["parameters"],
                    )
                except JSONSchemaError as e:
                    break

                parsed_steps.append(
                    PlanStep(
                        tool=compiled_arguments.get("tool", tool_name),
                        arguments=compiled_arguments.get("arguments", {}),
                    )
                )
                valids.append(True)

            if all(valids) and len(valids) == len(steps):
                break
        logger.info(f"Validated steps: {parsed_steps}")

        if not parsed_steps:
            raise PolicyOutputError("EMPTY_PLAN")

        if parsed_steps[-1].tool != "delegate_to_reasoner":
            parsed_steps.append(
                PlanStep(
                    tool="delegate_to_reasoner",
                    arguments={},
                )
            )

        return parsed_steps

    def get_info(self):
        return {"Name": "IntentionService", "Model": self.name, "Version": "1.0.0"}


class InfoService:
    def __init__(self):
        pass

    def get_info(self):
        payload = {}
        payload["service"] = "agent_policy_ollama"
        planning = PlanningService().get_info()
        payload[planning["Name"]] = {k: v for k, v in planning.items() if k != "Name"}
        payload["policy_version"] = "1.0.0"
        return payload
