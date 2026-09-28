"""
Campus Resource Booking System - Data Models
============================================

Non-Functional Requirements Addressed:
- Maintainability: Strict type hinting, standard dataclasses, self-documenting field definitions.
- Reliability: Default factory values and validation helper properties.
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class User:
    """Represents a system user (Student or Admin)."""
    user_id: Optional[int]
    username: str
    full_name: str
    email: str
    role: str  # 'Student' or 'Admin'
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_admin(self) -> bool:
        return self.role.strip().lower() == "admin"

    @property
    def is_student(self) -> bool:
        return self.role.strip().lower() == "student"


@dataclass
class Resource:
    """Represents a physical campus facility, room, or equipment."""
    resource_id: Optional[int]
    name: str
    category: str  # 'Auditorium', 'Lab', 'Classroom', 'Equipment', 'Sports Facility'
    capacity: int
    location: str
    status: str  # 'Available', 'Under Maintenance', 'Decommissioned'
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_available(self) -> bool:
        return self.status.strip().lower() == "available"


@dataclass
class Booking:
    """Represents a reservation request or confirmed reservation."""
    booking_id: Optional[int]
    user_id: int
    resource_id: int
    booking_date: str  # Format: YYYY-MM-DD
    time_slot: str     # e.g., '09:00 - 11:00', '11:00 - 13:00', '14:00 - 16:00', '16:00 - 18:00'
    purpose: str
    status: str        # 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'
    admin_remarks: Optional[str] = ""
    created_at: Optional[str] = None
    # Joined metadata fields for presentation
    username: Optional[str] = None
    resource_name: Optional[str] = None
    resource_location: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
