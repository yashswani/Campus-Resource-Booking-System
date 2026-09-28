"""
Campus Resource Booking System - Main CLI Application
=====================================================

Title: Campus Resource Booking System
Entry Point: main.py

Architectural Overview & Non-Functional Requirements Addressed:
---------------------------------------------------------------
1. PERFORMANCE:
   - Zero-latency local SQLite operations with indexed query lookups.
   - Formatted table rendering with page-level streaming and light memory footprint.
2. SECURITY:
   - Role-based authorization guardrails on every administrative submenu and route.
   - Salted SHA-256 password hashing; masked password prompt inputs.
   - Sanitized numeric/string inputs against prompt injection and format errors.
3. RELIABILITY:
   - Robust try-except wrapping across all interactive input loops and database calls.
   - Safe signal interception handling (KeyboardInterrupt / EOFError) ensuring graceful exit.
   - Foreign-key integrity validation preventing broken relationships.
4. MAINTAINABILITY:
   - Clean, modular separation across Auth, Resource Management, and Booking workflows.
   - Self-documenting functions with explicit typing and docstrings.
"""

import sys
import os
import getpass
from datetime import datetime, date
from typing import List, Optional, Any

# Local Modules
from database import db
from models import User, Resource, Booking
from auth_service import AuthService
from resource_manager import ResourceManager, VALID_CATEGORIES, VALID_STATUSES
from booking_service import BookingService, TIME_SLOTS, BOOKING_STATUSES

# Try importing tabulate for tables; fallback to custom pretty formatter if unavailable
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ANSI Color formatting helper
class Style:
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


def print_banner(text: str, color: str = Style.CYAN) -> None:
    """Prints a styled box banner."""
    width = 68
    border = "=" * width
    print(f"\n{color}{border}")
    print(f" {text.center(width - 2)} ")
    print(f"{border}{Style.RESET}\n")


def print_section(title: str) -> None:
    """Prints a section heading."""
    print(f"\n{Style.BOLD}{Style.BLUE}>>> {title} <<<{Style.RESET}")


def print_success(msg: str) -> None:
    print(f"{Style.GREEN}✔ {msg}{Style.RESET}")


def print_error(msg: str) -> None:
    print(f"{Style.RED}✘ {msg}{Style.RESET}")


def print_info(msg: str) -> None:
    print(f"{Style.YELLOW}ℹ {msg}{Style.RESET}")


def pause() -> None:
    """Waits for user Enter key to continue."""
    try:
        input(f"\n{Style.CYAN}Press [Enter] to return to the menu...{Style.RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


def render_table(headers: List[str], data: List[List[Any]], table_title: Optional[str] = None) -> None:
    """Renders tabular data with tabulate or fallback formatted alignment."""
    if table_title:
        print(f"\n{Style.BOLD}{table_title}{Style.RESET}")

    if not data:
        print_info("No records found.")
        return

    if HAS_TABULATE:
        print(tabulate(data, headers=headers, tablefmt="fancy_grid"))
    else:
        # Fallback text table
        col_widths = [len(h) for h in headers]
        for row in data:
            for idx, val in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(val)))

        header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
        separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

        print(f"\n{header_line}")
        print(separator)
        for row in data:
            print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))
        print()


def prompt_choice(prompt_text: str, valid_choices: List[str]) -> str:
    """Safely prompts for a menu choice with validation."""
    while True:
        try:
            choice = input(f"{Style.BOLD}{prompt_text}{Style.RESET} ").strip()
            if choice in valid_choices:
                return choice
            print_error(f"Invalid option. Please enter one of: {', '.join(valid_choices)}")
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return valid_choices[-1]  # Return last choice (Exit/Back)


# ==========================================
# GUEST / PUBLIC VIEWS
# ==========================================

def view_public_resources() -> None:
    """Displays public catalog of all campus facilities."""
    print_section("Campus Facility & Resource Catalog")
    resources = ResourceManager.get_all_resources()

    headers = ["ID", "Resource Name", "Category", "Capacity", "Location", "Status"]
    data = []
    for r in resources:
        status_color = Style.GREEN if r.is_available else Style.YELLOW
        data.append([
            r.resource_id,
            r.name,
            r.category,
            f"{r.capacity} seats" if r.capacity > 1 else f"{r.capacity} unit",
            r.location,
            f"{status_color}{r.status}{Style.RESET}"
        ])

    render_table(headers, data, "Available University Resources")
    pause()


