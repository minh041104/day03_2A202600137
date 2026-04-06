import os
import re
import json
import datetime
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.restaurant_tools_v2 import TOOLS, execute_tool

class ReActAgent:
    """
    Restaurant Booking Agent using ReAct pattern
    """

    def __init__(self, llm: LLMProvider, max_steps: int = 5):
        self.llm = llm
        self.max_steps = max_steps
        self.history = []
        # Booking context - what we know so far
        self.booking_context = {
            "party_size": None,
            "branch": None,
            "date": None,
            "time": None,
            "guest_name": None,
            "guest_phone": None
        }

    def get_system_prompt(self) -> str:
        """
        System prompt instructing the agent to follow ReAct for restaurant booking.
        Includes current booking context to avoid repeating questions.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in TOOLS])
        current_date = datetime.date.today().isoformat()
        
        # Build context string from collected info
        context_lines = []
        if self.booking_context["party_size"]:
            context_lines.append(f"- Số người: {self.booking_context['party_size']}")
        if self.booking_context["branch"]:
            context_lines.append(f"- Chi nhánh: {self.booking_context['branch']}")
        if self.booking_context["date"]:
            context_lines.append(f"- Ngày: {self.booking_context['date']}")
        if self.booking_context["time"]:
            context_lines.append(f"- Giờ: {self.booking_context['time']}")
        
        context_str = "\n".join(context_lines) if context_lines else "Chưa có thông tin nào"

        return f"""
Bạn là trợ lý đặt bàn nhà hàng. Nhiệm vụ: giúp khách đặt bàn chuyên nghiệp.

THÔNG TIN ĐÃ THU THẬP:
{context_str}

CÔNG CỤ SẴN CÓ:
{tool_descriptions}

QUY TẮC:
- Nhớ thông tin đã hỏi được, KHÔNG HỎI LẠI
- Nếu thiếu thông tin: HỎI KHÁCH (số người, chi nhánh, ngày, giờ)
- Chỉ dùng tool khi có đủ thông tin
- Ngày "tối nay" = {current_date}
- Chi nhánh: 1=B3 Central, 2=B3 Riverside, 3=B3 Landmark

