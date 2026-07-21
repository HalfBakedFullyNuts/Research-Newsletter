# 🔒 ResearchPulse Security Audit Report
**Date:** 2026-07-20  
**Auditor:** Hermes Agent (automated + manual review)  
**Scope:** Full codebase (src/, scripts/, .env)  
**Severity Scale:** Critical, High, Medium, Low, Info

---

## Executive Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | ✅ |
| High | 0 | ✅ Fixed |
| Medium | 2 | 🟡 Remaining |
| Low | 3 | ✅ Fixed |
| Info | 2 | ℹ️ Info |

---

## Fixed Issues

### ✅ H1: Email Validation (FIXED)
**File:** `src/web/api.py`  
**Fix:** Added `@field_validator` with regex validation, lowercase normalization, 254-char limit  
**Status:** All input models (SignupRequest, FeedbackRequest, SettingsUpdate) now validate email format

### ✅ H2: SQL Injection via Column Names (FIXED)
**File:** `src/core/db.py:67-77`  
**Fix:** Column whitelist (`ALLOWED_COLUMNS`) rejects any unknown column before SQL construction  
**Status:** Only `topics`, `profession`, `day`, `time`, `active` accepted

### ✅ L1: .gitignore for Secrets (FIXED)
**File:** `.gitignore`  
**Fix:** Added `.env`, `token.json`, `client_secret*.json`, `*.pem`, `*.key` exclusions  
**Status:** Secrets excluded from git tracking

### ✅ L2: Rate Limiting (FIXED)
**File:** `src/web/api.py`  
**Fix:** In-memory rate limiter (20 req/60s per IP per endpoint)  
**Status:** API endpoints protected. 429 on excess.

### ✅ L3: CORS (FIXED)
**File:** `src/web/api.py`  
**Fix:** `CORSMiddleware` with empty `allow_origins` (same-origin only)  
**Status:** No cross-origin requests allowed

---

## Remaining Issues

### 🟡 M1: URL Scheme Validation (Bandit B310)
**Files:** `scripts/fetch_predatory_list.py:25`, `src/core/openalex.py:30`, `src/core/quality_control.py:158`  
**Status:** Hardcoded HTTP URLs only — low risk but flagged by bandit  
**Recommendation:** Accept as-is (hardcoded trusted URLs). Flag for next audit.

### 🟡 M2: Dashboard Accessible by Email Guessing
**File:** `src/web/api.py:80-100`  
**Status:** Dashboard URL `/dashboard/{email}` reveals subscriber data by guessing email  
**Recommendation:** Add token-based auth when Stripe integration lands. Acceptable for MVP.

---

## Bandit SAST Scan Results

```
Before fixes: 5 MEDIUM issues
After fixes:  3 MEDIUM (all B310 - hardcoded URL scheme warnings)
  [FIXED] B608 - SQL injection via column names
  [FIXED] B104 - Binding to all interfaces (dev-only, commented)
```

---

## Next Audit
- [ ] Token-based auth for dashboard (when Stripe lands)
- [ ] Add HTTPS/TLS (production deployment)
- [ ] Dependency pinning (`requirements.txt`)
- [ ] Add logging/monitoring for suspicious activity