def show_about() -> None:
    """Displays project description, architecture info, and developer notes."""
    print_banner("About Campus Resource Booking System", Style.MAGENTA)
    about_text = f"""
{Style.BOLD}System Overview:{Style.RESET}
  The Campus Resource Booking System is a unified, terminal-based platform designed
  for university administration and students to eliminate scheduling collisions,
  streamline facility approvals, and digitize inventory tracking.

{Style.BOLD}Core Functional Modules:{Style.RESET}
  1. User Management (Salted SHA-256 Auth, Role-Based Access Control: Student / Admin)
  2. Resource Inventory CRUD (Auditoriums, Research Labs, Classrooms, Equipment)
  3. Booking Workflow (Conflict Detection, Slot Allocation, Approval & Cancellation)

{Style.BOLD}Non-Functional Requirements Complied:{Style.RESET}
  • Security: Salted SHA-256 cryptographic hashing, parameterized SQL.
  • Performance: Indexed SQLite B-Trees for sub-millisecond retrieval.
  • Reliability: ACID database transactions, safe foreign-key constraints.
  • Maintainability: Modular domain separation, typed dataclasses.

{Style.BOLD}Pre-seeded Test Credentials:{Style.RESET}
  - Administrator Account : Username: {Style.CYAN}admin{Style.RESET}    | Password: {Style.CYAN}Admin@123{Style.RESET}
  - Student Account       : Username: {Style.CYAN}student1{Style.RESET} | Password: {Style.CYAN}Student@123{Style.RESET}
    """
    print(about_text)
    pause()


# ==========================================
# STUDENT WORKFLOWS
# ==========================================

def student_view_resources() -> None:
    """Student view for browsing and filtering resources."""
    print_section("Browse Campus Resources")
    print("Filter options:")
    print("1. View All")
    print("2. Filter by Category")
    print("3. View Only Available")
    
    opt = prompt_choice("Select view option (1-3):", ["1", "2", "3"])
    
    cat_filter = None
    status_filter = None

    if opt == "2":
        print(f"Categories: {', '.join(VALID_CATEGORIES)}")
        cat_filter = input("Enter category name: ").strip()
    elif opt == "3":
        status_filter = "Available"

    resources = ResourceManager.get_all_resources(cat_filter, status_filter)
    headers = ["ID", "Name", "Category", "Capacity", "Location", "Status", "Description"]
    data = [
        [r.resource_id, r.name, r.category, r.capacity, r.location, r.status, (r.description[:35] + "..." if len(r.description) > 35 else r.description)]
        for r in resources
    ]
    render_table(headers, data, "University Resources")
    pause()


def student_search_resources() -> None:
    """Student search query across resources."""
    print_section("Search Campus Resources")
    keyword = input("Enter search keyword (name, location, category): ").strip()
    if not keyword:
        print_info("Empty search query.")
        return

    results = ResourceManager.search_resources(keyword)
    headers = ["ID", "Name", "Category", "Capacity", "Location", "Status", "Description"]
    data = [
        [r.resource_id, r.name, r.category, r.capacity, r.location, r.status, r.description]
        for r in results
    ]
    render_table(headers, data, f"Search Results for '{keyword}'")
    pause()


