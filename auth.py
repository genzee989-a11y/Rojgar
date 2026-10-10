import hashlib
import os
import secrets
import time
from database import get_db

ITERATIONS = 100000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes lockout
SESSION_DURATION_SECONDS = 86400  # 24 hours

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hashes a password securely using PBKDF2-HMAC-SHA256 with a unique cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )
    return key.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)

def ensure_default_admin():
    """Creates a default secure admin if none exists."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admins LIMIT 1")
    admin = cursor.fetchone()
    
    if not admin:
        default_user = "admin"
        default_pass = "admin@Rojgar2026"
        p_hash, salt = hash_password(default_pass)
        now = time.time()
        cursor.execute("""
        INSERT INTO admins (username, password_hash, salt, full_name, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (default_user, p_hash, salt, "Portal Master Admin", now))
        conn.commit()
        print(f"[SECURITY] Initial admin created: username='{default_user}', password='{default_pass}'")
    conn.close()

def authenticate_admin(username: str, password: str, ip_address: str = "127.0.0.1") -> tuple[bool, str, dict]:
    """
    Authenticates admin with anti-brute force protection.
    Returns: (success: bool, message: str, admin_info: dict)
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
    admin = cursor.fetchone()

    now = time.time()

    if not admin:
        # Avoid timing attacks by running a dummy hash
        hash_password("dummy_password", "dummy_salt")
        log_security_event(username, "FAILED_LOGIN_UNKNOWN_USER", ip_address, "User not found")
        conn.close()
        return False, "Invalid username or password", {}

    # Check lockout
    if admin["locked_until"] and admin["locked_until"] > now:
        remaining = int((admin["locked_until"] - now) / 60) + 1
        log_security_event(username, "LOCKED_LOGIN_ATTEMPT", ip_address, f"Account locked for {remaining} more mins")
        conn.close()
        return False, f"Account locked due to multiple failed attempts. Please try again after {remaining} minutes.", {}

    # Verify password
    if verify_password(password, admin["password_hash"], admin["salt"]):
        # Reset failed attempts and update last_login
        cursor.execute("""
        UPDATE admins 
        SET failed_attempts = 0, locked_until = 0, last_login = ? 
        WHERE id = ?
        """, (now, admin["id"]))
        
        # Create session token
        token = secrets.token_hex(32)
        expires_at = now + SESSION_DURATION_SECONDS
        cursor.execute("""
        INSERT INTO sessions (token, admin_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """, (token, admin["id"], expires_at, now))
        
        conn.commit()
        log_security_event(username, "SUCCESSFUL_LOGIN", ip_address, "Admin logged in successfully")
        
        admin_data = {
            "id": admin["id"],
            "username": admin["username"],
            "full_name": admin["full_name"],
            "token": token,
            "expires_at": expires_at
        }
        conn.close()
        return True, "Login successful", admin_data
    else:
        # Increment failed attempts
        failed = (admin["failed_attempts"] or 0) + 1
        locked_until = 0
        if failed >= MAX_FAILED_ATTEMPTS:
            locked_until = now + LOCKOUT_DURATION_SECONDS
            msg = f"Account locked for 15 minutes due to {MAX_FAILED_ATTEMPTS} incorrect attempts."
            action_name = "ACCOUNT_LOCKED"
        else:
            remaining_tries = MAX_FAILED_ATTEMPTS - failed
            msg = f"Invalid password. {remaining_tries} attempts remaining before account lockout."
            action_name = "FAILED_LOGIN"

        cursor.execute("""
        UPDATE admins 
        SET failed_attempts = ?, locked_until = ? 
        WHERE id = ?
        """, (failed, locked_until, admin["id"]))
        conn.commit()
        
        log_security_event(username, action_name, ip_address, f"Attempt #{failed}")
        conn.close()
        return False, msg, {}

def validate_session(token: str) -> dict | None:
    """Validates session token and returns admin profile if active."""
    if not token:
        return None
    conn = get_db()
    cursor = conn.cursor()
    now = time.time()
    
    cursor.execute("""
    SELECT a.id, a.username, a.full_name, s.expires_at 
    FROM sessions s
    JOIN admins a ON s.admin_id = a.id
    WHERE s.token = ? AND s.expires_at > ?
    """, (token, now))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"]
        }
    return None

def logout_session(token: str):
    """Deletes the active session token."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def change_admin_credentials(admin_id: int, old_password: str, new_username: str, new_password: str) -> tuple[bool, str]:
    """Allows admin to change username and password securely."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
    admin = cursor.fetchone()
    
    if not admin:
        conn.close()
        return False, "Admin not found"
        
    if not verify_password(old_password, admin["password_hash"], admin["salt"]):
        conn.close()
        return False, "Current password is incorrect"
        
    if len(new_password) < 8:
        conn.close()
        return False, "New password must be at least 8 characters long"
        
    new_hash, new_salt = hash_password(new_password)
    target_username = new_username.strip() if new_username.strip() else admin["username"]
    
    try:
        cursor.execute("""
        UPDATE admins 
        SET username = ?, password_hash = ?, salt = ? 
        WHERE id = ?
        """, (target_username, new_hash, new_salt, admin_id))
        conn.commit()
        log_security_event(target_username, "PASSWORD_CHANGED", "127.0.0.1", "Admin credentials updated")
        conn.close()
        return True, "Credentials updated successfully"
    except Exception as e:
        conn.close()
        return False, f"Could not update username: {str(e)}"

def log_security_event(username: str, action: str, ip: str, details: str):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO activity_logs (admin_username, action, ip_address, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (username, action, ip, details, time.time()))
        conn.commit()
        conn.close()
    except Exception:
        pass
