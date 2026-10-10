// Global App State
let activeTab = "jobs";
let activeBlogKey = "rojgar";
let activeCategory = "all";
let cachedJobs = [];
let cachedPosts = [];

const BLOG_DATA = {
    rojgar: {
        id: "7975521606837664007",
        name: "Rojgar Notification",
        url: "https://rojgarnotifications.blogspot.com/"
    },
    krishi: {
        id: "5186771250163328966",
        name: "Krishi Rojgar",
        url: "https://krishirojgar.blogspot.com/"
    }
};

// PWA Install Prompt Handler
let deferredPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const btn = document.getElementById("installPwaBtn");
    if (btn) btn.classList.remove("hidden");
});

function installPwaApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                showToast("App install successful!", "success");
            }
            deferredPrompt = null;
        });
    } else {
        showToast("Phone ke browser menu (⋮) par tap karke 'Add to Home screen' ya 'Install app' chunein.", "info");
    }
}

// Register Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js').catch(err => console.log('SW reg error', err));
    });
}

// Initialize on Load (No Login Needed)
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    initBackPressHandler();
    loadAllJobs();
    loadBlogPosts();
    updateBlogStatsLink();
});

// Hardware / Gesture Back Button Interceptor for Native App Exit Popup
function initBackPressHandler() {
    history.pushState({ app: 'main' }, '', '');

    window.addEventListener('popstate', (e) => {
        const modal = document.getElementById('exitModal');
        if (modal && !modal.classList.contains('hidden')) {
            dismissExitModal();
            return;
        }

        if (activeTab === 'views') {
            switchTab('jobs');
            history.pushState({ app: 'main' }, '', '');
            return;
        }

        showExitModal();
    });
}

function showExitModal() {
    const modal = document.getElementById('exitModal');
    if (modal) {
        modal.classList.remove('hidden');
        lucide.createIcons();
    }
}

function dismissExitModal() {
    const modal = document.getElementById('exitModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    history.pushState({ app: 'main' }, '', '');
}

function confirmExitApp() {
    dismissExitModal();
    showToast("Closing app...", "info");
    try {
        window.close();
    } catch (e) {}
    setTimeout(() => {
        window.location.href = "about:blank";
    }, 400);
}

// Automatically Hide Mobile Browser URL Bar on User Touch/Scroll
let hasAutoHiddenUrl = false;
function triggerAutoHideUrlBar() {
    if (hasAutoHiddenUrl) return;
    hasAutoHiddenUrl = true;

    // Small scroll to hide mobile Chrome's address bar
    setTimeout(() => {
        window.scrollTo(0, 1);
    }, 150);

    // If supported, request fullscreen on mobile to completely hide browser bar
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
    }
}

window.addEventListener('touchstart', triggerAutoHideUrlBar, { once: true, passive: true });
window.addEventListener('click', triggerAutoHideUrlBar, { once: true, passive: true });

// 1. NAVIGATION & TABS
function switchTab(tabId) {
    activeTab = tabId;
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".nav-btn").forEach(el => el.classList.remove("active"));

    const targetSection = document.getElementById(`tab-${tabId}`);
    const targetNav = document.getElementById(`nav-${tabId}`);
    if (targetSection) targetSection.classList.remove("hidden");
    if (targetNav) targetNav.classList.add("active");

    // Sync mobile bottom navigation
    ['jobs', 'views'].forEach(id => {
        const mob = document.getElementById(`mobnav-${id}`);
        if (mob) {
            if (id === tabId) {
                mob.classList.remove('text-slate-400');
                mob.classList.add('text-blue-500');
            } else {
                mob.classList.remove('text-blue-500');
                mob.classList.add('text-slate-400');
            }
        }
    });

    if (tabId === "views") {
        loadBlogPosts();
    } else {
        loadAllJobs();
    }
    lucide.createIcons();
}