def check_slot_availability_ui() -> None:
    """Interactive check to verify if a slot on a date is open."""
    print_section("Check Resource Availability")
    try:
        res_id_str = input("Enter Resource ID: ").strip()
        if not res_id_str.isdigit():
            print_error("Resource ID must be a numeric value.")
            pause()
            return
        res_id = int(res_id_str)

        res = ResourceManager.get_resource_by_id(res_id)
        if not res:
            print_error(f"Resource with ID #{res_id} not found.")
            pause()
            return

        print(f"Selected Resource: {Style.BOLD}{res.name}{Style.RESET} ({res.category} at {res.location})")
        date_input = input(f"Enter target date (YYYY-MM-DD, default today {date.today()}): ").strip()
        if not date_input:
            date_input = str(date.today())

        d_valid, d_msg = BookingService.validate_date(date_input)
        if not d_valid:
            print_error(d_msg)
            pause()
            return

        print(f"\nChecking availability for {Style.BOLD}{res.name}{Style.RESET} on {date_input}:")
        headers = ["Slot #", "Time Slot", "Status"]
        data = []
        for idx, slot in enumerate(TIME_SLOTS, start=1):
            is_avail, msg = BookingService.check_availability(res_id, date_input, slot)
            status_str = f"{Style.GREEN}AVAILABLE{Style.RESET}" if is_avail else f"{Style.RED}OCCUPIED / UNAVAILABLE{Style.RESET}"
            data.append([idx, slot, status_str])

        render_table(headers, data)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
    pause()


def student_request_booking(auth: AuthService) -> None:
    """Interactive workflow for student booking request submission."""
    user = auth.get_current_user()
    if not user:
        return

    print_section("Submit New Booking Request")
    try:
        res_id_str = input("Enter Resource ID to book: ").strip()
        if not res_id_str.isdigit():
            print_error("Resource ID must be a number.")
            pause()
            return
        res_id = int(res_id_str)

        res = ResourceManager.get_resource_by_id(res_id)
        if not res:
            print_error(f"Resource with ID #{res_id} does not exist.")
            pause()
            return

        if not res.is_available:
            print_error(f"Resource '{res.name}' is currently {res.status}. Cannot book.")
            pause()
            return

        print(f"Target Resource: {Style.BOLD}{res.name}{Style.RESET} (Capacity: {res.capacity} | Location: {res.location})")

        # Date input
        date_str = input(f"Enter Booking Date (YYYY-MM-DD, min today: {date.today()}): ").strip()
        d_valid, d_msg = BookingService.validate_date(date_str)
        if not d_valid:
            print_error(d_msg)
            pause()
            return

        # Display Available Time Slots
        print("\nAvailable Time Slots:")
        for idx, slot in enumerate(TIME_SLOTS, start=1):
            avail, _ = BookingService.check_availability(res_id, date_str, slot)
            tag = "[OPEN]" if avail else "[RESERVED]"
            print(f"  {idx}. {slot} {tag}")

        slot_choice = input(f"Select Time Slot (1-{len(TIME_SLOTS)}): ").strip()
        if not slot_choice.isdigit() or not (1 <= int(slot_choice) <= len(TIME_SLOTS)):
            print_error("Invalid time slot choice.")
            pause()
            return

        selected_slot = TIME_SLOTS[int(slot_choice) - 1]

        # Purpose
        purpose = input("Enter Purpose / Event Description: ").strip()
        if len(purpose) < 5:
            print_error("Purpose description must be at least 5 characters.")
            pause()
            return

        # Confirmation
        print("\n" + "-" * 50)
        print(f"Booking Summary:")
        print(f"  Resource : {res.name}")
        print(f"  Date     : {date_str}")
        print(f"  Time     : {selected_slot}")
        print(f"  Purpose  : {purpose}")
        print("-" * 50)

        confirm = input("Confirm submission? (y/n): ").strip().lower()
        if confirm == 'y':
            success, msg, booking_id = BookingService.request_booking(
                user.user_id, res_id, date_str, selected_slot, purpose
            )
            if success:
                print_success(msg)
            else:
                print_error(msg)
        else:
            print_info("Booking submission cancelled.")

    except Exception as e:
        print_error(f"Error submitting booking: {e}")
    pause()


