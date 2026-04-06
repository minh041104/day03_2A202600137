import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import random
import string

class RestaurantTools:
    """
    Tools for Restaurant Booking Agent v1
    """

    def __init__(self, data_file: str = "restaurant_booking_data_v2.xlsx"):
        self.data_path = Path(__file__).parent.parent.parent / data_file
        self.branches = None
        self.timeslots = None
        self.bookings = None
        self.deposit_policies = None
        self._load_data()

    def _load_data(self):
        """Load data from Excel file"""
        try:
            self.branches = pd.read_excel(self.data_path, sheet_name='Branches')
            self.timeslots = pd.read_excel(self.data_path, sheet_name='TimeSlots')
            self.bookings = pd.read_excel(self.data_path, sheet_name='Bookings')
            self.deposit_policies = pd.read_excel(self.data_path, sheet_name='DepositPolicies')
        except Exception as e:
            print(f"Error loading data: {e}")

    def get_available_slots(self, branch_id: str, date: str, party_size: int) -> Dict[str, Any]:
        """
        Kiểm tra các khung giờ còn trống dựa trên ngày, số lượng khách và chi nhánh.

        Args:
            branch_id: ID của chi nhánh
            date: Ngày (YYYY-MM-DD)
            party_size: Số lượng người

        Returns:
            Dict với available_slots và status
        """
        try:
            # Filter by branch and date
            slots = self.timeslots[
                (self.timeslots['BranchID'] == int(branch_id)) &
                (self.timeslots['Date'] == date)
            ]

            available_slots = []

            for _, slot in slots.iterrows():
                # Check if party_size fits table options
                table_sizes = [int(x) for x in str(slot['TableSizeOptions']).split(',')]
                if any(size >= party_size for size in table_sizes):
                    # Check available tables
                    if slot['AvailableTables'] > 0:
                        # Extract time from TimeSlot (e.g., "18:00-18:30" -> "18:00")
                        time_slot = str(slot['TimeSlot']).split('-')[0]
                        available_slots.append(time_slot)

            return {
                "available_slots": available_slots,
                "status": "success" if available_slots else "no_slots_available"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def check_table_options(self, branch_id: str, reservation_time: str, party_size: int) -> Dict[str, Any]:
        """
        Kiểm tra chi tiết các loại bàn còn trống tại thời điểm đó.

        Args:
            branch_id: ID chi nhánh
            reservation_time: Thời gian (ISO 8601, e.g., "2026-04-06T19:00:00")
            party_size: Số lượng người

        Returns:
            Dict với options (area, type)
        """
        try:
            # Parse date and time from reservation_time
            date = reservation_time.split('T')[0]
            time_part = reservation_time.split('T')[1][:5]  # Get HH:MM

            # Find matching slot
            slot = self.timeslots[
                (self.timeslots['BranchID'] == int(branch_id)) &
                (self.timeslots['Date'] == date) &
                (self.timeslots['TimeSlot'].str.startswith(time_part))
            ]

            if slot.empty:
                return {"options": [], "status": "no_slot_found"}

            # Parse table areas
            table_areas_str = str(slot.iloc[0]['TableAreas'])
            options = []

            for area_type in table_areas_str.split(';'):
                if ':' in area_type:
                    area, table_type = area_type.split(':', 1)
                    options.append({
                        "area": area.strip(),
                        "type": table_type.strip()
                    })

            return {"options": options, "status": "success"}

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def calculate_deposit_amount(self, party_size: int, is_vip_room: bool) -> Dict[str, Any]:
        """
        Tính toán số tiền cần cọc.

        Args:
            party_size: Số lượng người
            is_vip_room: Có phải phòng VIP không

        Returns:
            Dict với deposit info
        """
        try:
            # Find matching policy
            policies = self.deposit_policies[
                (self.deposit_policies['PartySizeMin'] <= party_size) &
                (self.deposit_policies['IsVIPRoom'] == is_vip_room)
            ]

            if policies.empty:
                return {"deposit_required": 0, "currency": "VND", "note": "No deposit required"}

            # Get the highest amount policy
            policy = policies.loc[policies['Amount'].idxmax()]

            return {
                "deposit_required": int(policy['Amount']),
                "currency": policy['Currency'],
                "note": policy['Description']
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def create_reservation(self, customer_name: str, phone_number: str, branch_id: str,
                          reservation_time: str, party_size: int, table_preference: str,
                          deposit_status: str = "pending") -> Dict[str, Any]:
        """
        Tạo đặt bàn mới.

        Args:
            customer_name: Tên khách
            phone_number: Số điện thoại
            branch_id: ID chi nhánh
            reservation_time: Thời gian (ISO 8601)
            party_size: Số lượng người
            table_preference: Sở thích bàn
            deposit_status: Trạng thái cọc

        Returns:
            Dict với booking_id và status
        """
        try:
            # Generate booking ID
            booking_id = f"RES-{random.randint(1000, 9999)}"

            # Parse date and time
            date = reservation_time.split('T')[0]
            time_slot = reservation_time.split('T')[1][:5] + "-19:30"  # Assume 30min slot

            # Create new booking record
            new_booking = {
                'BookingID': booking_id,
                'BranchID': int(branch_id),
                'CustomerName': customer_name,
                'Phone': phone_number,
                'PartySize': party_size,
                'Date': date,
                'TimeSlot': time_slot,
                'TableArea': table_preference,
                'DepositStatus': deposit_status,
                'Status': 'Confirmed',
                'Note': ''
            }

            # In real implementation, this would save to database
            # For now, just return success
            return {
                "booking_id": booking_id,
                "status": "confirmed",
                "message": "Đặt bàn thành công"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def send_notification_confirmation(self, booking_id: str, channel: str) -> Dict[str, Any]:
        """
        Gửi xác nhận qua kênh chỉ định.

        Args:
            booking_id: Mã đặt bàn
            channel: Kênh gửi ("zalo", "sms")

        Returns:
            Dict với status gửi
        """
        try:
            # In real implementation, this would send actual notification
            # For now, simulate success
            from datetime import datetime
            timestamp = datetime.now().isoformat()

            return {
                "status": "sent",
                "timestamp": timestamp,
                "channel": channel,
                "message": f"Confirmation sent via {channel}"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

# Global instance for tools
restaurant_tools = RestaurantTools()

# Tool definitions for agent
TOOLS = [
    {
        "name": "get_available_slots",
        "description": "Kiểm tra các khung giờ còn trống dựa trên ngày, số lượng khách và chi nhánh. Trả về danh sách giờ có thể đặt.",
        "parameters": {
            "type": "object",
            "properties": {
                "branch_id": {"type": "string", "description": "ID của chi nhánh"},
                "date": {"type": "string", "description": "Ngày muốn đặt (YYYY-MM-DD)"},
                "party_size": {"type": "integer", "description": "Số lượng người"}
            },
            "required": ["branch_id", "date", "party_size"]
        }
    },
    {
        "name": "check_table_options",
        "description": "Kiểm tra chi tiết các loại bàn (vùng và loại) còn trống tại thời điểm cụ thể.",
        "parameters": {
            "type": "object",
            "properties": {
                "branch_id": {"type": "string", "description": "ID chi nhánh"},
                "reservation_time": {"type": "string", "description": "Thời gian đặt bàn (ISO 8601)"},
                "party_size": {"type": "integer", "description": "Số lượng người"}
            },
            "required": ["branch_id", "reservation_time", "party_size"]
        }
    },
    {
        "name": "calculate_deposit_amount",
        "description": "Tính toán số tiền cọc cần thiết dựa trên số lượng người và loại phòng.",
        "parameters": {
            "type": "object",
            "properties": {
                "party_size": {"type": "integer", "description": "Số lượng người"},
                "is_vip_room": {"type": "boolean", "description": "Có phải phòng VIP không"}
            },
            "required": ["party_size", "is_vip_room"]
        }
    },
    {
        "name": "create_reservation",
        "description": "Tạo đặt bàn mới trong hệ thống với thông tin đầy đủ.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Tên khách hàng"},
                "phone_number": {"type": "string", "description": "Số điện thoại"},
                "branch_id": {"type": "string", "description": "ID chi nhánh"},
                "reservation_time": {"type": "string", "description": "Thời gian đặt bàn (ISO 8601)"},
                "party_size": {"type": "integer", "description": "Số lượng người"},
                "table_preference": {"type": "string", "description": "Sở thích bàn/khu vực"},
                "deposit_status": {"type": "string", "description": "Trạng thái cọc (pending/paid)"}
            },
            "required": ["customer_name", "phone_number", "branch_id", "reservation_time", "party_size", "table_preference"]
        }
    },
    {
        "name": "send_notification_confirmation",
        "description": "Gửi xác nhận đặt bàn qua kênh chỉ định (zalo/sms).",
        "parameters": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string", "description": "Mã đặt bàn"},
                "channel": {"type": "string", "description": "Kênh gửi tin (zalo/sms)"}
            },
            "required": ["booking_id", "channel"]
        }
    }
]

def execute_tool(tool_name: str, args: dict) -> str:
    """
    Execute a tool by name with given arguments.
    """
    try:
        if tool_name == "get_available_slots":
            result = restaurant_tools.get_available_slots(**args)
        elif tool_name == "check_table_options":
            result = restaurant_tools.check_table_options(**args)
        elif tool_name == "calculate_deposit_amount":
            result = restaurant_tools.calculate_deposit_amount(**args)
        elif tool_name == "create_reservation":
            result = restaurant_tools.create_reservation(**args)
        elif tool_name == "send_notification_confirmation":
            result = restaurant_tools.send_notification_confirmation(**args)
        else:
            return f"Tool {tool_name} not found"

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e), "status": "error"}, ensure_ascii=False)