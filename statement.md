# Problem Statement

University campuses feature a wide array of shared facilities and equipment—including auditoriums, specialized research laboratories, smart classrooms, projection kits, and sports facilities. Traditionally, the reservation of these resources relies on manual paper ledgers, informal verbal approvals, or uncoordinated email threads. This manual approach frequently leads to scheduling conflicts, accidental double-bookings, lack of usage transparency, unauthorized access, and administrative inefficiencies. The **Campus Resource Booking System** addresses these issues by providing a centralized, automated, and conflict-free digital management platform that streamlines resource scheduling, user accountability, and administrative approvals.

# Scope of the Project

The scope of this project encompasses:
- **User Authentication & Role-Based Access Control:** Secure registration, authentication with salted cryptographic password hashing, and distinct access tiers for Students and Administrators.
- **Resource Inventory Management:** Complete CRUD (Create, Read, Update, Delete/Decommission) operations for campus resources, with capacity, category, and status tracking.
- **Conflict-Free Reservation Workflow:** Standardized operational time slots, atomic collision detection preventing overlapping bookings, and an administrative approval/rejection lifecycle with remarks.
- **Audit Logging & Analytics:** Complete historical tracking of all booking records, cancellation management, and system-wide operational statistics.
- **Local Relational Storage:** Embedded SQLite persistence ensuring ACID compliance, foreign key integrity, and sub-millisecond query performance without requiring external database servers.

# Target Users

- **Students & Student Organizations:** Individuals and campus clubs seeking to browse available facilities, verify real-time slot availability, request reservations for academic/extracurricular events, and monitor approval statuses.
- **University Administrators & Faculty:** Facility managers, lab in-charges, and department heads responsible for maintaining the resource catalog, reviewing and approving/rejecting booking requests, and monitoring resource utilization.
- **Academic Evaluators:** Instructors and auditors assessing system design, modular software architecture, data integrity, and role-based workflows.

# High-Level Features

- **User Management & Authentication Module:**
  - Secure registration and login with input validation (regex checks on username and email).
  - Salted SHA-256 password hashing.
  - Role-Based Access Control (RBAC) separating Student and Admin privileges.
  - Profile inspection and secure logout.

- **Resource Inventory CRUD Module:**
  - Categorized resource directory (Auditorium, Lab, Classroom, Equipment, Sports Facility).
  - Admin capabilities to add, edit, search, and delete/decommission resources.
  - Deletion guardrails preventing the removal of resources linked to active bookings.

- **Booking Workflow & Conflict Prevention Module:**
  - Standardized daily time-slot discretization (e.g., 08:00–10:00, 10:00–12:00, 12:00–14:00, 14:00–16:00, 16:00–18:00, 18:00–20:00).
  - Real-time slot availability checking for specific dates.
  - Automatic collision prevention ensuring zero overlapping approved bookings.
  - Multi-state request lifecycle (`PENDING` $\to$ `APPROVED` / `REJECTED` / `CANCELLED`).
  - Booking cancellation workflow for students.
  - Administrative review queue with custom remark inputs.

- **Reporting & Operational Analytics Module:**
  - Master booking archive with multi-criteria filtering (by status, date, or resource ID).
  - User accounts registry for administrative oversight.
  - System summary dashboard detailing total users, facility counts, and status-wise booking metrics.
