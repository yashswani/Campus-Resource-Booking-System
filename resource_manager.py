"""
Campus Resource Booking System - Resource Manager
=================================================

Functional Module: Resource Inventory Management (CRUD)
Non-Functional Requirements Addressed:
- Security: Parameterized queries, validation of capacity and status enums.
- Reliability: Foreign key integrity checks preventing orphaned records on deletion.
- Performance: SQL filtering, indexed category lookups, optimized query execution.
- Maintainability: Reusable CRUD methods returning typed Resource domain models.
"""

import sqlite3
from typing import List, Optional, Tuple
from database import db
from models import Resource

VALID_CATEGORIES = ["Auditorium", "Lab", "Classroom", "Equipment", "Sports Facility", "Other"]
VALID_STATUSES = ["Available", "Under Maintenance", "Decommissioned"]


class ResourceManager:
    """Handles CRUD operations, inventory search, and availability checks for campus facilities."""

    @staticmethod
    def add_resource(
        name: str,
        category: str,
        capacity: int,
        location: str,
        status: str = "Available",
        description: str = ""
    ) -> Tuple[bool, str, Optional[int]]:
        """Adds a new resource to the campus inventory (Admin action)."""
        name = name.strip()
        category = category.strip().title()
        location = location.strip()
        status = status.strip().title()

        if not name:
            return False, "Resource name cannot be empty.", None

        if category not in VALID_CATEGORIES:
            return False, f"Invalid category. Allowed: {', '.join(VALID_CATEGORIES)}", None

        if capacity < 0:
            return False, "Capacity must be a non-negative integer.", None

        if not location:
            return False, "Location cannot be empty.", None

        if status not in VALID_STATUSES:
            return False, f"Invalid status. Allowed: {', '.join(VALID_STATUSES)}", None

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO resources (name, category, capacity, location, status, description)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (name, category, capacity, location, status, description.strip()))
                conn.commit()
                resource_id = cursor.lastrowid
                return True, f"Resource '{name}' (ID: {resource_id}) created successfully.", resource_id
        except sqlite3.Error as e:
            return False, f"Database error creating resource: {e}", None

    @staticmethod
    def get_all_resources(
        category_filter: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> List[Resource]:
        """Retrieves all resources, with optional category and status filtering."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT resource_id, name, category, capacity, location, status, description FROM resources WHERE 1=1"
                params = []

                if category_filter:
                    query += " AND LOWER(category) = LOWER(?)"
                    params.append(category_filter.strip())

                if status_filter:
                    query += " AND LOWER(status) = LOWER(?)"
                    params.append(status_filter.strip())

                query += " ORDER BY resource_id ASC;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    Resource(
                        resource_id=r["resource_id"],
                        name=r["name"],
                        category=r["category"],
                        capacity=r["capacity"],
                        location=r["location"],
                        status=r["status"],
                        description=r["description"]
                    )
                    for r in rows
                ]
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return []

    @staticmethod
    def get_resource_by_id(resource_id: int) -> Optional[Resource]:
        """Fetches a specific resource by its ID."""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT resource_id, name, category, capacity, location, status, description
                    FROM resources WHERE resource_id = ?;
                """, (resource_id,))
                row = cursor.fetchone()
                if row:
                    return Resource(
                        resource_id=row["resource_id"],
                        name=row["name"],
                        category=row["category"],
                        capacity=row["capacity"],
                        location=row["location"],
                        status=row["status"],
                        description=row["description"]
                    )
                return None
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return None

    @staticmethod
    def search_resources(query_str: str) -> List[Resource]:
        """Searches resources matching keyword in name, location, category, or description."""
        query_str = query_str.strip()
        if not query_str:
            return ResourceManager.get_all_resources()

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                search_pattern = f"%{query_str}%"
                cursor.execute("""
                    SELECT resource_id, name, category, capacity, location, status, description
                    FROM resources
                    WHERE name LIKE ? OR location LIKE ? OR category LIKE ? OR description LIKE ?
                    ORDER BY resource_id ASC;
                """, (search_pattern, search_pattern, search_pattern, search_pattern))
                rows = cursor.fetchall()
                return [
                    Resource(
                        resource_id=r["resource_id"],
                        name=r["name"],
                        category=r["category"],
                        capacity=r["capacity"],
                        location=r["location"],
                        status=r["status"],
                        description=r["description"]
                    )
                    for r in rows
                ]
        except sqlite3.Error as e:
            print(f"[Database Error]: {e}")
            return []

    @staticmethod
    def update_resource(
        resource_id: int,
        name: Optional[str] = None,
        category: Optional[str] = None,
        capacity: Optional[int] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Updates attributes of an existing resource."""
        res = ResourceManager.get_resource_by_id(resource_id)
        if not res:
            return False, f"Resource with ID {resource_id} does not exist."

        updated_name = name.strip() if name is not None and name.strip() else res.name
        updated_cat = category.strip().title() if category is not None and category.strip() else res.category
        updated_cap = capacity if capacity is not None else res.capacity
        updated_loc = location.strip() if location is not None and location.strip() else res.location
        updated_status = status.strip().title() if status is not None and status.strip() else res.status
        updated_desc = description.strip() if description is not None else res.description

        if updated_cat not in VALID_CATEGORIES:
            return False, f"Invalid category. Allowed: {', '.join(VALID_CATEGORIES)}"

        if updated_cap < 0:
            return False, "Capacity must be a non-negative integer."

        if updated_status not in VALID_STATUSES:
            return False, f"Invalid status. Allowed: {', '.join(VALID_STATUSES)}"

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE resources
                    SET name = ?, category = ?, capacity = ?, location = ?, status = ?, description = ?
                    WHERE resource_id = ?;
                """, (updated_name, updated_cat, updated_cap, updated_loc, updated_status, updated_desc, resource_id))
                conn.commit()
                return True, f"Resource #{resource_id} ('{updated_name}') updated successfully."
        except sqlite3.Error as e:
            return False, f"Database error updating resource: {e}"

    @staticmethod
    def delete_resource(resource_id: int) -> Tuple[bool, str]:
        """
        Deletes a resource.
        Reliability check: Prevents deletion if active or pending bookings exist.
        """
        res = ResourceManager.get_resource_by_id(resource_id)
        if not res:
            return False, f"Resource with ID {resource_id} not found."

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # Check for existing bookings
                cursor.execute("""
                    SELECT COUNT(*) as count FROM bookings
                    WHERE resource_id = ? AND status IN ('PENDING', 'APPROVED');
                """, (resource_id,))
                active_count = cursor.fetchone()["count"]

                if active_count > 0:
                    return False, (
                        f"Cannot delete resource #{resource_id} ('{res.name}'). "
                        f"There are {active_count} active/pending bookings associated with it. "
                        "Please cancel or resolve them first, or set status to 'Decommissioned'."
                    )

                cursor.execute("DELETE FROM resources WHERE resource_id = ?;", (resource_id,))
                conn.commit()
                return True, f"Resource #{resource_id} ('{res.name}') has been deleted."
        except sqlite3.IntegrityError as e:
            return False, f"Integrity constraint prevented deletion: {e}"
        except sqlite3.Error as e:
            return False, f"Database error during deletion: {e}"
