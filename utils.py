import logging
from flask import flash

# ================================================
# LOGGING SETUP
# ================================================
# Configure standard Python logging for production-ready structured logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BloodBank')

# ================================================
# VALIDATION UTILS
# ================================================
def sanitize_input(value):
    """Strips whitespace from string inputs; returns None if empty."""
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return value

def validate_enum(value, valid_set, default=None):
    """Validates that a value exists in a set; returns default if invalid."""
    if value in valid_set:
        return value
    return default

def parse_positive_int(value, default=None):
    """Parses a value into a positive integer, or returns default."""
    try:
        num = int(value)
        if num > 0:
            return num
    except (ValueError, TypeError):
        pass
    return default

# ================================================
# DATABASE UTILS
# ================================================
class DBHelper:
    """
    A helper class to encapsulate database operations, reducing duplicated
    try-except blocks across the application.
    """
    def __init__(self, mysql):
        self.mysql = mysql

    def fetch_one(self, query, params=None):
        cur = self.mysql.connection.cursor()
        try:
            cur.execute(query, params or ())
            return cur.fetchone()
        except Exception as e:
            logger.error(f"DB Error (fetch_one): {e} | Query: {query}")
            raise
        finally:
            cur.close()

    def fetch_all(self, query, params=None):
        cur = self.mysql.connection.cursor()
        try:
            cur.execute(query, params or ())
            return cur.fetchall()
        except Exception as e:
            logger.error(f"DB Error (fetch_all): {e} | Query: {query}")
            raise
        finally:
            cur.close()

    def safe_execute(self, query, params=None, success_msg=None, error_msg="A database error occurred."):
        """
        Executes an INSERT, UPDATE, or DELETE query safely.
        Automatically handles commits, rollbacks, and flashing messages.
        Returns True if successful, False otherwise.
        """
        cur = self.mysql.connection.cursor()
        try:
            logger.info(f"Executing Query: {query.strip()[:50]}... | Params: {params}")
            cur.execute(query, params or ())
            self.mysql.connection.commit()
            if success_msg:
                flash(success_msg, 'success')
            return True
        except Exception as e:
            logger.error(f"DB Error (safe_execute): {e} | Query: {query} | Params: {params}")
            self.mysql.connection.rollback()
            flash(error_msg, 'danger')
            return False
        finally:
            cur.close()
