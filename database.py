import sqlite3
import os
import json
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rojgar_portal.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Admin Users Table (Secure authentication)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT DEFAULT 'Portal Administrator',
        failed_attempts INTEGER DEFAULT 0,
        locked_until REAL DEFAULT 0,
        created_at REAL NOT NULL,
        last_login REAL
    )
    """)

    # 2. Session Tokens Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        admin_id INTEGER NOT NULL,
        expires_at REAL NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY (admin_id) REFERENCES admins (id)
    )
    """)

    # 3. Blogs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blogs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        feed_url TEXT NOT NULL,
        category TEXT NOT NULL,
        blogger_blog_id TEXT,
        description TEXT,
        total_posts INTEGER DEFAULT 0,
        total_views INTEGER DEFAULT 0,
        last_synced REAL
    )
    """)

    # 4. Govt Job Alerts Table (Scraped radar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        department TEXT,
        category TEXT NOT NULL, -- 'general' or 'krishi'
        vacancies TEXT,
        qualification TEXT,
        last_date TEXT,
        source_name TEXT,
        source_url TEXT UNIQUE,
        notification_pdf TEXT,
        summary TEXT,
        is_read INTEGER DEFAULT 0,
        is_converted INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        source_pub_date TEXT
    )
    """)

    try:
        cursor.execute("ALTER TABLE job_alerts ADD COLUMN source_pub_date TEXT")
    except Exception:
        pass

    # 5. Blog Posts Table (Local drafts and synced posts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blog_key TEXT NOT NULL,
        title TEXT NOT NULL,
        content_html TEXT NOT NULL,
        labels TEXT,
        blogger_post_id TEXT,
        url TEXT,
        status TEXT DEFAULT 'draft', -- 'draft', 'published'
        views INTEGER DEFAULT 0,
        published_at REAL,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    )
    """)

    # 6. Activity / Security Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_username TEXT,
        action TEXT NOT NULL,
        ip_address TEXT,
        details TEXT,
        created_at REAL NOT NULL
    )
    """)

    # 7. System Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Seed User's 2 Blogs with Blogger IDs
    blogs_seed = [
        (
            "rojgar",
            "Rojgar Notification",
            "https://rojgarnotifications.blogspot.com/",
            "https://rojgarnotifications.blogspot.com/feeds/posts/default?alt=json",
            "general",
            "7975521606837664007",
            "Central & State Government Jobs, Admit Cards, Answer Keys & Results"
        ),
        (
            "krishi",
            "Krishi Rojgar",
            "https://krishirojgar.blogspot.com/",
            "https://krishirojgar.blogspot.com/feeds/posts/default?alt=json",
            "krishi",
            "5186771250163328966",
            "Agriculture Jobs, KVK, ICAR, Horticulture, Pashupalan & Kisan Yojna"
        )
    ]

    for b in blogs_seed:
        cursor.execute("""
        INSERT OR IGNORE INTO blogs (key_name, name, url, feed_url, category, blogger_blog_id, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, b)
        # Update blog ID in case it was created earlier as blank
        cursor.execute("""
        UPDATE blogs SET blogger_blog_id = ? WHERE key_name = ?
        """, (b[5], b[0]))

    # Seed User's Blogger API Key
    cursor.execute("""
    INSERT OR REPLACE INTO settings (key, value)
    VALUES ('blogger_api_key', 'AIzaSyAY9BmHa8JKS-1kjrhcABy4568xHJMisM0')
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
