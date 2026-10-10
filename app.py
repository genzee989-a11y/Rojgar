import os
import time
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_db
from scraper import (
    seed_external_jobs,
    fetch_and_save_all_jobs,
    get_job_alerts
)
from blogger_client import sync_blog_posts

app = FastAPI(title="Rojgar & Krishi - Job Alerts & Views Portal", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    init_db()
    seed_external_jobs()
    # Trigger initial sync of user's 2 blogs
    try:
        sync_blog_posts("rojgar")
        sync_blog_posts("krishi")
    except Exception as e:
        print(f"[STARTUP] Sync error: {e}")
    # Also fetch fresh jobs
    try:
        fetch_and_save_all_jobs()
    except Exception as e:
        print(f"[STARTUP] Job fetch error: {e}")
    print("[SERVER] Portal started successfully with direct open access (No Login required).")

@app.get("/", response_class=HTMLResponse)
def index_page():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Loading Rojgar & Krishi Portal...</h1>")

# 1. BLOGS & POST VIEWS ROUTES (NO LOGIN REQUIRED)
@app.get("/api/blogs")
def get_blogs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blogs ORDER BY id ASC")
    blogs = [dict(b) for b in cursor.fetchall()]
    conn.close()
    return {"success": True, "blogs": blogs}

@app.post("/api/blogs/{blog_key}/sync")
def sync_blog(blog_key: str):
    result = sync_blog_posts(blog_key)
    return result

@app.get("/api/blogs/{blog_key}/posts")
def get_posts(blog_key: str, search: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM posts WHERE blog_key = ?"
    params = [blog_key]
    
    if search:
        query += " AND (title LIKE ? OR labels LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s])
        
    query += " ORDER BY id DESC LIMIT 100"
    cursor.execute(query, params)
    posts = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return {"success": True, "posts": posts}

class UpdateViewsRequest(BaseModel):
    views: int

@app.post("/api/posts/{post_id}/views")
def update_post_views(post_id: int, req: UpdateViewsRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET views = ? WHERE id = ?", (req.views, post_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Views updated"}

# 2. EXTERNAL GOVT JOB ALERTS ROUTES (SarkariResult, Police, SSC, Navy, etc.)
@app.get("/api/jobs")
def list_jobs(category: Optional[str] = None, search: Optional[str] = None):
    jobs = get_job_alerts(category=category, search=search, limit=120)
    return {"success": True, "jobs": jobs}

@app.post("/api/jobs/scrape")
def trigger_scrape():
    count = fetch_and_save_all_jobs()
    return {"success": True, "message": f"Updated latest jobs from SarkariResult & Official Portals ({count} new).", "count": count}

# 3. ANALYTICS & OVERVIEW (Total views, posts counts)
@app.get("/api/analytics/overview")
def get_analytics():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT key_name, name, total_posts, url, blogger_blog_id FROM blogs")
    blogs = [dict(b) for b in cursor.fetchall()]
    
    # Calculate views across posts
    cursor.execute("SELECT blog_key, SUM(views) as total_views, COUNT(*) as total_posts FROM posts GROUP BY blog_key")
    views_by_blog = {row["blog_key"]: {"views": row["total_views"] or 0, "posts": row["total_posts"]} for row in cursor.fetchall()}
    
    cursor.execute("SELECT COUNT(*) as count FROM job_alerts")
    total_jobs = cursor.fetchone()["count"]
    
    # Job count by category for badges
    categories = ['police', 'ssc', 'navy', 'railway', 'bank', 'krishi', 'teaching', 'latest']
    cat_counts = {}
    for c in categories:
        cursor.execute("SELECT COUNT(*) as count FROM job_alerts WHERE category = ?", (c,))
        cat_counts[c] = cursor.fetchone()["count"]
    
    conn.close()
    
    return {
        "success": True,
        "blogs": blogs,
        "views_by_blog": views_by_blog,
        "total_jobs": total_jobs,
        "cat_counts": cat_counts
    }
