import urllib.request
import json
import time
from database import get_db

def get_blogger_api_key() -> str:
    """Retrieves the configured Blogger API Key from database settings."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'blogger_api_key'")
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row and row["value"] else ""

def sync_blog_posts(blog_key: str) -> dict:
    """
    Syncs posts and links for the blog using official Google Blogger API v3.
    Falls back to Blogger public JSON feed if API Key is not available.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blogs WHERE key_name = ?", (blog_key,))
    blog = cursor.fetchone()
    
    if not blog:
        conn.close()
        return {"success": False, "message": "Blog not found"}

    api_key = get_blogger_api_key()
    blog_id = blog["blogger_blog_id"]
    now = time.time()
    synced_count = 0

    # 1. ATTEMPT VIA OFFICIAL GOOGLE BLOGGER v3 API
    if api_key and blog_id:
        try:
            # First, fetch blog metadata (real-time total posts, pages, description)
            meta_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}?key={api_key}"
            meta_req = urllib.request.Request(meta_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(meta_req, timeout=10) as resp:
                meta_data = json.loads(resp.read().decode("utf-8"))
                total_posts = meta_data.get("posts", {}).get("totalItems", 0)
                blog_name = meta_data.get("name", blog["name"])

            # Second, fetch posts list
            posts_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts?key={api_key}&maxResults=50"
            posts_req = urllib.request.Request(posts_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(posts_req, timeout=12) as resp:
                posts_data = json.loads(resp.read().decode("utf-8"))
                items = posts_data.get("items", [])

                for item in items:
                    p_id = item.get("id", "")
                    title = item.get("title", "Untitled Post")
                    url = item.get("url", "")
                    labels = ", ".join(item.get("labels", []))
                    content_html = item.get("content", "")
                    
                    # Check if exists by blogger_post_id or URL
                    cursor.execute("SELECT id FROM posts WHERE blogger_post_id = ? OR url = ?", (p_id, url))
                    existing = cursor.fetchone()

                    if existing:
                        cursor.execute("""
                        UPDATE posts 
                        SET title = ?, labels = ?, content_html = ?, blogger_post_id = ?, updated_at = ?
                        WHERE id = ?
                        """, (title, labels, content_html, p_id, now, existing["id"]))
                    else:
                        cursor.execute("""
                        INSERT INTO posts (blog_key, title, content_html, labels, blogger_post_id, url, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?)
                        """, (blog_key, title, content_html, labels, p_id, url, now, now))
                        synced_count += 1

            # Update blog stats in DB
            cursor.execute("""
            UPDATE blogs 
            SET name = ?, total_posts = ?, last_synced = ? 
            WHERE key_name = ?
            """, (blog_name, total_posts, now, blog_key))

            conn.commit()
            conn.close()
            return {
                "success": True,
                "message": f"[Blogger v3 API] Synced {len(items)} posts for {blog_name} (Total: {total_posts}).",
                "total_posts": total_posts,
                "synced_count": synced_count,
                "source": "google_api_v3"
            }
        except Exception as e:
            print(f"[BLOGGER API ERROR] Falling back to feed: {e}")

    # 2. FALLBACK TO PUBLIC JSON FEED
    feed_url = f"{blog['url'].rstrip('/')}/feeds/posts/default?alt=json&max-results=50"
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8", errors="ignore"))
            feed = data.get("feed", {})
            total_results = feed.get("openSearch$totalResults", {}).get("$t", 0)
            entries = feed.get("entry", [])

            for entry in entries:
                title = entry.get("title", {}).get("$t", "Untitled Post")
                url = ""
                for link in entry.get("link", []):
                    if link.get("rel") == "alternate":
                        url = link.get("href", "")
                        break

                categories = [c.get("term") for c in entry.get("category", []) if c.get("term")]
                labels = ", ".join(categories)
                content_html = entry.get("content", {}).get("$t", "") or entry.get("summary", {}).get("$t", "")

                cursor.execute("SELECT id FROM posts WHERE url = ?", (url,))
                existing = cursor.fetchone()

                if existing:
                    cursor.execute("""
                    UPDATE posts 
                    SET title = ?, labels = ?, content_html = ?, updated_at = ? 
                    WHERE id = ?
                    """, (title, labels, content_html, now, existing["id"]))
                else:
                    cursor.execute("""
                    INSERT INTO posts (blog_key, title, content_html, labels, url, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'published', ?, ?)
                    """, (blog_key, title, content_html, labels, url, now, now))
                    synced_count += 1

            total_count = int(total_results) if total_results else len(entries)
            cursor.execute("""
            UPDATE blogs 
            SET total_posts = ?, last_synced = ? 
            WHERE key_name = ?
            """, (total_count, now, blog_key))

            conn.commit()
            conn.close()
            return {
                "success": True, 
                "message": f"Successfully synced {len(entries)} posts for {blog['name']}.",
                "total_posts": total_count,
                "synced_count": synced_count,
                "source": "public_feed"
            }
    except Exception as e:
        conn.close()
        return {"success": False, "message": f"Sync error: {str(e)}"}

# Alias for backwards compatibility
sync_blog_posts_from_feed = sync_blog_posts

def generate_seo_post_template(job_data: dict, blog_key: str = "rojgar") -> dict:
    """
    Generates a high-CTR, SEO-optimized Blogger post draft in Hindi & English,
    specially formatted with modern HTML tables, badges, and action buttons.
    """
    title = job_data.get("title", "New Govt Job Recruitment 2026")
    dept = job_data.get("department", "Government of India")
    vacancies = job_data.get("vacancies", "Various Posts")
    qualification = job_data.get("qualification", "Graduate / 10th / 12th Pass")
    last_date = job_data.get("last_date", "Check Notification")
    source_url = job_data.get("source_url", "#")
    notification_pdf = job_data.get("notification_pdf", source_url)
    summary = job_data.get("summary", "Official recruitment notification has been released.")

    # High-CTR SEO Title
    if blog_key == "krishi":
        seo_title = f"{title} | कृषि विभाग भर्ती 2026: कुल {vacancies}, योग्यता एवं आवेदन लिंक"
        target_label = "Krishi Bharti, Agriculture Jobs, KVK Recruitment, Govt Jobs"
    else:
        seo_title = f"{title} | सरकारी नौकरी भर्ती 2026: कुल {vacancies}, योग्यता, अंतिम तिथि व ऑनलाइन फॉर्म"
        target_label = "Govt Jobs 2026, Latest Recruitment, Sarkari Bharti, Rojgar Notification"

    content_html = f"""
<!-- POST HEADER -->
<div style="font-family: Arial, sans-serif; line-height: 1.8; color: #222;">
    <div style="background: linear-gradient(135deg, #1e3a8a, #2563eb); color: white; padding: 20px; border-radius: 10px; margin-bottom: 25px; text-align: center;">
        <h2 style="margin: 0; font-size: 22px; font-weight: bold; color: #ffffff;">{dept} Recruitment 2026</h2>
        <p style="margin: 8px 0 0 0; font-size: 15px; opacity: 0.95;">{vacancies} Vacancy Notification Released | All India Eligible Candidates</p>
    </div>

    <!-- INTRODUCTION -->
    <p style="font-size: 16px; margin-bottom: 20px;">
        <strong>{dept}</strong> ने योग्य और इच्छुक उम्मीदवारों से <strong>{title}</strong> के रिक्त पदों पर ऑनलाइन आवेदन आमंत्रित किए हैं। इस भर्ती के तहत कुल <strong>{vacancies}</strong> पदों पर नियुक्ति की जाएगी।
    </p>
    <p style="font-size: 15px; background: #f8fafc; border-left: 4px solid #2563eb; padding: 12px 15px; border-radius: 4px;">
        {summary}
    </p>

    <!-- KEY HIGHLIGHTS TABLE -->
    <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 30px;">
        📌 Recruitment 2026 Overview (महत्वपूर्ण विवरण)
    </h3>
    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;">
        <tbody>
            <tr style="background: #f1f5f9;">
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1; width: 35%;">विभाग का नाम (Organization)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;">{dept}</td>
            </tr>
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1;">पद का नाम (Post Name)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;">{title}</td>
            </tr>
            <tr style="background: #f1f5f9;">
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1;">कुल पद (Total Vacancies)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;"><span style="color: #dc2626; font-weight: bold;">{vacancies}</span></td>
            </tr>
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1;">शैक्षणिक योग्यता (Qualification)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;">{qualification}</td>
            </tr>
            <tr style="background: #f1f5f9;">
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1;">आवेदन की अंतिम तिथि (Last Date)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;"><span style="color: #dc2626; font-weight: bold;">{last_date}</span></td>
            </tr>
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #cbd5e1;">आवेदन मोड (Application Mode)</td>
                <td style="padding: 12px; border: 1px solid #cbd5e1;">Online (ऑनलाइन)</td>
            </tr>
        </tbody>
    </table>

    <!-- ELIGIBILITY CRITERIA -->
    <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">
        🎓 शैक्षणिक योग्यता एवं आयु सीमा (Eligibility & Age Limit)
    </h3>
    <ul style="line-height: 2; font-size: 15px;">
        <li><strong>शैक्षणिक योग्यता:</strong> उम्मीदवार के पास मान्यता प्राप्त बोर्ड/विश्वविद्यालय से {qualification} होना अनिवार्य है। विस्तृत जानकारी के लिए आधिकारिक नोटिफिकेशन देखें।</li>
        <li><strong>आयु सीमा:</strong> उम्मीदवार की न्यूनतम आयु 18 वर्ष और अधिकतम आयु पदानुसार निर्धारित है। आरक्षित वर्गों (SC/ST/OBC) को सरकार के नियमानुसार अधिकतम आयु सीमा में छूट दी जाएगी।</li>
    </ul>

    <!-- HOW TO APPLY -->
    <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 35px;">
        📝 ऑनलाइन आवेदन कैसे करें (How to Apply)
    </h3>
    <ol style="line-height: 2; font-size: 15px;">
        <li>सबसे पहले नीचे दिए गए <strong>"Official Notification"</strong> लिंक पर क्लिक करके नोटिफिकेशन ध्यानपूर्वक पढ़ें।</li>
        <li>इसके बाद <strong>"Apply Online"</strong> लिंक पर क्लिक करें।</li>
        <li>अपना रजिस्ट्रेशन करें (यदि नए यूजर हैं) और लॉग इन करें।</li>
        <li>आवेदन फॉर्म में मांगी गई सभी आवश्यक जानकारी ध्यानपूर्वक भरें।</li>
        <li>अपने दस्तावेज (फोटो, हस्ताक्षर, शैक्षणिक प्रमाणपत्र) अपलोड करें।</li>
        <li>लागू आवेदन शुल्क का भुगतान करें और फॉर्म फाइनल सबमिट करें।</li>
        <li>भविष्य के संदर्भ के लिए फाइनल प्रिंटआउट निकाल कर सुरक्षित रख लें।</li>
    </ol>

    <!-- IMPORTANT LINKS BOX -->
    <div style="background: #eff6ff; border: 2px dashed #3b82f6; border-radius: 12px; padding: 25px; margin: 40px 0; text-align: center;">
        <h3 style="color: #1e40af; margin-top: 0; font-size: 20px;">🔗 महत्वपूर्ण लिंक (Direct Useful Links)</h3>
        <p style="color: #4b5563; font-size: 14px; margin-bottom: 20px;">नीचे दिए गए आधिकारिक लिंक से आवेदन करें और नोटिफिकेशन डाउनलोड करें:</p>
        
        <div style="display: flex; flex-direction: column; gap: 12px; max-width: 480px; margin: 0 auto;">
            <a href="{notification_pdf}" target="_blank" rel="noopener noreferrer" style="background: #2563eb; color: #ffffff; padding: 12px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: block; box-shadow: 0 2px 4px rgba(37,99,235,0.3);">
                📥 Download Official Notification PDF
            </a>
            <a href="{source_url}" target="_blank" rel="noopener noreferrer" style="background: #16a34a; color: #ffffff; padding: 12px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 15px; display: block; box-shadow: 0 2px 4px rgba(22,163,74,0.3);">
                👉 Click Here to Apply Online
            </a>
        </div>
    </div>

    <!-- FOOTER / JOIN CHANNELS -->
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; text-align: center; font-size: 14px; color: #64748b;">
        <p style="margin: 0;">📢 रोज़गार एवं भर्ती की सबसे तेज़ और सटीक जानकारी के लिए इस वेबसाइट को बुकमार्क कर लें।</p>
    </div>
</div>
"""
    return {
        "title": seo_title,
        "content_html": content_html.strip(),
        "labels": target_label,
        "blog_key": blog_key
    }
