#!/usr/bin/env python3
"""
Demo script for Restaurant Booking Agent v1
"""

import os
import sys
sys.path.append('src')

from dotenv import load_dotenv
from src.core.openai_provider import OpenAIProvider
from src.core.mock_provider import MockProvider
from src.agent.agent import ReActAgent

def main():
    # Make Windows console output robust with Unicode (prevents emoji crashes)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Load environment variables
    load_dotenv()

    # Initialize LLM provider
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        provider = OpenAIProvider(api_key=api_key, model_name="gpt-4o")
    else:
        provider = MockProvider()

    # Initialize agent
    agent = ReActAgent(llm=provider, max_steps=10)

    # Test cases
    test_inputs = [
        "Tôi muốn đặt bàn cho 4 người vào tối nay",
        "Nhà hàng có bàn trống lúc 7h tối không?",
        "Đặt bàn VIP cho 6 người vào ngày mai",
    ]

    print("Restaurant Booking Agent Demo")
    print("=" * 50)
    print("Chào mừng bạn đến với hệ thống đặt bàn nhà hàng!")
    print("Bạn có thể hỏi về đặt bàn, kiểm tra availability, v.v.")
    print("Nhập 'quit' hoặc 'exit' để thoát.")
    print("=" * 50)

    while True:
        try:
            user_input = input("\nBạn: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Cảm ơn bạn đã sử dụng dịch vụ!")
                break
                
            if not user_input:
                continue
                
            print("-" * 40)
            print("Agent đang xử lý...")
            
            response = agent.run(user_input)
            print(f"Agent: {response}")
            
        except KeyboardInterrupt:
            print("\nĐã thoát chương trình.")
            break
        except Exception as e:
            print(f"❌ Lỗi: {e}")

    # Optional: Run test cases if wanted
    run_tests = input("\nBạn có muốn chạy các test case mẫu không? (y/n): ").lower().strip()
    if run_tests == 'y':
        print("\n" + "=" * 50)
        print("Chạy test cases mẫu:")
        print("=" * 50)
        
        for i, user_input in enumerate(test_inputs, 1):
            print(f"\nTest Case {i}: {user_input}")
            print("-" * 40)

            try:
                response = agent.run(user_input)
                print(f"Agent Response:\n{response}")
            except Exception as e:
                print(f"❌ Error: {e}")

            print("\n" + "=" * 50)

if __name__ == "__main__":
    main()