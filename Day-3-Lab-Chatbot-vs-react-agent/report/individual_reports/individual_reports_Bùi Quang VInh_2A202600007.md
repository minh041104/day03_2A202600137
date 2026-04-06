# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Bùi Quang Vinh
- **Student ID**: 2A202600007
- **Date**: 2026-04-06

---

## I. Technical Contribution

Phần tôi phụ trách trong dự án là **Tooling v1**, tập trung vào việc thiết kế lớp công cụ ban đầu cho agent đặt bàn nhà hàng và xây dựng contract đầu vào/đầu ra để agent có thể tương tác với dữ liệu nghiệp vụ thay vì chỉ trả lời bằng ngôn ngữ tự nhiên.

- **Modules Implementated**:
  - [restaurant_tools.py]
- **Code Highlights**:
  - Hàm `get_available_slots()` tại [restaurant_tools.py] là tool lõi để kiểm tra availability theo `branch_id`, `date`, `party_size`.
  - Hàm `check_table_options()` tại [restaurant_tools.py] xử lý truy vấn loại bàn dựa trên `reservation_time` dạng ISO.
  - Hàm `calculate_deposit_amount()` tại [restaurant_tools.py] ánh xạ số khách và trạng thái VIP sang chính sách cọc trong sheet `DepositPolicies`.
  - Hàm `create_reservation()` tại [restaurant_tools.py] là thiết kế ban đầu cho thao tác ghi booking, dù ở v1 mới dừng ở mức trả về thành công mô phỏng.
  - Danh sách `TOOLS` tại [restaurant_tools.py:229] đóng vai trò là contract chính thức để agent đọc và quyết định action.
- **Documentation**:
  - Tooling v1 đóng vai trò cầu nối giữa agent và dữ liệu nhà hàng. Trong vòng lặp ReAct, agent sinh `Action`, sau đó `execute_tool(...)` tại [restaurant_tools.py] ánh xạ tên tool sang hàm Python tương ứng, rồi trả `Observation` dưới dạng JSON string về cho agent suy luận tiếp.
  - Giá trị lớn nhất của Tooling v1 là tạo ra khung rõ ràng gồm 5 bước: kiểm tra giờ trống, kiểm tra loại bàn, tính cọc, tạo đặt bàn và gửi xác nhận. Nhờ đó, agent có thể xử lý một quy trình đặt bàn trọn vẹn thay vì chỉ hội thoại.

Đánh giá phần đóng góp:

- Tooling v1 giúp xác định rõ các công việc của agent.
- Các hàm được tách độc lập, dễ gọi và dễ kiểm thử thủ công.
- Tuy nhiên, qua quá trình chạy thật, v1 cũng bộc lộ các hạn chế về độ thân thiện với LLM, từ đó dẫn đến việc nâng cấp lên `restaurant_tools_v2.py`.

---

## II. Debugging Case Study

- **Problem Description**:
  - Trong các trace đầu tiên, agent thường gọi tool sai tên tham số, ví dụ dùng `guests`, `people`, `branch` thay vì đúng với contract v1 là `party_size`, `branch_id`.
  - Điều này làm agent không tận dụng được tool dù logic của tool bản thân vẫn đúng.
- **Log Source**:
  - `logs/2026-04-06.log`, khu vực khoảng 08:30 đến 08:31.
  - Một trace điển hình cho thấy model sinh action kiểu `get_available_slots(date="2026-04-06", guests=4, branch=1)` rồi sau đó trả lời theo hướng phỏng đoán thay vì thực thi tool đúng contract.
- **Diagnosis**:
  - Nguyên nhân không nằm hoàn toàn ở model, mà nằm ở **độ khó dùng của tool spec v1 đối với LLM**.
  - Trong v1, một số contract còn mang tính kỹ thuật quá nhiều:
    - `check_table_options()` dùng `reservation_time` dạng ISO thay vì cặp `date + time_slot`
    - `calculate_deposit_amount()` dùng `is_vip_room: bool`, trong khi người dùng và model thường nghĩ theo ngôn ngữ tự nhiên kiểu “VIP”, “phòng riêng”, “thường”
    - `create_reservation()` cần nhiều tham số một lúc, bao gồm `table_preference` và `deposit_status`, khiến model dễ bỏ sót hoặc tự đổi tên trường
  - -> tool v1 hợp lý với dev, nhưng chưa đủ tối ưu với LLM.