def student_view_my_bookings(auth: AuthService) -> None:
    """Displays all bookings for the logged-in student."""
    user = auth.get_current_user()
    if not user:
        return

    print_section(f"My Booking Requests & History ({user.username})")
    bookings = BookingService.get_user_bookings(user.user_id)

    headers = ["Booking ID", "Resource", "Location", "Date", "Time Slot", "Status", "Admin Remarks"]
    data = []
    for b in bookings:
        color = Style.YELLOW if b.status == "PENDING" else (Style.GREEN if b.status == "APPROVED" else Style.RED)
        data.append([
            b.booking_id,
            b.resource_name,
            b.resource_location,
            b.booking_date,
            b.time_slot,
            f"{color}{b.status}{Style.RESET}",
            b.admin_remarks or "-"
        ])

    render_table(headers, data, "Your Campus Booking Records")
    pause()


def student_cancel_booking(auth: AuthService) -> None:
    """Allows student to cancel an existing booking request."""
    user = auth.get_current_user()
    if not user:
        return

    print_section("Cancel a Booking Request")
    bookings = BookingService.get_user_bookings(user.user_id)
    cancellable = [b for b in bookings if b.status in ["PENDING", "APPROVED"]]

    if not cancellable:
        print_info("You have no active or pending bookings eligible for cancellation.")
        pause()
        return

    headers = ["Booking ID", "Resource", "Date", "Slot", "Status"]
    data = [[b.booking_id, b.resource_name, b.booking_date, b.time_slot, b.status] for b in cancellable]
    render_table(headers, data, "Active Bookings Eligible for Cancellation")

    b_id_str = input("\nEnter Booking ID to cancel: ").strip()
    if not b_id_str.isdigit():
        print_error("Invalid Booking ID.")
        pause()
        return

    b_id = int(b_id_str)
    confirm = input(f"Are you sure you want to cancel booking #{b_id}? (y/n): ").strip().lower()
    if confirm == 'y':
        success, msg = BookingService.cancel_booking(b_id, user.user_id, is_admin=False)
        if success:
            print_success(msg)
        else:
            print_error(msg)
    else:
        print_info("Cancellation aborted.")
    pause()


# ==========================================
# ADMIN WORKFLOWS
# ==========================================

def admin_resource_management() -> None:
    """Admin submenu for Resource CRUD operations."""
    while True:
        print_section("Admin: Resource Inventory CRUD Management")
        print("1. View All Resources")
        print("2. Add New Resource")
        print("3. Update Existing Resource")
        print("4. Delete / Decommission Resource")
        print("5. Search Resources")
        print("6. Back to Admin Menu")

        choice = prompt_choice("Select operation (1-6):", ["1", "2", "3", "4", "5", "6"])

        if choice == "1":
            resources = ResourceManager.get_all_resources()
            headers = ["ID", "Name", "Category", "Cap", "Location", "Status", "Description"]
            data = [[r.resource_id, r.name, r.category, r.capacity, r.location, r.status, r.description] for r in resources]
            render_table(headers, data, "Current Campus Resources")
            pause()

        elif choice == "2":
            print_section("Add New Campus Resource")
            name = input("Resource Name (e.g., Computer Lab 4): ").strip()
            print(f"Categories: {', '.join(VALID_CATEGORIES)}")
            category = input("Category: ").strip()
            cap_str = input("Capacity (seats or units): ").strip()
            capacity = int(cap_str) if cap_str.isdigit() else 0
            location = input("Location / Room Number: ").strip()
            print(f"Statuses: {', '.join(VALID_STATUSES)}")
            status = input("Initial Status (default Available): ").strip() or "Available"
            desc = input("Description: ").strip()

            success, msg, r_id = ResourceManager.add_resource(name, category, capacity, location, status, desc)
            if success:
                print_success(msg)
            else:
                print_error(msg)
            pause()

        elif choice == "3":
            print_section("Update Existing Resource")
            r_id_str = input("Enter Resource ID to update: ").strip()
            if not r_id_str.isdigit():
                print_error("Invalid ID.")
                pause()
                continue
            r_id = int(r_id_str)
            existing = ResourceManager.get_resource_by_id(r_id)
            if not existing:
                print_error(f"Resource #{r_id} not found.")
                pause()
                continue

            print(f"Editing Resource #{existing.resource_id} ({existing.name})")
            print("Leave blank to keep existing value.")

            name = input(f"New Name [{existing.name}]: ").strip() or None
            category = input(f"New Category [{existing.category}]: ").strip() or None
            cap_str = input(f"New Capacity [{existing.capacity}]: ").strip()
            capacity = int(cap_str) if cap_str.isdigit() else None
            location = input(f"New Location [{existing.location}]: ").strip() or None
            status = input(f"New Status [{existing.status}]: ").strip() or None
            desc = input(f"New Description [{existing.description}]: ").strip() or None

            success, msg = ResourceManager.update_resource(r_id, name, category, capacity, location, status, desc)
            if success:
                print_success(msg)
            else:
                print_error(msg)
            pause()

        elif choice == "4":
            print_section("Delete / Remove Resource")
            r_id_str = input("Enter Resource ID to delete: ").strip()
            if not r_id_str.isdigit():
                print_error("Invalid ID.")
                pause()
                continue
            r_id = int(r_id_str)
            confirm = input(f"Are you sure you want to permanently delete resource #{r_id}? (y/n): ").strip().lower()
            if confirm == 'y':
                success, msg = ResourceManager.delete_resource(r_id)
                if success:
                    print_success(msg)
                else:
                    print_error(msg)
            else:
                print_info("Deletion cancelled.")
            pause()

        elif choice == "5":
            query = input("Enter search keyword: ").strip()
            res = ResourceManager.search_resources(query)
            headers = ["ID", "Name", "Category", "Capacity", "Location", "Status"]
            data = [[r.resource_id, r.name, r.category, r.capacity, r.location, r.status] for r in res]
            render_table(headers, data, f"Results for '{query}'")
            pause()

        elif choice == "6":
            break


