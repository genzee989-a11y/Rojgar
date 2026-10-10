# 🚀 Rojgar & Krishi - Blogger Command Center

Yeh ek centralized **Admin Command Center aur Govt Job Radar Application** hai jo specially aapke dono blogs ke liye design kiya gaya hai:
1. **[Rojgar Notification](https://rojgarnotifications.blogspot.com/)** (General Sarkari Naukri, SSC, UPSC, Railway, Defence)
2. **[Krishi Rojgar](https://krishirojgar.blogspot.com/)** (Krishi Vibhag, KVK, ICAR, Horticulture, Kisan Yojna)

---

## 🌟 Key Features (खासियतें)

### 1. 🛡️ High-Security Admin Authentication (Anti-Hack Shield)
- **256-bit PBKDF2 Password Hashing**: Passwords ko 100,000 salt iterations ke sath encrypt kiya jata hai.
- **Anti-Brute Force Protection**: Lagataar 5 galat password attempts ke baad system 15 minute ke liye account auto-lock kar deta hai.
- **Session Tokens**: 24-hour cryptographically secure session tokens.
- **Credentials Manager**: Settings tab se aap kabhi bhi apna username aur password badal sakte hain.

### 2. 📡 Real-Time Govt Job Radar (ऑटोमेटिक जॉब अलर्ट्स)
- Sarkari job notification portals aur RSS feeds se latest jobs auto-fetch karta hai.
- **Smart Category Filtering**:
  - `General Jobs` -> Seedha Rojgar Notification ke liye classify karta hai.
  - `Krishi & Agriculture Jobs` -> Seedha Krishi Rojgar ke liye classify karta hai.
- **"⚡ 1-Click Draft" Button**: Job alert par click karte hi pura structured blog post (Hindi + English headings, dates table, qualification, official apply link) taiyar ho jata hai!

### 3. ✍️ Professional Post Studio (WYSIWYG + HTML Editor)
- High-CTR Responsive Post Generator:
  - Header & Summary
  - Overview Key Highlights Table
  - Eligibility Criteria (Age Limit & Education)
  - Step-by-Step How to Apply (आवेदन कैसे करें)
  - **Important Links Box**: Styled Download Notification & Apply Online Buttons
- **1-Click "Copy Blogger HTML"**: Copy karke Blogger post editor me paste karein aur publish karein.

### 4. 📑 Posts & Links Tracker
- Dono blogs ke sabhi live posts aur links ko sync karta hai.
- Ek click me link copy karein aur social media / WhatsApp / Telegram par share karein.

---

## 🔑 Login Credentials (डिफ़ॉल्ट लॉगिन विवरण)

- **Login URL**: `http://127.0.0.1:8000`
- **Username**: `admin`
- **Password**: `admin@Rojgar2026`

> **Note**: Pehli baar login karne ke baad **Admin Security** tab me jakar apna naya secret password set kar lein.

---

## ⚡ How to Run (कैसे चलाएं)

### Method 1: 1-Click Launch (Recommended for Windows)
`run_app.bat` file par double-click karein. Server apne aap start ho jayega aur aapka browser dashboard open kar dega.

### Method 2: Command Line
```powershell
cd C:\Users\Admin\.gemini\antigravity\scratch\rojgar_portal_app
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Browser me open karein: `http://127.0.0.1:8000`
