from .scheme import CompletionRequest, CompletionResponse
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from tools.tools import SearchMaterialsTool, GetMaterialPropertiesTool
import requests
import hashlib
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class CompletionService:
    def __init__(self):
        self.intention_api = "http://agents:8003/v1/intention"
        self.chat_api = "http://backend-llm:8001/v1/chat"
        self.timeout_seconds = 20
        self.tools = {
            "search_materials": SearchMaterialsTool(),
            "get_material_properties": GetMaterialPropertiesTool(),
            "delegate_to_reasoner": None,
        }
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.http = requests.Session()
        self.http.mount("http://", adapter)
        self.http.mount("https://", adapter)

    def chat(self, request: CompletionRequest) -> CompletionResponse:
        # Implement the logic to call the chat API and return the response
        # Step 1. Generate intention from the prompt
        try:
            payload = {
                "model_name": "kwangsuklee/Qwen2.5-7B-Instruct-1M-Q6_K",
                "prompt": request.prompt,
                "max_tokens": request.max_tokens_for_context,
            }
            steps = self.http.post(
                self.intention_api,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )
            logger.info(f"Intention API response: {steps}")
            steps = steps.json()
        except Exception as e:
            raise RuntimeError(f"Intention API error: {str(e)}")

        context = ""
        parsed_steps = steps.get("steps", []) if isinstance(steps, dict) else []
        if not parsed_steps:
            raise RuntimeError("Intention API returned an empty or invalid plan")

        for step in parsed_steps:
            logger.info(f"Executing step: {step}")
            if not isinstance(step, dict):
                raise RuntimeError(f"Invalid plan step type: {type(step).__name__}")

            tool_name = step.get("tool")
            arguments = step.get("arguments", {})
            if not tool_name:
                raise RuntimeError(f"Plan step is missing 'tool': {step}")
            if tool_name not in self.tools.keys():
                raise RuntimeError(f"Tool {tool_name} not found")
            if tool_name == "delegate_to_reasoner":
                break
            tool = self.tools[tool_name]
            tool_response = tool.execute(**arguments)
            context += f"\nTool: {tool_name}\nResponse: {tool_response}\n"
            logger.info(f"Generated context: {context}")

        # Step 3. Generate final response using chat API
        try:
            chat_payload = {
                "messages": [
                    {"role": "system", "content": context},
                    {"role": "user", "content": request.prompt},
                ],
                # "temperature": request.temperature,
                # "max_tokens": request.max_tokens_for_response,
            }
            chat_response = self.http.post(
                self.chat_api,
                json=chat_payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_seconds,
            )

            response_text = chat_response.json().get("response", "")
        except Exception as e:
            raise RuntimeError(f"Chat API error: {str(e)}")

        logger.info(f"Chat API response: {chat_response}")
        logger.info(f"Final response text: {response_text}")

        # approximate tokens for context
        context_tokens = self.approximate_tokens(context)
        # approximate tokens for response
        response_tokens = self.approximate_tokens(response_text)
        # approximate input tokens
        input_tokens = self.approximate_tokens(request.prompt)
        usage = {
            "prompt_tokens": input_tokens + context_tokens,
            "context_tokens": context_tokens,
            "completion_tokens": response_tokens,
            "total_tokens": input_tokens + context_tokens + response_tokens,
        }

        return CompletionResponse(
            id=hashlib.md5(request.prompt.encode()).hexdigest(),
            object="text_completion",
            choices=[
                {
                    "text": response_text,
                }
            ],
            usage=usage,
        )

    def approximate_tokens(self, text: str) -> int:
        # Simple approximation: 1 token ~ 4 characters
        return len(text) // 4