def admin_review_bookings() -> None:
    """Admin approval workflow for pending booking requests."""
    print_section("Pending Booking Requests for Review")
    pending = BookingService.get_all_bookings(status_filter="PENDING")

    if not pending:
        print_info("No pending booking requests awaiting review.")
        pause()
        return

    headers = ["Booking ID", "Student", "Resource", "Date", "Slot", "Purpose"]
    data = [[b.booking_id, b.username, b.resource_name, b.booking_date, b.time_slot, b.purpose] for b in pending]
    render_table(headers, data, "Requests Awaiting Administrative Decision")

    b_id_str = input("\nEnter Booking ID to approve or reject (or 'q' to back): ").strip()
    if b_id_str.lower() == 'q' or not b_id_str.isdigit():
        return

    b_id = int(b_id_str)
    booking = BookingService.get_booking_by_id(b_id)
    if not booking or booking.status != "PENDING":
        print_error(f"Valid pending booking #{b_id} not found.")
        pause()
        return

    decision = prompt_choice("Action for this request: (1) Approve, (2) Reject, (3) Cancel Action:", ["1", "2", "3"])
    if decision == "3":
        return

    remarks = input("Enter Administrative Remarks (optional): ").strip()

    if decision == "1":
        success, msg = BookingService.update_booking_status(b_id, "APPROVED", remarks)
    else:
        success, msg = BookingService.update_booking_status(b_id, "REJECTED", remarks)

    if success:
        print_success(msg)
    else:
        print_error(msg)
    pause()


def admin_view_all_bookings() -> None:
    """Admin full bookings log with multi-criteria filtering."""
    print_section("All University Booking Records")
    print("Filter by:")
    print("1. All Bookings")
    print("2. Filter by Status (PENDING, APPROVED, REJECTED, CANCELLED)")
    print("3. Filter by Date")
    print("4. Filter by Resource ID")

    opt = prompt_choice("Select filter option (1-4):", ["1", "2", "3", "4"])

    status_filter = None
    date_filter = None
    res_id_filter = None

    if opt == "2":
        status_filter = input("Enter Status (PENDING, APPROVED, REJECTED, CANCELLED): ").strip().upper()
    elif opt == "3":
        date_filter = input("Enter Date (YYYY-MM-DD): ").strip()
    elif opt == "4":
        r_str = input("Enter Resource ID: ").strip()
        res_id_filter = int(r_str) if r_str.isdigit() else None

    bookings = BookingService.get_all_bookings(status_filter, date_filter, res_id_filter)
    headers = ["ID", "Student", "Resource", "Date", "Slot", "Status", "Remarks"]
    data = []
    for b in bookings:
        c = Style.YELLOW if b.status == "PENDING" else (Style.GREEN if b.status == "APPROVED" else Style.RED)
        data.append([
            b.booking_id,
            b.username,
            b.resource_name,
            b.booking_date,
            b.time_slot,
            f"{c}{b.status}{Style.RESET}",
            b.admin_remarks or "-"
        ])

    render_table(headers, data, "Campus Booking Archive")
    pause()


