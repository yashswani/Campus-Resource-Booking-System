# Campus Resource Booking System

## Overview of the Project

The **Campus Resource Booking System** is a modular, command-line Python application developed for university portals. It automates and centralizes the scheduling and management of shared campus facilities—such as seminar halls, research laboratories, smart classrooms, audiovisual equipment, and indoor sports arenas.

The system replaces error-prone manual registers and email-based booking procedures with an automated, conflict-free digital workflow. It incorporates role-based access control (Students vs. Administrators), inventory management, atomic double-booking prevention, and an administrative approval pipeline backed by a local SQLite database.

## Features

- **Role-Based Authentication & Access Control:**
  - Secure registration and login for Students and Administrators.
  - Password security using salted SHA-256 cryptographic hashing.
  - Input validation for emails, usernames, and password strength.

- **Resource Inventory Management (CRUD):**
  - Categorized management of campus assets (Auditoriums, Research Labs, Classrooms, Equipment, Sports Facilities).
  - Admin operations: Add new resources, edit capacities/locations, search catalog, and delete/decommission facilities.
  - Referential integrity checks preventing accidental deletion of resources with active bookings.

- **Conflict-Free Booking Workflow:**
  - Standardized daily operational time slots (08:00–10:00, 10:00–12:00, 12:00–14:00, 14:00–16:00, 16:00–18:00, 18:00–20:00).
  - Real-time slot availability checking for any chosen date.
  - Automated collision detection preventing double-booking of any facility.
  - Complete request lifecycle tracking (`PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`).
  - Student self-service cancellation for active bookings.
  - Administrator approval/rejection queue with custom remarks.

- **System Analytics & Audit Logs:**
  - Filterable master booking log (filter by status, date, or resource ID).
  - Administrative user registry.
  - Operational metrics summary (total users, available resources, booking status breakdown).

## Technologies/Tools Used

- **Programming Language:** Python 3.8+
- **Database Engine:** SQLite3 (Embedded local relational database with ACID compliance)
- **Standard Libraries:** `sqlite3`, `hashlib`, `secrets`, `re`, `datetime`, `dataclasses`, `getpass`, `sys`, `os`
- **CLI Table Formatting:** `tabulate` (with an automatic pure-Python fallback formatter)

## Steps to Install & Run the Project

### 1. Prerequisites
Ensure **Python 3.8 or higher** is installed on your computer.

### 2. Navigate to Project Directory
Open your terminal or command prompt and change directory to the project folder:
```bash
cd "c:\Programming\Yashi VITYARTHI"
```

### 3. Install Dependencies (Optional)
Install `tabulate` for enhanced terminal table formatting:
```bash
pip install -r requirements.txt
```
*(Note: The project runs completely out-of-the-box using Python standard libraries if tabulate is omitted.)*

### 4. Run the Application
Execute the main entry point:
```bash
python main.py
```

## Instructions for Testing

The system automatically initializes `campus_booking.db` with pre-seeded test data upon first launch.

### Pre-Seeded Credentials:
- **Administrator:** Username: `admin` | Password: `Admin@123`
- **Student:** Username: `student1` | Password: `Student@123`

### Test Scenario 1: Student Booking Workflow
1. Launch `python main.py` and select option `1` (Login).
2. Log in using `student1` / `Student@123` (or register a new student account using option `2`).
3. Select **Option 3: Check Resource Slot Availability** for Resource ID `2` (*Robotics & AI Research Lab*) for a future date.
4. Select **Option 4: Submit Booking Request**, choose a slot (e.g., `10:00 - 12:00`), and enter a purpose description.
5. Select **Option 5: View My Bookings & Approval Status** to verify the request is created with status `PENDING`.
6. Select **Option 8: Logout**.

### Test Scenario 2: Administrator Approval Workflow
1. Log in using `admin` / `Admin@123`.
2. Select **Option 2: Review Pending Booking Requests**.
3. Enter the pending Booking ID and choose `1` to **Approve** (with optional remarks).
4. Select **Option 3: View All Campus Bookings** to confirm the status is now `APPROVED`.
5. Select **Option 5: System Overview & Analytics** to observe updated booking statistics.
6. Select **Option 7: Logout**.

### Test Scenario 3: Double-Booking Conflict Prevention
1. Log in as a Student.
2. Attempt to submit a new booking request for the exact same resource, date, and time slot that was approved in Scenario 2.
3. Verify that the system detects the collision and blocks the duplicate booking request.

## Screenshots

<!-- Add your terminal execution screenshots below -->

*Placeholder for terminal execution screenshots:*
- *Screenshot 1: Main Menu & Authentication*
- *Screenshot 2: Student Resource Catalog & Availability Check*
- *Screenshot 3: Student Booking Request Submission*
- *Screenshot 4: Administrator Approval Workflow*
- *Screenshot 5: System Analytics Dashboard*
