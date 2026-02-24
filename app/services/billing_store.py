import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional


class BillingStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS billing_customers (
                    clerk_user_id TEXT PRIMARY KEY,
                    stripe_customer_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS billing_processed_events (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_customer_id(self, clerk_user_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT stripe_customer_id FROM billing_customers WHERE clerk_user_id = ?",
                (clerk_user_id,),
            ).fetchone()
        return row[0] if row else None

    def set_customer_id(self, clerk_user_id: str, stripe_customer_id: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO billing_customers (clerk_user_id, stripe_customer_id, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(clerk_user_id) DO UPDATE SET
                        stripe_customer_id = excluded.stripe_customer_id,
                        updated_at = excluded.updated_at
                    """,
                    (clerk_user_id, stripe_customer_id, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()

    def mark_event_started(self, event_id: str) -> bool:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO billing_processed_events (event_id, created_at)
                    VALUES (?, ?)
                    """,
                    (event_id, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
                return cursor.rowcount == 1

    def unmark_event(self, event_id: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM billing_processed_events WHERE event_id = ?",
                    (event_id,),
                )
                conn.commit()