function setActiveBlog(blogKey) {
    activeBlogKey = blogKey;
    const rojgarBtn = document.getElementById("btn-blog-rojgar");
    const krishiBtn = document.getElementById("btn-blog-krishi");
    const titleDisplay = document.getElementById("viewsBlogTitleDisplay");

    if (blogKey === "rojgar") {
        rojgarBtn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-blue-600 text-white shadow-sm";
        krishiBtn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white";
        if (titleDisplay) titleDisplay.textContent = "Rojgar Notification Posts (व्यूज रिपोर्ट)";
    } else {
        krishiBtn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition bg-emerald-600 text-white shadow-sm";
        rojgarBtn.className = "px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition text-slate-400 hover:text-white";
        if (titleDisplay) titleDisplay.textContent = "Krishi Rojgar Posts (व्यूज रिपोर्ट)";
    }

    updateBlogStatsLink();
    loadBlogPosts();
}

function updateBlogStatsLink() {
    const statsBtn = document.getElementById("btnBloggerStatsLink");
    if (statsBtn && BLOG_DATA[activeBlogKey]) {
        statsBtn.href = `https://www.blogger.com/blog/stats/overview/${BLOG_DATA[activeBlogKey].id}`;
    }
}

// 2. GOVT JOB RADAR & CATEGORY FILTERING
async function loadAllJobs() {
    try {
        const res = await fetch("/api/jobs");
        const data = await res.json();
        if (data.success) {
            cachedJobs = data.jobs;
            document.getElementById("badgeJobCount").textContent = `${cachedJobs.length} Jobs`;
            renderJobCards(cachedJobs);
        }
    } catch (err) {
        console.error("Job load error", err);
    }
}

function selectCategory(cat) {
    activeCategory = cat;
    
    // Update active pill style
    document.querySelectorAll(".cat-pill").forEach(btn => {
        btn.classList.remove("active", "bg-blue-600", "text-white", "shadow-md");
        btn.classList.add("bg-slate-900", "text-slate-300");
    });

    const activeBtn = document.getElementById(`cat-${cat}`);
    if (activeBtn) {
        activeBtn.classList.remove("bg-slate-900", "text-slate-300");
        activeBtn.classList.add("active", "bg-blue-600", "text-white", "shadow-md");
    }

    filterJobs();
}

let jobSearchTimeout = null;
function debounceJobSearch() {
    clearTimeout(jobSearchTimeout);
    jobSearchTimeout = setTimeout(() => {
        filterJobs();
    }, 200);
}

function filterJobs() {
    const q = document.getElementById("jobSearchInput").value.toLowerCase().trim();
    let filtered = cachedJobs;

    // Filter by Category
    if (activeCategory !== "all") {
        if (activeCategory === "latest") {
            filtered = cachedJobs.slice(0, 40);
        } else {
            filtered = cachedJobs.filter(j => j.category === activeCategory);
        }
    }

    // Filter by Search Query
    if (q) {
        filtered = filtered.filter(j => 
            j.title.toLowerCase().includes(q) ||
            (j.department && j.department.toLowerCase().includes(q)) ||
            (j.qualification && j.qualification.toLowerCase().includes(q))
        );
    }

    renderJobCards(filtered);
}

function getCategoryColor(cat) {
    switch (cat) {
        case 'police': return 'bg-amber-950/80 text-amber-400 border-amber-500/30';
        case 'ssc': return 'bg-blue-950/80 text-blue-400 border-blue-500/30';
        case 'navy': return 'bg-cyan-950/80 text-cyan-400 border-cyan-500/30';
        case 'railway': return 'bg-purple-950/80 text-purple-400 border-purple-500/30';
        case 'bank': return 'bg-indigo-950/80 text-indigo-400 border-indigo-500/30';
        case 'krishi': return 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30';
        case 'teaching': return 'bg-rose-950/80 text-rose-400 border-rose-500/30';
        default: return 'bg-slate-800 text-slate-300 border-slate-700';
    }
}

function getCategoryLabel(cat) {
    switch (cat) {
        case 'police': return '👮 Police Bharti';
        case 'ssc': return '🏛️ SSC Recruitment';
        case 'navy': return '⚓ Navy / Defence';
        case 'railway': return '🚆 Railway RRB';
        case 'bank': return '🏦 Bank Bharti';
        case 'krishi': return '🌾 Krishi / Agriculture';
        case 'teaching': return '📚 Teaching Bharti';
        default: return '🔥 Latest Govt Job';
    }
}

