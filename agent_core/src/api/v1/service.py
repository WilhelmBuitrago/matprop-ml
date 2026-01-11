from .scheme import CompletionRequest, CompletionResponse
import requests
import hashlib
import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class CompletionService:
    def __init__(self):
        self.intention_api = "http://agents:8003/v1/intention"
        self.chat_api = "http://backend-llm:8001/v1/chat"
        self.tools = {}

    def chat(self, request: CompletionRequest) -> CompletionResponse:
        # Implement the logic to call the chat API and return the response
        # Step 1. Generate intention from the prompt
        try:
            payload = {
                "model_name": "kwangsuklee/Qwen2.5-7B-Instruct-1M-Q6_K",
                "prompt": request.prompt,
                "max_tokens": request.max_tokens_for_context,
            }
            steps = requests.post(
                self.intention_api,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            raise RuntimeError(f"Intention API error: {str(e)}")

        logger.info(f"Intention steps: {steps.json()}")
        #   Step 2.Execute the plan and generate context
        context = "No context available."
        """
        for step in steps:
            tool_name = step["tool"]
            arguments = step["arguments"]
            if tool_name not in self.tools.keys():
                raise RuntimeError(f"Tool {tool_name} not found")
            tool = self.tools[tool_name]
            tool_response = tool.execute(**arguments)
            context += f"\nTool: {tool_name}\nResponse: {tool_response}\n"
        """

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
            chat_response = requests.post(
                self.chat_api,
                json=chat_payload,
                headers={"Content-Type": "application/json"},
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
            choices=[{"text": response_text}],
            usage=usage,
        )

    def approximate_tokens(self, text: str) -> int:
        # Simple approximation: 1 token ~ 4 characters
        return len(text) // 4
