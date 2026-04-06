# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Bình Minh  
- **Student ID**: 2A202600137
- **Date**: 2026-04-06


---

## I. Technical Contribution (15 Points)

*Mô tả các phần việc bạn đã trực tiếp cấu hình hoặc đóng góp trong source code.*

- **Modules Implementated**: Là người chịu trách nhiệm chính thiết kế cấu trúc thư mục cốt lõi tại `src/agent/agent.py`. Xây dựng kiến trúc vòng lặp ReAct, bộ phân tích cú pháp (Parser), và cơ chế duy trì ngữ cảnh nhiều lượt (Multi-turn Context/History).
- **Code Highlights**:
 `Thought -> Action -> Observation` và đồng bộ hóa Serialization kết quả vào ngữ cảnh kế tiếp:
  ```python
  # Trích đoạn run() trong agent.py
  thought, action = self._parse_response(response_text)
  
  if action:
      tool_name, args = action
      observation = execute_tool(tool_name, args)

      # Serialization ép chuẩn format Action cho LLM học theo
      serialized_action = self._serialize_action_call(tool_name, args)
      current_prompt = (
          f"{current_prompt}\n"
          f"Thought: {thought}\n"
          f"Action: {serialized_action}\n"
          f"Observation: {observation}"
      )
  ```
- **Documentation (Kiến trúc Agent)**: 
  - Đã thiết lập quy trình vận hành Agent: (1) **Context Management**: tự động trích xuất thông tin khách cung cấp qua Regex (`_extract_booking_info`) và lưu vào `booking_context` (như `party_size`, `branch`) để duy trì ngữ cảnh hội thoại đa lượt không bị quên/hỏi vòng quanh; (2) **ReAct Loop Execution**: Triển khai while-loop (`max_steps`) vận hành cơ chế `Thought->Action->Observation` chờ đến khi sinh ra `Final Answer`.

---

## II. Debugging Case Study (10 Points)

*Phân tích 1 tình huống hoạt động không mong muốn mà bạn đã tìm thấy từ file log và cách khắc phục.*

- **Problem Description**: Xảy ra lỗi "Parser Error" do LLM sinh ra `Action` sai định dạng JSON/Python Dict kiểu như `Action: tool_name({"key": "value"})` thay vì `tool_name(key="value")`.
- **Log Source**: Trích xuất từ file `logs/2026-04-06.log`: 
  ```log
  2026-04-06 14:22:15,102 - INFO - AGENT_ERROR: {'step': 2, 'error': "Error parsing action 'check_table_options({\"branch_id\":\"1\", \"party_size\":4})': unhashable type: 'dict'"}
  ```
- **Diagnosis**: Bởi vì thông tin đầu vào đa dạng, LLM (đặc biệt là model local nhỏ) đôi lúc gặp ảo giác (hallucination) trong cấu trúc dữ liệu. Do bộ Pattern Regex ban đầu `(\w+)\s*\((.*)\)` không bắt được cú pháp dấu ngoặc nhọn `{}` phức tạp, khiến hệ thống không trích xuất được args -> Vòng lặp ReAct chạy hoài mà không thực thi được Tool.
- **Solution**: Mình đã can thiệp thiết kế hai giải pháp trong `agent.py`:
  1. Viết hàm `_serialize_action_call`: Ép định dạng ngược lại thành chuẩn param=value (ví dụ `key="value"`) trước khi cập nhật chuỗi lên `current_prompt`. Điều này giúp mô hình "nhìn" thấy 1 ví dụ đúng chuẩn ở vòng lặp kế tiếp.
  2. Xây dựng khối lệnh bắt ngoại lệ (Graceful Degradation) ở phần phân loại Action: Nếu `action` không có, Agent tự động cập nhật lịch sử, không gắt gao crash ứng dụng (raise Error) mà nhảy qua vòng suy nghĩ kế tiếp.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Phản biện và đúc kết trải nghiệm cá nhân sau khi xây dựng Agent.*

1. **Reasoning (Khả năng suy luận)**: Lối suy nghĩ tuần tự `Thought -> Action -> Observation` mô phỏng cách làm việc của 1 tư vấn viên thực tế. Thay vì đoán mò trực tiếp từ prompt, LLM tự lý luận: "Mình chưa có thông tin chi nhánh -> Mình phải hỏi chi nhánh trước khi tra cứu giờ". Cơ chế Thought này tạo ra `Final Answer` mang tính thuyết phục tuyệt đối.
2. **Reliability (Độ tin cậy)**: Việc chủ động duy trì History và nhồi ngược thông tin trích xuất vào `<System Prompt>` giúp Agent giải quyết triệt để lỗi quên thông tin ở các hội thoại multi-turn dài, làm cho bot trở nên siêu tin cậy trong tác vụ thu thập form đặt bàn.
3. **Observation (Từ môi trường)**: Nhờ có bước phản hồi Tool Call (Observation), Agent chuyển hóa từ trạng thái chỉ "nói dựa trên xác suất chữ" sang nắm giữ dữ liệu cứng (hard data) từ Database nội bộ. Qua đây, mình nhận ra vai trò của mình (lập trình viên backend) chuyển qua tập trung làm sao để Parse/Serialize data gọn gàng nhất giữa LLM và Database.

---

## IV. Future Improvements (5 Points)

*Làm thế nào để ứng dụng AI Agent này hoạt động tốt hơn nếu nó được công ty triển khai thực tế?*

- **Performance**: Nâng cấp Parser thành hệ thống xử lý Native Function/Tool Calling (JSON Schema của OpenAI hoặc Gemini API) thay vì lệ thuộc vào Regex tự xây. Giải quyết dứt điểm các rủi ro liên quan tới Parser error.
- **Scalability**: Chuyển module `booking_context` và `history` sang dùng bộ nhớ Redis Cache hoặc Graph Database để lưu Memory của khách hàng. Hiện tại context bị lưu trong Local Dict của Class `ReActAgent` nên sẽ mất dữ liệu khi restart app.
- **Safety**: Xây dựng Guardrails Validator trước hàm `_extract_booking_info` để chống Prompt Injection, đồng thời kiểm tra xác thực số điện thoại chuẩn Việt Nam (+84) trước khi Agent ra quyết định (Decision Making).
