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
| High | 2 | 🔴 |
| Medium | 5 | 🟡 |
| Low | 3 | 🔵 |
| Info | 2 | ℹ️ |

---

## High Severity Issues

### 🔴 H1: No Email Validation (API Endpoints)
**File:** `src/web/api.py:40-54`  
**Impact:** Malformed emails, email spoofing, DoS via email enumeration

```python
class SignupRequest(BaseModel):
    email: str  # No email format validation
```

**Fix:**
```python
from pydantic import EmailStr
class SignupRequest(BaseModel):
    email: EmailStr  # Validates format
```

### 🔴 H2: Subscriber Data Accessible by Guessing Email
**File:** `src/web/api.py:80-100`  
**Impact:** Any user can view/update ANY subscriber's data by guessing emails

```python
@app.get("/dashboard/{email}", response_class=HTMLResponse)
async def dashboard(request: Request, email: str):
    # No authentication - anyone can access any dashboard
```

**Fix:** Add token-based authentication or email confirmation flow.

---

## Medium Severity Issues

### 🟡 M1: SQL Injection via Dynamic Column Names
**File:** `src/core/db.py:77`  
**Impact:** Column names constructed from Python dict keys

```python
fields.append(f"{key}=?")  # key from updates dict
conn.execute(f"UPDATE subscribers SET {', '.join(fields)} WHERE email=?", values)
```

**Fix:** Whitelist allowed column names.

### 🟡 M2: No Rate Limiting
**File:** `src/web/api.py` (global)  
**Impact:** Brute force attacks on signup, settings update, feedback

**Fix:** Add `slowapi` middleware.

### 🟡 M3: Server Binds to All Interfaces (Development)
**File:** `src/web/api.py:190`  
**Impact:** Development server exposed on all network interfaces

```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Fix:** Use `127.0.0.1` for development, configure proper host for production.

### 🟡 M4: URL Scheme Validation (urllib)
**Files:** `scripts/fetch_predatory_list.py:25`, `src/core/openalex.py:30`, `src/core/quality_control.py:158`  
**Impact:** Bandit B310 - Hardcoded URLs but no scheme validation

**Fix:** Add URL scheme validation or use `requests` library with scheme validation.

### 🟡 M5: No API Authentication
**File:** `src/web/api.py`  
**Impact:** API endpoints accessible without authentication

**Fix:** Add API key or token-based auth for API endpoints.

---

## Low Severity Issues

### 🔵 L1: No .gitignore for Secrets
**File:** `.gitignore`  
**Impact:** `.env` file could be accidentally committed

**Fix:** Add explicit `.env`, `token.json`, `client_secret*.json` exclusions.

### 🔵 L2: No Dependency Pinning
**Impact:** Supply chain attack vector via unpinned dependencies

**Fix:** Create `requirements.txt` with pinned versions.

### 🔵 L3: Feedback Email Not Validated
**File:** `src/web/api.py:120-140`  
**Impact:** Anyone can submit feedback for any email address

**Fix:** Validate feedback email matches authenticated session or add rate limiting.

---

## Informational

### ℹ️ I1: Gmail API Scopes
**File:** `src/email/sender.py:11-14`  
**Status:** Using `gmail.modify` scope (broader than needed)  
**Recommendation:** Use `gmail.send` only for sending emails.

### ℹ️ I2: .env Permissions
**File:** `.env`  
**Status:** `600` (owner read/write only) - ✅ Correct

---

## Bandit SAST Scan Results

```
Found 5 MEDIUM issues:
[MEDIUM] B310 - Audit url open for permitted schemes (3 instances)
[MEDIUM] B608 - Possible SQL injection via string-based query (db.py:77)
[MEDIUM] B104 - Possible binding to all interfaces (api.py:190)
```

---

## Recommendations

1. **Critical Priority:**
   - Add email format validation (Pydantic `EmailStr`)
   - Implement authentication for dashboard/settings endpoints

2. **High Priority:**
   - Add rate limiting (`slowapi`)
   - Fix SQL injection via column name whitelisting
   - Create `.gitignore` for secrets

3. **Medium Priority:**
   - Pin dependencies (`requirements.txt`)
   - Add URL scheme validation
   - Use `gmail.send` scope only

4. **Low Priority:**
   - Validate feedback email ownership
   - Add API key authentication for endpoints

---

## Next Steps

- [ ] Fix H1, H2 (authentication)
- [ ] Fix M1 (SQL injection)
- [ ] Add M2 (rate limiting)
- [ ] Create `.gitignore` for secrets
- [ ] Add `requirements.txt` with pinned versions
- [ ] Re-run bandit scan after fixes