- **Solution**:
  - Ở phiên bản tiếp theo, nhóm chuyển sang [restaurant_tools_v2.py], trong đó:
    - `reservation_time` được tách thành `date` và `time_slot`
    - `is_vip_room` được đổi thành `room_type`
    - contract tạo reservation được rút gọn và gần ngôn ngữ người dùng hơn
  - Bổ sung thêm `_serialize_action_call(...)` ở agent để giữ format action ổn định giữa các vòng lặp
- **Kết quả**:
  - Ở cửa sổ log ban đầu, success rate heuristic chỉ đạt **62.75%** trên 51 lượt chạy.
  - Ở cửa sổ ổn định hơn từ 10:30 trở đi, success rate tăng lên **97.40%** trên 77 lượt chạy.
  - Điều này cho thấy chất lượng của tool spec ảnh hưởng trực tiếp đến độ tin cậy của agent, không kém gì prompt hay model.

Bài học rút ra:

- Khi xây tool cho AI agent, không chỉ cần code đúng, mà còn phải “dễ hiểu với model”.
- Một tool spec tốt phải cân bằng giữa tính chính xác kỹ thuật và tính tự nhiên trong cách biểu diễn tham số.

---

## III. Personal Insights: Chatbot vs ReAct

1. **Reasoning**

Điểm khác biệt lớn nhất quan sát được là agent không trả lời ngay lập tức như chatbot, mà biết dừng để gọi công cụ. Với chatbot thường, câu hỏi như “tối nay còn bàn 5 người không?” rất dễ bị trả lời cảm tính hoặc hallucination. Với ReAct agent, `Thought` giúp hệ thống xác định bước tiếp theo phải là kiểm tra availability trước, sau đó mới có thể kết luận.

2. **Reliability**

Agent chỉ thực sự đáng tin khi tool spec được thiết kế tốt. Trong giai đoạn Tooling v1, agent đôi khi còn tệ hơn chatbot ở chỗ nó có hoạt động nhưng gọi sai tham số nên không thực thi được. Điều này cho thấy agent không tự động mạnh hơn chatbot; agent chỉ mạnh khi cả **LLM + tool contract + parser** cùng ăn khớp.

3. **Observation**

Observation là phần biến một mô hình ngôn ngữ thành một hệ thống biết hành động. Sau khi tool trả về kết quả như danh sách giờ trống hoặc mức cọc, bước suy luận tiếp theo của agent được dựa trên dữ liệu thật từ môi trường. Đây là khác biệt bản chất so với chatbot truyền thống, vốn chỉ dựa vào những gì nhớ trong prompt và trọng số mô hình.

---

## IV. Future Improvements 

- **Scalability**:
  - Thay thế file Excel bằng database có transaction để hỗ trợ nhiều người dùng đồng thời.
  - Tách riêng lớp service nghiệp vụ và lớp tool wrapper để dễ mở rộng thêm tool mới.
- **Safety**:
  - Chuyển toàn bộ action sang JSON schema cứng thay vì regex text parsing.
  - Validate chặt các tham số đầu vào trước khi cho tool thực thi, đặc biệt với tool ghi dữ liệu như `create_reservation`.
- **Performance**:
  - Nối `PerformanceTracker` vào runtime thật để theo dõi token, latency và cost theo từng tool-flow.
  - Dùng cache theo branch/date/time cho các truy vấn availability lặp lại nhiều lần.

Nếu tiếp tục phát triển phần Tooling v1 lên production-level, có đề xuất:

- Đổi tên tham số theo ngôn ngữ tự nhiên hơn ngay từ đầu để model ít phải dịch.
- Bổ sung mô tả tool bằng ví dụ few-shot ngay trong tool registry.
- Tách tool “read” và tool “write” thành hai mức độ an toàn khác nhau, trong đó các tool ghi dữ liệu cần thêm cơ chế xác nhận hoặc supervisor.

---

