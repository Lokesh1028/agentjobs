/* AgentJobs — Frontend JavaScript */

const API_BASE = '/api/v1';

// ── Utility Functions ───────────────────────────

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function formatSalary(min, max) {
    if (min && max) return `₹${(min/1000).toFixed(0)}K - ₹${(max/1000).toFixed(0)}K/mo`;
    if (min) return `₹${(min/1000).toFixed(0)}K+/mo`;
    if (max) return `Up to ₹${(max/1000).toFixed(0)}K/mo`;
    return null;
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const days = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    return `${Math.floor(days / 30)} months ago`;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function getMatchClass(score) {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
}

// ── Auth Functions ──────────────────────────────

function authGetToken() {
    return localStorage.getItem('aj_token');
}

function authGetUser() {
    try {
        const u = localStorage.getItem('aj_user');
        return u ? JSON.parse(u) : null;
    } catch (e) { return null; }
}

function authSetSession(token, user) {
    localStorage.setItem('aj_token', token);
    localStorage.setItem('aj_user', JSON.stringify(user));
}

function authClearSession() {
    localStorage.removeItem('aj_token');
    localStorage.removeItem('aj_user');
}

async function authLogin(email, password) {
    const res = await fetch(API_BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    authSetSession(data.token, data.user);
    return data;
}

async function authSignup(params) {
    const res = await fetch(API_BASE + '/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Signup failed');
    }
    const data = await res.json();
    authSetSession(data.token, data.user);
    return data;
}

async function authLogout() {
    const token = authGetToken();
    if (token) {
        fetch(API_BASE + '/auth/logout', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
        }).catch(() => {});
    }
    authClearSession();
    window.location.href = '/';
}

async function authGetMe() {
    const token = authGetToken();
    if (!token) return null;
    try {
        const res = await fetch(API_BASE + '/auth/me', {
            headers: { 'Authorization': 'Bearer ' + token },
        });
        if (!res.ok) {
            if (res.status === 401) authClearSession();
            return null;
        }
        const user = await res.json();
        localStorage.setItem('aj_user', JSON.stringify(user));
        return user;
    } catch (e) { return null; }
}

function authGetHeaders() {
    const token = authGetToken();
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function renderAuthHeader() {
    const area = document.getElementById('auth-header-area');
    if (!area) return;

    const user = authGetUser();
    if (user) {
        const initials = (user.name || user.email || '?').charAt(0).toUpperCase();
        const displayName = user.name || user.email.split('@')[0];
        area.innerHTML = `
            <div class="auth-header">
                <div class="auth-user-info">
                    <div class="auth-avatar">${escapeHtml(initials)}</div>
                    <span>${escapeHtml(displayName)}</span>
                    ${user.role === 'admin' ? '<a href="/admin" style="font-size:11px;" class="tag orange">Admin</a>' : ''}
                </div>
                <button class="auth-logout-btn" onclick="authLogout()">Logout</button>
            </div>
        `;
    } else {
        area.innerHTML = `
            <div class="auth-header">
                <a href="/login" class="auth-login-btn">Login</a>
            </div>
        `;
    }
}

// ── API Functions ───────────────────────────────

async function apiGet(path, params = {}) {
    const url = new URL(API_BASE + path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v);
    });
    const headers = authGetHeaders();
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPost(path, body) {
    const headers = { 'Content-Type': 'application/json', ...authGetHeaders() };
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.json();
}

// ── Stats Loader (for landing page) ─────────────

