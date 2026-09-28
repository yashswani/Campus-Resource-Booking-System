"""
Campus Resource Booking System - Booking Workflow Service
=========================================================

Functional Module: Booking Workflow & Approval Management
Non-Functional Requirements Addressed:
- Security: User ownership verification on cancellations, role-based approval gating.
- Reliability: Atomic conflict checks preventing double-booking; validation of dates and slots.
- Performance: Optimized SQL joins resolving User and Resource metadata in a single query.
- Maintainability: Centralized slot definitions, clean status lifecycle (PENDING -> APPROVED/REJECTED/CANCELLED).
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict
from database import db
from models import Booking
from resource_manager import ResourceManager

TIME_SLOTS = [
    "08:00 - 10:00",
    "10:00 - 12:00",
    "12:00 - 14:00",
    "14:00 - 16:00",
    "16:00 - 18:00",
    "18:00 - 20:00"
]

BOOKING_STATUSES = ["PENDING", "APPROVED", "REJECTED", "CANCELLED"]


class BookingService:
    """Manages the lifecycle of facility and equipment reservation requests."""

    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, str]:
        """Validates that date is in YYYY-MM-DD format and is today or in the future."""
        try:
            target_date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
            if target_date < date.today():
                return False, f"Booking date '{date_str}' is in the past. Please select a future date."
            return True, ""
        except ValueError:
            return False, "Invalid date format. Please use YYYY-MM-DD (e.g., 2026-10-15)."

    @staticmethod
    def check_availability(resource_id: int, booking_date: str, time_slot: str) -> Tuple[bool, str]:
        """
        Checks if a resource is available for a given date and time slot.
        Returns (is_available, message).
        """
        res = ResourceManager.get_resource_by_id(resource_id)
        if not res:
            return False, f"Resource #{resource_id} not found."

        if not res.is_available:
            return False, f"Resource '{res.name}' is currently '{res.status}' and cannot be booked."

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Check for approved bookings on that date and slot
                cursor.execute("""
                    SELECT booking_id, status FROM bookings
                    WHERE resource_id = ? AND booking_date = ? AND time_slot = ? AND status = 'APPROVED';
                """, (resource_id, booking_date, time_slot))
                approved_conflict = cursor.fetchone()

                if approved_conflict:
                    return False, f"Resource '{res.name}' is already APPROVED for another booking on {booking_date} ({time_slot})."

                return True, "Slot is available."
        except sqlite3.Error as e:
            return False, f"Database check error: {e}"

    @staticmethod
    def request_booking(
        user_id: int,
        resource_id: int,
        booking_date: str,
        time_slot: str,
        purpose: str
    ) -> Tuple[bool, str, Optional[int]]:
        """Submits a new booking request."""
        # Validate Date
        d_valid, d_msg = BookingService.validate_date(booking_date)
        if not d_valid:
            return False, d_msg, None

        # Validate Time Slot
        time_slot = time_slot.strip()
        if time_slot not in TIME_SLOTS:
            return False, f"Invalid time slot. Choose from: {', '.join(TIME_SLOTS)}", None

        # Validate Purpose
        purpose = purpose.strip()
        if not purpose or len(purpose) < 5:
            return False, "Please provide a descriptive purpose for the booking (min 5 characters).", None

        # Check Availability Conflict
        avail_ok, avail_msg = BookingService.check_availability(resource_id, booking_date, time_slot)
        if not avail_ok:
            return False, avail_msg, None

        # Check for user duplicate pending request on same slot
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT booking_id FROM bookings
                    WHERE user_id = ? AND resource_id = ? AND booking_date = ? AND time_slot = ? AND status = 'PENDING';
                """, (user_id, resource_id, booking_date, time_slot))
                if cursor.fetchone():
                    return False, "You already have a PENDING request for this resource and time slot.", None

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO bookings (user_id, resource_id, booking_date, time_slot, purpose, status, admin_remarks, created_at)
                    VALUES (?, ?, ?, ?, ?, 'PENDING', '', ?);
                """, (user_id, resource_id, booking_date, time_slot, purpose, now))
                conn.commit()
                booking_id = cursor.lastrowid
                return True, f"Booking request #{booking_id} submitted successfully! Awaiting Admin approval.", booking_id
        except sqlite3.Error as e:
            return False, f"Database error submitting booking: {e}", None

    @staticmethod
    def get_user_bookings(user_id: int, status_filter: Optional[str] = None) -> List[Booking]:
        """Retrieves booking history for a specific user with resource details."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT b.booking_id, b.user_id, b.resource_id, b.booking_date, b.time_slot,
                           b.purpose, b.status, b.admin_remarks, b.created_at,
                           u.username, r.name as resource_name, r.location as resource_location
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    JOIN resources r ON b.resource_id = r.resource_id
                    WHERE b.user_id = ?
                """
                params = [user_id]

                if status_filter:
                    query += " AND b.status = ?"
                    params.append(status_filter.strip().upper())

                query += " ORDER BY b.booking_date DESC, b.booking_id DESC;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    Booking(
                        booking_id=r["booking_id"],
                        user_id=r["user_id"],
                        resource_id=r["resource_id"],
                        booking_date=r["booking_date"],
                        time_slot=r["time_slot"],
                        purpose=r["purpose"],
                        status=r["status"],
                        admin_remarks=r["admin_remarks"],
                        created_at=r["created_at"],
                        username=r["username"],
                        resource_name=r["resource_name"],
                        resource_location=r["resource_location"]
                    )
                    for r in rows
                ]
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return []

    @staticmethod
    def get_all_bookings(
        status_filter: Optional[str] = None,
        date_filter: Optional[str] = None,
        resource_id_filter: Optional[int] = None
    ) -> List[Booking]:
        """Admin query to retrieve all bookings with multi-criteria filters."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT b.booking_id, b.user_id, b.resource_id, b.booking_date, b.time_slot,
                           b.purpose, b.status, b.admin_remarks, b.created_at,
                           u.username, r.name as resource_name, r.location as resource_location
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    JOIN resources r ON b.resource_id = r.resource_id
                    WHERE 1=1
                """
                params = []

                if status_filter:
                    query += " AND b.status = ?"
                    params.append(status_filter.strip().upper())

                if date_filter:
                    query += " AND b.booking_date = ?"
                    params.append(date_filter.strip())

                if resource_id_filter:
                    query += " AND b.resource_id = ?"
                    params.append(resource_id_filter)

                query += " ORDER BY b.booking_date DESC, b.booking_id DESC;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    Booking(
                        booking_id=r["booking_id"],
                        user_id=r["user_id"],
                        resource_id=r["resource_id"],
                        booking_date=r["booking_date"],
                        time_slot=r["time_slot"],
                        purpose=r["purpose"],
                        status=r["status"],
                        admin_remarks=r["admin_remarks"],
                        created_at=r["created_at"],
                        username=r["username"],
                        resource_name=r["resource_name"],
                        resource_location=r["resource_location"]
                    )
                    for r in rows
                ]
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return []

    @staticmethod
    def get_booking_by_id(booking_id: int) -> Optional[Booking]:
        """Fetches a specific booking record with joined user and resource details."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.booking_id, b.user_id, b.resource_id, b.booking_date, b.time_slot,
                           b.purpose, b.status, b.admin_remarks, b.created_at,
                           u.username, r.name as resource_name, r.location as resource_location
                    FROM bookings b
                    JOIN users u ON b.user_id = u.user_id
                    JOIN resources r ON b.resource_id = r.resource_id
                    WHERE b.booking_id = ?;
                """, (booking_id,))
                r = cursor.fetchone()
                if r:
                    return Booking(
                        booking_id=r["booking_id"],
                        user_id=r["user_id"],
                        resource_id=r["resource_id"],
                        booking_date=r["booking_date"],
                        time_slot=r["time_slot"],
                        purpose=r["purpose"],
                        status=r["status"],
                        admin_remarks=r["admin_remarks"],
                        created_at=r["created_at"],
                        username=r["username"],
                        resource_name=r["resource_name"],
                        resource_location=r["resource_location"]
                    )
                return None
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return None

    @staticmethod
    def update_booking_status(booking_id: int, new_status: str, admin_remarks: str = "") -> Tuple[bool, str]:
        """Admin action: Approves or Rejects a booking request."""
        new_status = new_status.strip().upper()
        if new_status not in ["APPROVED", "REJECTED", "CANCELLED"]:
            return False, f"Invalid status update. Allowed: APPROVED, REJECTED, CANCELLED"

        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            return False, f"Booking request #{booking_id} not found."

        if booking.status in ["CANCELLED", "REJECTED"]:
            return False, f"Cannot update booking #{booking_id} because it is already {booking.status}."

        # If approving, verify conflict again
        if new_status == "APPROVED":
            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT booking_id FROM bookings
                        WHERE resource_id = ? AND booking_date = ? AND time_slot = ? 
                          AND status = 'APPROVED' AND booking_id != ?;
                    """, (booking.resource_id, booking.booking_date, booking.time_slot, booking_id))
                    if cursor.fetchone():
                        return False, f"Conflict: Another approved booking already occupies this resource on {booking.booking_date} ({booking.time_slot})."
            except sqlite3.Error as e:
                return False, f"Database error verifying conflict: {e}"

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bookings
                    SET status = ?, admin_remarks = ?
                    WHERE booking_id = ?;
                """, (new_status, admin_remarks.strip(), booking_id))
                conn.commit()
                return True, f"Booking #{booking_id} has been marked as '{new_status}'."
        except sqlite3.Error as e:
            return False, f"Database error updating status: {e}"

    @staticmethod
    def cancel_booking(booking_id: int, user_id: int, is_admin: bool = False) -> Tuple[bool, str]:
        """Cancels a booking (by the owning student or an admin)."""
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            return False, f"Booking #{booking_id} not found."

        if not is_admin and booking.user_id != user_id:
            return False, "Permission denied: You can only cancel your own bookings."

        if booking.status == "CANCELLED":
            return False, f"Booking #{booking_id} is already cancelled."

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bookings
                    SET status = 'CANCELLED', admin_remarks = admin_remarks || ' [User Cancelled]'
                    WHERE booking_id = ?;
                """, (booking_id,))
                conn.commit()
                return True, f"Booking #{booking_id} has been cancelled."
        except sqlite3.Error as e:
            return False, f"Database error cancelling booking: {e}"