function renderJobCards(jobs) {
    const container = document.getElementById("jobsContainer");
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="col-span-full py-12 text-center text-slate-500">
                <i data-lucide="inbox" class="w-10 h-10 mx-auto mb-2 opacity-50"></i>
                <p>Is category me abhi koi job alert nahi mili.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = jobs.map(j => {
        const badgeStyle = getCategoryColor(j.category);
        const catName = getCategoryLabel(j.category);

        // Format exact Post Date & Time
        const postDate = j.created_at ? new Date(j.created_at * 1000) : new Date();
        const dateStr = postDate.toLocaleDateString('hi-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        const timeStr = postDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

        return `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition duration-200">
            <div>
                <div class="flex items-center justify-between gap-2 mb-2">
                    <span class="px-2.5 py-1 rounded-full text-[11px] font-bold border ${badgeStyle}">
                        ${catName}
                    </span>
                    <span class="text-[11px] text-red-400 font-bold bg-red-950/60 px-2 py-0.5 rounded-md border border-red-500/20">
                        ${j.vacancies}
                    </span>
                </div>

                <!-- Exact Website Post Date & Time Badge -->
                <div class="flex items-center gap-1.5 text-[11px] text-emerald-400 font-bold bg-emerald-950/60 border border-emerald-500/25 px-2.5 py-1 rounded-lg w-fit mb-2">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 text-emerald-400"></i>
                    <span>वेबसाइट पोस्ट तिथि: ${j.source_pub_date || `${dateStr} at ${timeStr}`}</span>
                </div>

                <h4 class="font-bold text-white text-sm line-clamp-2 mb-2 leading-snug" title="${j.title}">
                    ${j.title}
                </h4>

                <div class="space-y-1 text-xs text-slate-400 border-t border-slate-800/80 pt-2.5 mt-2.5">
                    <p><strong class="text-slate-300">Department:</strong> ${j.department}</p>
                    <p><strong class="text-slate-300">Qualification:</strong> ${j.qualification}</p>
                    <p class="text-[11px] text-slate-500">Source: <span class="text-slate-300 font-semibold">${j.source_name}</span></p>
                </div>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                <button onclick="copyToClipboard('${j.source_url}')" class="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition text-xs flex items-center gap-1" title="Copy Link">
                    <i data-lucide="copy" class="w-3.5 h-3.5"></i> Copy Link
                </button>

                <a href="${j.source_url}" target="_blank" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-md flex items-center gap-1.5 transition">
                    <span>View / Apply Link</span>
                    <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                </a>
            </div>
        </div>
        `;
    }).join("");

    lucide.createIcons();
}

// 3. BLOG POST VIEWS TRACKER
async function loadBlogPosts() {
    try {
        const res = await fetch(`/api/blogs/${activeBlogKey}/posts`);
        const data = await res.json();
        if (data.success) {
            cachedPosts = data.posts;
            document.getElementById("viewsTotalPosts").textContent = `${cachedPosts.length} Posts`;
            renderPostsViewsList(cachedPosts);
        }
    } catch (err) {
        console.error("Posts fetch error", err);
    }
}

function filterPostsSearch() {
    const q = document.getElementById("postSearchInput").value.toLowerCase().trim();
    if (!q) {
        renderPostsViewsList(cachedPosts);
        return;
    }
    const filtered = cachedPosts.filter(p => p.title.toLowerCase().includes(q) || (p.labels && p.labels.toLowerCase().includes(q)));
    renderPostsViewsList(filtered);
}

function renderPostsViewsList(posts) {
    const container = document.getElementById("postsListContainer");
    if (!posts || posts.length === 0) {
        container.innerHTML = `
            <div class="py-12 text-center text-slate-500 bg-slate-900 border border-slate-800 rounded-2xl">
                <i data-lucide="file-question" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
                <p>Is blog ke posts load nahi huye. "Refresh" par click karein.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = posts.map(p => {
        const dateStr = p.updated_at ? new Date(p.updated_at * 1000).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Live';
        const viewsCount = p.views || 0;

        return `
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-700 transition">
            <div class="space-y-1.5 max-w-2xl">
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-950 text-blue-400 border border-blue-500/20">
                        ${p.labels ? p.labels.split(',')[0] : 'General'}
                    </span>
                    <span class="text-[11px] text-slate-500">${dateStr}</span>
                </div>
                <h4 class="font-bold text-white text-sm sm:text-base line-clamp-2">
                    ${p.title}
                </h4>
                <div class="flex items-center gap-4 text-xs text-slate-400 pt-1">
                    <span class="flex items-center gap-1 text-emerald-400 font-semibold">
                        <i data-lucide="check-circle" class="w-3.5 h-3.5"></i> Published Live on Blogger
                    </span>
                </div>
            </div>

            <!-- Views Counter & Direct Link Actions -->
            <div class="flex items-center gap-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800">
                <!-- Views Display Badge -->
                <div onclick="promptUpdateViews(${p.id}, ${viewsCount})" class="cursor-pointer px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl flex items-center gap-2 hover:border-blue-500 transition" title="Click to update views manually">
                    <i data-lucide="eye" class="w-4 h-4 text-emerald-400"></i>
                    <div>
                        <span class="text-[10px] text-slate-500 block leading-none">Views</span>
                        <span class="text-sm font-bold text-white">${viewsCount > 0 ? viewsCount : 'View Data'}</span>
                    </div>
                </div>

                <!-- Open Live Post Button -->
                <a href="${p.url}" target="_blank" class="p-2.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-xl border border-blue-500/30 transition flex items-center gap-1.5 text-xs font-semibold" title="View Post on Blogger">
                    <span>Open Post</span>
                    <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                </a>
            </div>
        </div>
        `;
    }).join("");

    lucide.createIcons();
}

async function promptUpdateViews(postId, currentViews) {
    const input = prompt("Is post ke kitne views record karne hain? (Enter views count):", currentViews || "100");
    if (input !== null && !isNaN(input)) {
        const views = parseInt(input);
        try {
            await fetch(`/api/posts/${postId}/views`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ views: views })
            });
            showToast("Views counter updated!", "success");
            loadBlogPosts();
        } catch (e) {
            showToast("Failed to update views", "error");
        }
    }
}

// 4. REFRESH DATA
async function refreshCurrentData() {
    const btn = document.getElementById("refreshBtn");
    btn.disabled = true;
    btn.innerHTML = `<span class="inline-block animate-spin mr-1">⌛</span> Syncing...`;

    try {
        if (activeTab === "jobs") {
            await fetch("/api/jobs/scrape", { method: "POST" });
            await loadAllJobs();
            showToast("Govt jobs refreshed from SarkariResult & Official Portals!", "success");
        } else {
            await fetch(`/api/blogs/${activeBlogKey}/sync`, { method: "POST" });
            await loadBlogPosts();
            showToast("Blogger posts & data synchronized!", "success");
        }
    } catch (err) {
        showToast("Sync error. Please check connection.", "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span>Refresh</span>`;
        lucide.createIcons();
    }
}

// 5. HELPERS
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    
    let bg = "bg-slate-900 border-slate-700 text-slate-200";
    let icon = "info";
    if (type === "success") {
        bg = "bg-emerald-950/90 border-emerald-500/40 text-emerald-200";
        icon = "check-circle";
    } else if (type === "error") {
        bg = "bg-red-950/90 border-red-500/40 text-red-200";
        icon = "alert-circle";
    }

    toast.className = `p-3 rounded-xl border shadow-xl flex items-center gap-2.5 text-xs font-medium max-w-sm pointer-events-auto transition duration-300 ${bg}`;
    toast.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4 shrink-0"></i><span>${message}</span>`;
    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Official Job Link copied to clipboard!", "success");
    });
}
