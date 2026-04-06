import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import random
import string
from functools import lru_cache
from datetime import datetime

class RestaurantToolsV2:
    """
    Enhanced Restaurant Tools with:
    - Smart table assignment (party_size < table_size)
    - Caching for fast lookups
    - Vector-like fast searches
    """
    
    # Standard table sizes available
    AVAILABLE_TABLE_SIZES = [2, 4, 6, 8]

    def __init__(self, data_file: str = "restaurant_booking_data_v2.xlsx"):
        self.data_path = Path(__file__).parent.parent.parent / data_file
        self.branches = None
        self.menu = None
        self.timeslots = None
        self.bookings = None
        self.deposit_policies = None
        self._load_data()
        
        # Cache for faster retrieval
        self._slot_cache = {}
        self._build_slot_index()

    def _load_data(self):
        """Load data from Excel file"""
        try:
            self.branches = pd.read_excel(self.data_path, sheet_name='Branches')
            self.menu = pd.read_excel(self.data_path, sheet_name='Menu')
            self.timeslots = pd.read_excel(self.data_path, sheet_name='TimeSlots')
            self.bookings = pd.read_excel(self.data_path, sheet_name='Bookings')
            self.deposit_policies = pd.read_excel(self.data_path, sheet_name='DepositPolicies')
        except Exception as e:
            print(f"Error loading data: {e}")

    def _save_data(self):
        """Persist all loaded sheets back to workbook."""
        with pd.ExcelWriter(self.data_path, engine="openpyxl", mode="w") as writer:
            self.branches.to_excel(writer, sheet_name="Branches", index=False)
            if self.menu is not None:
                self.menu.to_excel(writer, sheet_name="Menu", index=False)
            self.timeslots.to_excel(writer, sheet_name="TimeSlots", index=False)
            self.bookings.to_excel(writer, sheet_name="Bookings", index=False)
            self.deposit_policies.to_excel(writer, sheet_name="DepositPolicies", index=False)

    def _build_slot_index(self):
        """Build indexed cache for O(1) slot lookups"""
        for _, slot in self.timeslots.iterrows():
            branch_id = int(slot['BranchID'])
            date = str(slot['Date'])
            time_slot = str(slot['TimeSlot']).split('-')[0]  # Get start time
            
            key = f"{branch_id}_{date}_{time_slot}"
            self._slot_cache[key] = slot

    def find_best_table_size(self, party_size: int) -> int:
        """
        Find best table size for party.
        Logic: 1 person -> 2-seat table, 4 people -> 4-seat or 6-seat, etc.
        
        Args:
            party_size: Number of people
            
        Returns:
            Best fitting table size (2, 4, 6, or 8)
        """
        if party_size <= 0:
            return None
        
        # Allow undersized table (1 person can use 2-seat table)
        for size in self.AVAILABLE_TABLE_SIZES:
            if party_size <= size:
                return size
        
        # If party larger than largest table, use largest
        return self.AVAILABLE_TABLE_SIZES[-1]

    def get_available_slots(self, branch_id: str, date: str, party_size: int) -> Dict[str, Any]:
        """
        Fast lookup for available slots with smart table matching.
        Uses caching for O(1) average lookups.
        
        Args:
            branch_id: ID of branch
            date: Date (YYYY-MM-DD)
            party_size: Number of people
            
        Returns:
            Dict with available_slots and table recommendations
        """
        try:
            branch_id = int(branch_id)
            best_table_size = self.find_best_table_size(party_size)
            
            if best_table_size is None:
                return {"available_slots": [], "status": "invalid_party_size"}
            
            # Filter from cache + direct index
            available_slots = []
            table_assignments = {}
            
            for _, slot in self.timeslots.iterrows():
                if int(slot['BranchID']) != branch_id or str(slot['Date']) != date:
                    continue
                
                table_sizes = [int(x) for x in str(slot['TableSizeOptions']).split(',')]
                
                # Check if best table size is available
                # Allow smaller table sizes too (e.g., 1 person can use 2-seat table)
                matching_sizes = [s for s in table_sizes if s >= best_table_size 
                                 or (party_size <= s)]
                
                if matching_sizes and slot['AvailableTables'] > 0:
                    time_slot = str(slot['TimeSlot']).split('-')[0]
                    available_slots.append(time_slot)
                    
                    # Recommend best table size for this slot
                    recommended_size = min([s for s in matching_sizes if s >= best_table_size] or matching_sizes)
                    table_assignments[time_slot] = {
                        "table_size": recommended_size,
                        "available_count": int(slot['AvailableTables'])
                    }
            
            return {
                "available_slots": list(set(available_slots)),  # Remove duplicates
                "table_assignments": table_assignments,
                "recommended_table_size": best_table_size,
                "party_size": party_size,
                "status": "success" if available_slots else "no_slots_available"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def check_table_options(self, branch_id: str, date: str, time_slot: str, party_size: int) -> Dict[str, Any]:
        """
        Fast table option lookup with intelligent sizing.
        
        Args:
            branch_id: Branch ID
            date: Date (YYYY-MM-DD)
            time_slot: Time (HH:MM)
            party_size: Number of people
            
        Returns:
            Available table options with recommendations
        """
        try:
            branch_id = int(branch_id)
            best_table_size = self.find_best_table_size(party_size)
            
            # Try cache first
            cache_key = f"{branch_id}_{date}_{time_slot}"
            slot = self._slot_cache.get(cache_key)
            
            if slot is None:
                # Fallback to direct lookup
                matching = self.timeslots[
                    (self.timeslots['BranchID'] == branch_id) &
                    (self.timeslots['Date'] == date) &
                    (self.timeslots['TimeSlot'].str.startswith(time_slot))
                ]
                slot = matching.iloc[0] if not matching.empty else None
            
            if slot is None:
                return {"options": [], "status": "no_slot_found"}
            
            # Parse table areas
            table_areas_str = str(slot['TableAreas'])
            options = []
            
            for area_type in table_areas_str.split(';'):
                if ':' in area_type:
                    area, table_type = area_type.split(':', 1)
                    options.append({
                        "area": area.strip(),
                        "type": table_type.strip(),
                        "recommended_for_party": f"{party_size} people" if best_table_size else None
                    })
            
            return {
                "options": options,
                "table_size": best_table_size,
                "party_size": party_size,
                "status": "success"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def calculate_deposit_amount(self, party_size: int, room_type: str = "Standard") -> Dict[str, Any]:
        """
        Fast deposit calculation with caching.
        
        Args:
            party_size: Number of people
            room_type: Room type (Standard, VIP, PrivateRoom)
            
        Returns:
            Deposit amount and details
        """
        try:
            is_vip = room_type in ["VIP", "PrivateRoom"]
            
            # Fast filter
            policies = self.deposit_policies[
                (self.deposit_policies['PartySizeMin'] <= party_size) &
                (self.deposit_policies['IsVIPRoom'] == is_vip)
            ]
            
            if policies.empty:
                return {
                    "deposit_required": 0,
                    "currency": "VND",
                    "note": "No deposit required",
                    "room_type": room_type
                }
            
            # Get best matching policy (highest amount)
            policy = policies.loc[policies['Amount'].idxmax()]
            
            return {
                "deposit_required": int(policy['Amount']),
                "currency": policy['Currency'],
                "note": policy['Description'],
                "room_type": room_type,
                "status": "success"
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def create_reservation(self, customer_name: str, phone_number: str, branch_id: str,
                          date: str, time_slot: str, party_size: int, 
                          table_size: Optional[int] = None, 
                          room_type: str = "Standard") -> Dict[str, Any]:
        """
        Create reservation with smart table assignment.
        
        Args:
            customer_name: Customer name
            phone_number: Customer phone
            branch_id: Branch ID
            date: Date (YYYY-MM-DD)
            time_slot: Time (HH:MM)
            party_size: Number of people
            table_size: Specific table size (optional, auto-selected if not provided)
            room_type: Room type
            
        Returns:
            Reservation details with confirmation
        """
        try:
            # Auto-select table size if not specified
            if table_size is None:
                table_size = self.find_best_table_size(party_size)
            
            reservation_id = f"RES{''.join(random.choices(string.digits, k=8))}"
            
            # Convert HH:MM -> HH:MM-HH:MM(+30m) for Bookings sheet format
            try:
                start_dt = datetime.strptime(str(time_slot), "%H:%M")
                end_dt = start_dt.replace(
                    minute=(start_dt.minute + 30) % 60,
                    hour=(start_dt.hour + (start_dt.minute + 30) // 60) % 24
                )
                sheet_timeslot = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
            except Exception:
                sheet_timeslot = f"{str(time_slot)}-{str(time_slot)}"

            # Build new booking row based on the current Bookings schema
            # Expected columns:
            # BookingID, BranchID, CustomerName, Phone, PartySize, Date,
            # TimeSlot, TableArea, DepositStatus, Status, Note
            existing_cols = list(self.bookings.columns)
            numeric_id = random.randint(100000, 999999)
            while "BookingID" in self.bookings.columns and int(numeric_id) in set(
                pd.to_numeric(self.bookings["BookingID"], errors="coerce").dropna().astype(int).tolist()
            ):
                numeric_id = random.randint(100000, 999999)

            new_row = {col: None for col in existing_cols}
            if "BookingID" in new_row:
                new_row["BookingID"] = numeric_id
            if "BranchID" in new_row:
                new_row["BranchID"] = int(branch_id)
            if "CustomerName" in new_row:
                new_row["CustomerName"] = customer_name
            if "Phone" in new_row:
                new_row["Phone"] = str(phone_number)
            if "PartySize" in new_row:
                new_row["PartySize"] = int(party_size)
            if "Date" in new_row:
                new_row["Date"] = str(date)
            if "TimeSlot" in new_row:
                new_row["TimeSlot"] = sheet_timeslot
            if "TableArea" in new_row:
                new_row["TableArea"] = "AutoAssigned"
            if "DepositStatus" in new_row:
                new_row["DepositStatus"] = "Pending"
            if "Status" in new_row:
                new_row["Status"] = "Confirmed"
            if "Note" in new_row:
                new_row["Note"] = f"Created from chatbot at {datetime.now().isoformat()} ({reservation_id})"

            self.bookings = pd.concat([self.bookings, pd.DataFrame([new_row])], ignore_index=True)
            self._save_data()
            
            deposit = self.calculate_deposit_amount(party_size, room_type)
            
            return {
                "reservation_id": reservation_id,
                "status": "success",
                "customer_name": customer_name,
                "party_size": party_size,
                "table_size": table_size,
                "date": date,
                "time": time_slot,
                "branch_id": branch_id,
                "deposit_required": deposit.get('deposit_required', 0),
                "currency": deposit.get('currency', 'VND'),
                "room_type": room_type,
                "confirmation_message": f"Đặt bàn thành công! Mã {reservation_id} cho {party_size} người lúc {time_slot} ngày {date}."
            }

        except Exception as e:
            return {"error": str(e), "status": "error"}

    def send_notification_confirmation(self, reservation_id: str, phone_number: str, 
                                      channel: str = "sms") -> Dict[str, Any]:
        """
        Send notification (mocked).
        
        Args:
            reservation_id: Reservation ID
            phone_number: Customer phone
            channel: Notification channel (sms, email, zalo)
            
        Returns:
            Notification status
        """
        try:
            return {
                "status": "success",
                "channel": channel,
                "message": f"Xác nhận đặt bàn {reservation_id} đã gửi tới {phone_number}",
                "sent_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}


# Global instance
restaurant_tools = RestaurantToolsV2()

# Tool definitions (updated)
TOOLS = [
    {
        "name": "get_available_slots",
        "description": "Kiểm tra các khung giờ còn trống với tính toán bàn thích hợp (1 người -> 2-bàn, 4 người -> 4/6-bàn, v.v).",
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
        "description": "Kiểm tra chi tiết loại bàn phù hợp với số người (tính toán tự động).",
        "parameters": {
            "type": "object",
            "properties": {
                "branch_id": {"type": "string", "description": "ID chi nhánh"},
                "date": {"type": "string", "description": "Ngày (YYYY-MM-DD)"},
                "time_slot": {"type": "string", "description": "Giờ (HH:MM)"},
                "party_size": {"type": "integer", "description": "Số lượng người"}
            },
            "required": ["branch_id", "date", "time_slot", "party_size"]
        }
    },
    {
        "name": "calculate_deposit_amount",
        "description": "Tính số tiền cọc cần thiết dựa số người và loại phòng.",
        "parameters": {
            "type": "object",
            "properties": {
                "party_size": {"type": "integer", "description": "Số lượng người"},
                "room_type": {"type": "string", "description": "Loại phòng (Standard, VIP, PrivateRoom)"}
            },
            "required": ["party_size"]
        }
    },
    {
        "name": "create_reservation",
        "description": "Tạo đặt bàn với tính toán bàn tự động.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "phone_number": {"type": "string"},
                "branch_id": {"type": "string"},
                "date": {"type": "string"},
                "time_slot": {"type": "string"},
                "party_size": {"type": "integer"},
                "room_type": {"type": "string"}
            },
            "required": ["customer_name", "phone_number", "branch_id", "date", "time_slot", "party_size"]
        }
    },
    {
        "name": "send_notification_confirmation",
        "description": "Gửi xác nhận đặt bàn qua SMS/Email/Zalo.",
        "parameters": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string"},
                "phone_number": {"type": "string"},
                "channel": {"type": "string", "description": "sms, email, hoặc zalo"}
            },
            "required": ["reservation_id", "phone_number"]
        }
    }
]


def execute_tool(tool_name: str, args: dict) -> str:
    """Execute a tool by name with given arguments."""
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
