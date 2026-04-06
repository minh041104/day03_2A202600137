from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class MockProvider(LLMProvider):
    """
    Mock LLM Provider for testing without API calls.
    Returns predefined responses for testing ReAct agent.
    """
    def __init__(self, model_name: str = "mock-llm"):
        super().__init__(model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        # Simple mock responses for testing
        if "Observation:" in prompt:
            # After tool execution, provide final answer
            response = """Thought: Tôi đã kiểm tra availability và có thông tin. Bây giờ tôi sẽ trả lời khách.

Final Answer: Có giờ trống lúc 18:00, 19:00 và 20:00. Anh/chị muốn chọn giờ nào?"""
        elif "đặt bàn" in prompt.lower() or "booking" in prompt.lower():
            response = """Thought: Người dùng muốn đặt bàn. Tôi cần kiểm tra availability trước.

Action: get_available_slots(branch_id="1", date="2024-01-01", party_size=4)"""
        elif "bàn trống" in prompt.lower() or "available" in prompt.lower():
            response = """Thought: Người dùng hỏi về bàn trống. Tôi sẽ kiểm tra slots available.

Action: get_available_slots(branch_id="1", date="2024-01-01", party_size=2)"""
        else:
            response = """Thought: Tôi cần hiểu rõ hơn yêu cầu của người dùng.

Final Answer: Xin chào! Tôi có thể giúp bạn đặt bàn nhà hàng. Bạn muốn đặt bàn cho bao nhiêu người và vào thời gian nào?"""

        return {
            "content": response,
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "finish_reason": "stop"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Mock streaming - just yield the full response"""
        response = self.generate(prompt, system_prompt)["content"]
        yield response