ĐỊNH DẠNG PHẢI THEO ĐÚNG:
Thought: [suy nghĩ của bạn]
Action: tool_name(param1="value1", param2="value2")
Observation: [kết quả tool]
Final Answer: [trả lời tiếng Việt cho khách]
"""

    def run(self, user_input: str) -> str:
        """
        Main ReAct loop for restaurant booking.
        Maintains conversation history and booking context.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        # Extract booking info from user input
        self._extract_booking_info(user_input)
        
        # Store user input in history
        self.history.append({"role": "user", "content": user_input})

        current_prompt = user_input
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            try:
                # Generate LLM response
                result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
                
                # Extract content from response dict
                if isinstance(result, dict) and 'content' in result:
                    response_text = result['content']
                else:
                    response_text = str(result)

                # Parse Thought and Action
                thought, action = self._parse_response(response_text)

                if not action:
                    # No action found, might be final answer
                    if "Final Answer:" in response_text:
                        final_answer = response_text.split("Final Answer:")[-1].strip()
                        break
                    else:
                        # If the model didn't follow the required format, degrade gracefully:
                        # keep going a little, but don't end with a useless fallback message.
                        if steps >= 1:
                            final_answer = response_text.strip()
                            break

                        current_prompt = f"{current_prompt}\n{response_text}"
                        steps += 1
                        continue

                # Execute tool
                tool_name, args = action
                observation = execute_tool(tool_name, args)

                # Update prompt with observation
                # IMPORTANT: keep Action format consistent with the system prompt
                # (tool_name(param=value, ...)), not Python dict formatting.
                serialized_action = self._serialize_action_call(tool_name, args)
                current_prompt = (
                    f"{current_prompt}\n"
                    f"Thought: {thought}\n"
                    f"Action: {serialized_action}\n"
                    f"Observation: {observation}"
                )

                # If the model already produced a Final Answer in the same turn,
                # prefer returning only the user-facing part.
                if "Final Answer:" in response_text:
                    final_answer = response_text.split("Final Answer:")[-1].strip()
                    break

                steps += 1

            except Exception as e:
                logger.log_event("AGENT_ERROR", {"step": steps, "error": str(e)})
                return f"Xin lỗi, có lỗi xảy ra: {str(e)}"

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})

        if final_answer:
            result = self._format_final_answer(final_answer)
        else:
            result = "Xin lỗi, tôi không thể xử lý yêu cầu của bạn. Vui lòng thử lại."
        
        # Store agent response in history
        self.history.append({"role": "assistant", "content": result})
        
        return result

    def _extract_booking_info(self, text: str) -> None:
        """
        Extract booking information from user text and update booking_context.
        Looks for: party_size, branch, date, time
        """
        text_lower = text.lower()
        
        # Extract party size (số người, người)
        party_patterns = [
            r'(\d+)\s*người',
            r'cho\s*(\d+)',
        ]
        for pattern in party_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.booking_context["party_size"] = int(match.group(1))
                break
        
        # Extract branch
        branch_patterns = {
            "B3 Central": ["central", "trung tâm"],
            "B3 Riverside": ["riverside", "sông"],
            "B3 Landmark": ["landmark", "mốc"]
        }
        for branch, keywords in branch_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    self.booking_context["branch"] = branch
                    break
            if self.booking_context["branch"]:
                break
        
        # Extract time (18:00, 6h, 18h, etc.)
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # 18:00
            r'(\d{1,2})h',  # 6h, 18h
        ]
        for pattern in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if pattern == r'(\d{1,2}):(\d{2})':
                    self.booking_context["time"] = f"{match.group(1)}:{match.group(2)}"
                else:
                    hour = match.group(1)
                    self.booking_context["time"] = f"{hour}:00"
                break
        
        # Extract date
        date_patterns = {
            "today": ["tối nay", "hôm nay", "thôi"],
            "tomorrow": ["ngày mai", "mai"],
        }
        current_date = datetime.date.today()
        for date_type, keywords in date_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if date_type == "today":
                        self.booking_context["date"] = current_date.isoformat()
                    else:
                        self.booking_context["date"] = (current_date + datetime.timedelta(days=1)).isoformat()
                    break
            if self.booking_context["date"]:
                break

    def _parse_response(self, response: str) -> tuple:
        """
        Parse Thought and Action from LLM response.
        Supports multiple formats.
        Returns: (thought, (tool_name, args_dict)) or (thought, None)
        """
        lines = response.strip().split('\n')
        thought = ""
        action = None

        for line in lines:
            line = line.strip()
            if line.startswith("Thought:"):
                thought = line[8:].strip()
            elif line.startswith("Action:"):
                action_str = line[7:].strip()
                # Parse action: tool_name(parameters)
                # Support multiple formats: tool_name(key="value"), tool_name(key=value), etc.
                try:
                    # Extract tool name and parameters
                    match = re.match(r'(\w+)\s*\((.*)\)', action_str)
                    if match:
                        tool_name = match.group(1)
                        params_str = match.group(2).strip()

                        args = {}
                        if params_str:
                            # Parse parameters: key="value" or key=value
                            # Use regex to find key-value pairs
                            param_matches = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s)]+))', params_str)
                            for match in param_matches:
                                key = match[0]
                                # Value is the first non-empty group
                                value = match[1] or match[2] or match[3]
                                
                                # Convert to appropriate type
                                if value.isdigit():
                                    args[key] = int(value)
                                elif value.lower() in ['true', 'false']:
                                    args[key] = value.lower() == 'true'
                                else:
                                    args[key] = value

                        action = (tool_name, args)
                except Exception as e:
                    print(f"Error parsing action '{action_str}': {e}")
                    continue

        return thought, action

    def _serialize_action_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Serialize a tool call back into `tool_name(key="value", n=1)` format.
        This prevents the model from seeing Python dict formatting like `{...}`
        and thinking the Action syntax is invalid.
        """
        if not args:
            return f"{tool_name}()"

        def _serialize_value(v: Any) -> str:
            if isinstance(v, bool):
                return "true" if v else "false"
            if v is None:
                return "null"
            if isinstance(v, (int, float)):
                return str(v)
            # Strings: always double-quote, escape internal quotes/backslashes
            s = str(v).replace("\\", "\\\\").replace('"', '\\"')
            return f"\"{s}\""

        parts = [f"{k}={_serialize_value(args[k])}" for k in sorted(args.keys())]
        return f"{tool_name}({', '.join(parts)})"

    def _format_final_answer(self, answer: str) -> str:
        """
        Format the final answer for user.
        """
        try:
            # If it's JSON, parse and format nicely
            if answer.startswith('{'):
                data = json.loads(answer)
                if 'booking_id' in data or 'reservation_id' in data:
                    bid = data.get('booking_id') or data.get('reservation_id')
                    return f"✅ Đặt bàn thành công!\nMã đặt bàn: {bid}\nTrạng thái: {data.get('status', 'N/A')}"
                elif 'available_slots' in data:
                    slots = data['available_slots']
                    if slots:
                        return f"Khung giờ trống: {', '.join(slots)}"
                    else:
                        return "Không có khung giờ trống cho yêu cầu này."
                elif 'options' in data:
                    options = data['options']
                    if options:
                        formatted = "\n".join([f"- {opt['area']}: {opt['type']}" for opt in options])
                        return f"Lựa chọn bàn:\n{formatted}"
                    else:
                        return "Không có lựa chọn bàn phù hợp."
                elif 'deposit_required' in data:
                    return f"Số tiền cọc: {data['deposit_required']:,} {data['currency']}\nGhi chú: {data['note']}"
                else:
                    return str(data)
            else:
                return answer
        except:
            return answer