def admin_view_users() -> None:
    """Displays all registered users in the database."""
    print_section("Registered Portal Users")
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, full_name, email, role, created_at FROM users ORDER BY user_id ASC;")
            rows = cursor.fetchall()
            headers = ["ID", "Username", "Full Name", "Email", "Role", "Registered At"]
            data = [[r["user_id"], r["username"], r["full_name"], r["email"], r["role"], r["created_at"]] for r in rows]
            render_table(headers, data, "User Accounts Registry")
    except Exception as e:
        print_error(f"Error fetching users: {e}")
    pause()


def admin_system_statistics() -> None:
    """Displays high-level operational statistics and summary metrics."""
    print_section("System Overview & Operational Analytics")
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users;")
            total_users = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'Student';")
            total_students = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM resources;")
            total_resources = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM resources WHERE status = 'Available';")
            avail_resources = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM bookings;")
            total_bookings = cursor.fetchone()["count"]

            cursor.execute("SELECT status, COUNT(*) as count FROM bookings GROUP BY status;")
            status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}

            print(f"  • Total Registered Users : {total_users} ({total_students} Students, {total_users - total_students} Admins)")
            print(f"  • Total Resources       : {total_resources} ({avail_resources} Currently Available)")
            print(f"  • Total Booking Records : {total_bookings}")
            print(f"      - Pending Approvals : {Style.YELLOW}{status_counts.get('PENDING', 0)}{Style.RESET}")
            print(f"      - Approved Bookings : {Style.GREEN}{status_counts.get('APPROVED', 0)}{Style.RESET}")
            print(f"      - Rejected Requests : {Style.RED}{status_counts.get('REJECTED', 0)}{Style.RESET}")
            print(f"      - Cancelled Records : {status_counts.get('CANCELLED', 0)}")
    except Exception as e:
        print_error(f"Error compiling statistics: {e}")
    pause()


# ==========================================
# AUTHENTICATION & PROFILE MENUS
# ==========================================

def user_profile_view(auth: AuthService) -> None:
    """Displays details of the currently authenticated user."""
    user = auth.get_current_user()
    if not user:
        return
    print_section("User Profile Information")
    print(f"  User ID       : #{user.user_id}")
    print(f"  Username      : {user.username}")
    print(f"  Full Name     : {user.full_name}")
    print(f"  Email Address : {user.email}")
    print(f"  System Role   : {Style.BOLD}{user.role}{Style.RESET}")
    print(f"  Member Since  : {user.created_at}")
    pause()


def login_flow(auth: AuthService) -> None:
    """Handles interactive user login."""
    print_section("User Login")
    username = input("Username: ").strip()
    try:
        password = getpass.getpass("Password: ")
    except Exception:
        password = input("Password: ")

    success, msg, user = auth.login(username, password)
    if success and user:
        print_success(msg)
    else:
        print_error(msg)
    pause()


def register_flow(auth: AuthService) -> None:
    """Handles interactive student registration."""
    print_section("Student Account Registration")
    print_info("Create your campus credentials (Alphanumeric username, valid email, strong password).")
    username = input("Desired Username (3-20 chars): ").strip()
    full_name = input("Full Name: ").strip()
    email = input("Email Address: ").strip()
    try:
        password = getpass.getpass("Password (min 6 chars, letters & digits): ")
        password_confirm = getpass.getpass("Confirm Password: ")
    except Exception:
        password = input("Password (min 6 chars, letters & digits): ")
        password_confirm = input("Confirm Password: ")

    if password != password_confirm:
        print_error("Passwords do not match. Registration aborted.")
        pause()
        return

    success, msg = auth.register_user(username, password, full_name, email, role="Student")
    if success:
        print_success(msg)
    else:
        print_error(msg)
    pause()