async function loadStats() {
    try {
        const stats = await apiGet('/stats');
        const el = $('#stats-row');
        if (!el) return;
        el.innerHTML = `
            <div class="stat">
                <div class="stat-num">${stats.total_active_jobs.toLocaleString()}</div>
                <div class="stat-label">Active Jobs</div>
            </div>
            <div class="stat">
                <div class="stat-num">${stats.total_companies.toLocaleString()}</div>
                <div class="stat-label">Companies</div>
            </div>
            <div class="stat">
                <div class="stat-num">${stats.categories.length}</div>
                <div class="stat-label">Categories</div>
            </div>
        `;
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

// ── Job Card Renderer ───────────────────────────

function sourceLabel(src) {
    if (!src) return '';
    const labels = {remotive:'Remotive',jobicy:'Jobicy',themuse:'The Muse',arbeitnow:'Arbeitnow',linkedin:'LinkedIn',seed:'Offline'};
    const colors = {remotive:'#059669',jobicy:'#7c3aed',themuse:'#2563eb',arbeitnow:'#d97706',linkedin:'#0a66c2',seed:'#6b7280'};
    const name = labels[src] || src;
    const color = colors[src] || '#6b7280';
    return `<span class="source-badge" style="background:${color};color:#fff;font-size:10px;padding:2px 6px;border-radius:4px;margin-left:6px;">via ${name}</span>`;
}

function renderJobCard(job) {
    const salary = job.salary_range || formatSalary(job.salary_min, job.salary_max);
    const skills = (job.skills || []).slice(0, 5);
    const company = typeof job.company === 'object' ? job.company.name : job.company;
    const hasApplyUrl = job.apply_url && job.apply_url !== 'null' && job.apply_url !== '';
    const clickAction = hasApplyUrl ? `onclick="window.open('${escapeHtml(job.apply_url)}', '_blank')"` : '';
    const applyLabel = hasApplyUrl ? '🔗 Apply Now' : '📋 View Details';

    return `
        <div class="card job-card" ${clickAction} style="${hasApplyUrl ? 'cursor:pointer;' : 'cursor:default;opacity:0.9;'}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="job-title">${escapeHtml(job.title)}</div>
                    <div class="job-company">${escapeHtml(company)}${sourceLabel(job.source)}</div>
                </div>
                <span style="font-size:11px;white-space:nowrap;padding:4px 10px;border-radius:6px;font-weight:600;${hasApplyUrl ? 'background:var(--green,#059669);color:#fff;' : 'background:#e5e7eb;color:#374151;'}">${applyLabel}</span>
            </div>
            <div class="job-meta">
                ${job.location ? `<span class="tag">${escapeHtml(job.location)}</span>` : ''}
                ${job.location_type ? `<span class="tag blue">${escapeHtml(job.location_type)}</span>` : ''}
                ${job.employment_type ? `<span class="tag">${escapeHtml(job.employment_type)}</span>` : ''}
                ${job.category ? `<span class="tag">${escapeHtml(job.category)}</span>` : ''}
            </div>
            ${salary ? `<div class="job-salary">${escapeHtml(salary)}</div>` : ''}
            <div class="job-skills">
                ${skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')}
            </div>
            ${job.description_short ? `<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">${escapeHtml(job.description_short)}</p>` : ''}
            <div class="job-footer">
                <span>${job.experience || ''}</span>
                <span>${timeAgo(job.posted_at)}</span>
            </div>
        </div>
    `;
}

function renderMatchCard(job) {
    const scoreClass = getMatchClass(job.match_score);
    const hasApplyUrl = job.apply_url && job.apply_url !== 'null' && job.apply_url !== '';
    const clickAction = hasApplyUrl ? `onclick="window.open('${escapeHtml(job.apply_url)}', '_blank')"` : '';
    const applyLabel = hasApplyUrl ? '🔗 Apply Now' : '📋 View Details';

    return `
        <div class="card job-card" ${clickAction} style="${hasApplyUrl ? 'cursor:pointer;' : 'cursor:default;'}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                <div>
                    <div class="job-title">${escapeHtml(job.title)}</div>
                    <div class="job-company">${escapeHtml(job.company)}${typeof sourceLabel === 'function' ? sourceLabel(job.source) : ''}</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:10px;padding:3px 8px;border-radius:4px;font-weight:600;${hasApplyUrl ? 'background:var(--green,#059669);color:#fff;' : 'background:#e5e7eb;color:#374151;'}">${applyLabel}</span>
                    <span class="match-score ${scoreClass}">${job.match_score}%</span>
                </div>
            </div>
            <div class="job-meta">
                ${job.location ? `<span class="tag">${escapeHtml(job.location)}</span>` : ''}
                ${job.salary_range ? `<span class="tag green">${escapeHtml(job.salary_range)}</span>` : ''}
            </div>
            ${job.description_short ? `<p style="font-size:13px;color:var(--text-secondary);margin:8px 0;">${escapeHtml(job.description_short)}</p>` : ''}
            <div class="job-skills" style="margin-bottom:8px;">
                ${(job.skills_match || []).map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')}
                ${(job.skills_missing || []).map(s => `<span class="skill-tag" style="opacity:0.4;text-decoration:line-through;">${escapeHtml(s)}</span>`).join('')}
            </div>
            <ul class="match-reasons">
                ${(job.match_reasons || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
        </div>
    `;
}

// ── Search Page Logic ───────────────────────────

async function searchJobs() {
    const q = $('#search-input')?.value || '';
    const location = $('#filter-location')?.value || '';
    const category = $('#filter-category')?.value || '';
    const locationType = $('#filter-location-type')?.value || '';
    const employmentType = $('#filter-employment-type')?.value || '';

    const resultsEl = $('#results');
    const headerEl = $('#results-header');
    if (!resultsEl) return;

    resultsEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const data = await apiGet('/jobs', {
            q: q || undefined,
            location: location || undefined,
            category: category || undefined,
            location_type: locationType || undefined,
            employment_type: employmentType || undefined,
            limit: 40,
        });

        if (headerEl) {
            headerEl.innerHTML = `
                <span class="results-count">${data.total.toLocaleString()} jobs found</span>
                <span class="results-time">${data.query_time_ms.toFixed(1)}ms</span>
            `;
        }

        if (data.jobs.length === 0) {
            resultsEl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px;">No jobs found matching your criteria.</p>';
            return;
        }

        resultsEl.innerHTML = `<div class="cards-grid">${data.jobs.map(renderJobCard).join('')}</div>`;
    } catch (e) {
        resultsEl.innerHTML = `<p style="text-align:center;color:var(--red);padding:40px;">Error: ${escapeHtml(e.message)}</p>`;
    }
}

// ── Agent Search Logic ──────────────────────────

async function agentSearch() {
    const resumeText = $('#resume-text')?.value || '';
    const skills = $('#agent-skills')?.value || '';
    const experience = $('#agent-experience')?.value || '';
    const locations = $('#agent-locations')?.value || '';
    const salaryMin = $('#agent-salary')?.value || '';

    const resultsEl = $('#agent-results');
    if (!resultsEl) return;

    resultsEl.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    const body = {};
    if (resumeText) body.resume_text = resumeText;
    if (skills) body.skills = skills.split(',').map(s => s.trim()).filter(Boolean);
    if (experience) body.experience_years = parseInt(experience);
    if (locations) body.preferred_locations = locations.split(',').map(s => s.trim()).filter(Boolean);
    if (salaryMin) body.salary_min = parseInt(salaryMin);
    body.limit = 20;

    try {
        const data = await apiPost('/agent/search', body);

        resultsEl.innerHTML = `
            <div class="results-header">
                <span class="results-count">${data.match_count} matches found</span>
                <span class="results-time">Matched in ${data.query_time_ms.toFixed(0)}ms · Session: ${data.session_id}</span>
            </div>
            <div class="cards-grid">
                ${data.jobs.map(renderMatchCard).join('')}
            </div>
        `;
    } catch (e) {
        resultsEl.innerHTML = `<p style="text-align:center;color:var(--red);padding:40px;">Error: ${escapeHtml(e.message)}</p>`;
    }
}

// ── Landing Page Quick Search ───────────────────

function quickSearch() {
    const q = $('#hero-search')?.value;
    if (q) {
        window.location.href = `/search?q=${encodeURIComponent(q)}`;
    }
}

// ── Initialize ──────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Render auth header on all pages
    renderAuthHeader();

    // Landing page
    if ($('#stats-row')) loadStats();
    if ($('#hero-search')) {
        $('#hero-search').addEventListener('keydown', e => {
            if (e.key === 'Enter') quickSearch();
        });
    }

    // Search page
    if ($('#search-input')) {
        // Load from URL params
        const params = new URLSearchParams(window.location.search);
        if (params.get('q')) $('#search-input').value = params.get('q');

        // Auto-search on load if query exists
        if (params.get('q')) searchJobs();

        // Search on enter
        $('#search-input').addEventListener('keydown', e => {
            if (e.key === 'Enter') searchJobs();
        });

        // Load categories for filter
        apiGet('/categories').then(data => {
            const sel = $('#filter-category');
            if (sel && data.categories) {
                data.categories.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.category;
                    opt.textContent = `${c.category} (${c.count})`;
                    sel.appendChild(opt);
                });
            }
        }).catch(() => {});
    }

    // Agent page
    if ($('#agent-search-btn')) {
        $('#agent-search-btn').addEventListener('click', agentSearch);
    }
});