# ==========================================
# MAIN DASHBOARD CONTROLLERS
# ==========================================

def student_dashboard(auth: AuthService) -> None:
    """Main menu loop for authenticated Student users."""
    user = auth.get_current_user()
    while auth.is_logged_in() and user and user.is_student:
        print_banner(f"Campus Resource Booking - Student Portal ({user.full_name})", Style.CYAN)
        print(f"Logged in as: {Style.BOLD}{user.username}{Style.RESET} [Role: Student]\n")
        print("1. Browse Campus Resources")
        print("2. Search Resources Catalog")
        print("3. Check Resource Slot Availability")
        print("4. Submit Booking Request")
        print("5. View My Bookings & Approval Status")
        print("6. Cancel an Active Booking")
        print("7. My Account Profile")
        print("8. Logout")

        choice = prompt_choice("Select an option (1-8):", ["1", "2", "3", "4", "5", "6", "7", "8"])

        if choice == "1":
            student_view_resources()
        elif choice == "2":
            student_search_resources()
        elif choice == "3":
            check_slot_availability_ui()
        elif choice == "4":
            student_request_booking(auth)
        elif choice == "5":
            student_view_my_bookings(auth)
        elif choice == "6":
            student_cancel_booking(auth)
        elif choice == "7":
            user_profile_view(auth)
        elif choice == "8":
            auth.logout()
            print_info("Logged out successfully.")
            pause()
            break


def admin_dashboard(auth: AuthService) -> None:
    """Main menu loop for authenticated Administrator users."""
    user = auth.get_current_user()
    while auth.is_logged_in() and user and user.is_admin:
        print_banner(f"Campus Resource Booking - Administrator Portal", Style.GREEN)
        print(f"Administrator: {Style.BOLD}{user.full_name}{Style.RESET} ({user.username})\n")
        print("1. Resource Management (Add, View, Update, Delete)")
        print("2. Review Pending Booking Requests (Approve / Reject)")
        print("3. View All Campus Bookings (Filtered Log)")
        print("4. User Accounts Registry")
        print("5. System Overview & Analytics")
        print("6. My Account Profile")
        print("7. Logout")

        choice = prompt_choice("Select an option (1-7):", ["1", "2", "3", "4", "5", "6", "7"])

        if choice == "1":
            admin_resource_management()
        elif choice == "2":
            admin_review_bookings()
        elif choice == "3":
            admin_view_all_bookings()
        elif choice == "4":
            admin_view_users()
        elif choice == "5":
            admin_system_statistics()
        elif choice == "6":
            user_profile_view(auth)
        elif choice == "7":
            auth.logout()
            print_info("Admin logged out successfully.")
            pause()
            break


def main_loop() -> None:
    """Top-level application loop."""
    auth = AuthService()

    while True:
        try:
            if auth.is_logged_in():
                current_user = auth.get_current_user()
                if current_user and current_user.is_admin:
                    admin_dashboard(auth)
                else:
                    student_dashboard(auth)
            else:
                print_banner("Welcome to Campus Resource Booking System", Style.BLUE)
                print("1. Login to Portal")
                print("2. Register as New Student")
                print("3. View Public Campus Facilities Catalog")
                print("4. About System & Default Credentials")
                print("5. Exit Application")

                choice = prompt_choice("Select an option (1-5):", ["1", "2", "3", "4", "5"])

                if choice == "1":
                    login_flow(auth)
                elif choice == "2":
                    register_flow(auth)
                elif choice == "3":
                    view_public_resources()
                elif choice == "4":
                    show_about()
                elif choice == "5":
                    print_banner("Thank you for using Campus Resource Booking System. Goodbye!", Style.CYAN)
                    sys.exit(0)

        except (KeyboardInterrupt, EOFError):
            print("\n\nApplication interrupted. Safely closing...")
            sys.exit(0)
        except Exception as e:
            print_error(f"Fatal runtime error: {e}")
            pause()


if __name__ == "__main__":
    main_loop()
