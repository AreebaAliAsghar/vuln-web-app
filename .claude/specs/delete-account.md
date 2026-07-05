# Software Specification Document — Delete Account

**Version:** 1.0.0
**Last Updated:** 2026-07-05
**Target Release Tag:** v2.2.0
**Parent Documents:** [PRD.md](../../docs/PRD.md), [TDD.md](../../docs/TDD.md), [app-foundation.md](./app-foundation.md), [user-profile-page.md](./user-profile-page.md), [display-name-and-email-edit.md](./display-name-and-email-edit.md)
**Tracking Issue:** [User Account Management Enhancements — Delete Account](https://github.com/arifpucit/vuln-web-app/issues)

---

## 1. Overview / Purpose

This document specifies the **Delete Account** enhancement. It is the second slice of the "User Account Management Enhancements" feature group identified in the README's "Feature Enhancements" table. It adds the ability for a logged-in user to permanently delete their account from the `/profile` page.

**This slice is additive, schema-migrating, and middleware-respecting.** It does not modify `main.py`, `auth_service.login()`, the lockout/CSRF/rate-limit middleware, the session secret, or any of the eight previously-closed vulnerabilities. It composes cleanly with every shipped feature (Email Verification v1.0.4, Account Lockout v1.0.5, Email-OTP 2FA v1.0.6, TOTP v1.0.7, QR Login v1.0.8, CAPTCHA v2.0.0, Profile Editing v2.1.0).

### 1.1 Why now, and what the user sees

Today's `/profile` page allows users to view and edit their display name, email, and password, and configure 2FA. However, there is no way for a user to permanently delete their account. This slice adds a **Delete Account** card at the bottom of the profile page that allows users to:

1. **Confirm their password** — as authorization to delete (same as the change-password flow).
2. **Permanently delete the account** — removes the user row from the database.
3. **Session termination** — clears the session and redirects to the login page with a success message.

### 1.2 Design Decisions (product-owner choices)

These decisions were made explicitly before writing this spec and shape everything below:

1. **Password confirmation is required.** Deleting an account is a destructive action. The user must confirm their current password to authorize the deletion. This is the same pattern as change-password.
2. **Soft-delete is NOT used.** The user's row is permanently removed from the database. No `is_deleted` flag or archival. This is a hard delete.
3. **The user's data is completely removed.** All columns associated with the user (`users` row) are deleted. This includes display name, email, password hash, 2FA settings, verification tokens, OAuth linkage, etc.
4. **No confirmation dialog beyond password.** The password field itself serves as the confirmation. No additional "Are you sure?" modal is shown — the password entry is the deliberate act.
5. **The session is cleared on success.** After deletion, the user is logged out and redirected to `/login` with a flash message "Your account has been deleted."
6. **Username is NOT reusable.** After deletion, the username is permanently gone. A new user can sign up with the same username (SQLite does not enforce unique at the application level beyond the INSERT constraint, which is removed with the row).
7. **No email notification of deletion.** The deletion is silent — no confirmation email is sent. This matches the no-notification-on-password-change pattern.
8. **QR login tokens are NOT cleaned up.** The in-memory QR login state (`core/qr_login.py`) is not modified. Stale tokens will simply never be claimed. This is acceptable because they already have a TTL and self-purge.
9. **Rate limiting applies.** The delete account POST is a POST, so it inherits the existing `RateLimitMiddleware` (5 POSTs per 60s per IP).
10. **CSRF protection applies.** The delete account form carries the hidden `csrf_token` field and is protected by `CSRFMiddleware`.

### 1.3 Built on existing primitives

This slice is deliberately **surgical**: it adds one new service module, one new route, one new card in `profile.html`, and the existing infrastructure (middleware, mailer, verification service) is unchanged.

- **New service lives in `account_service.py`** — sibling of `auth_service.py`, `profile_service.py`. Parameterized DELETE query.
- **The new route follows the same `def_post` pattern as every other route** in `api/routes/auth.py` — thin wrapper over the service layer that splices CSRF tokens, parses `Form(...)` inputs, and returns JSON.
- **The new "Delete Account" card follows the same `profile-card > section-title + form + profile-message` pattern** as every other card on `/profile`.
- **The existing middleware stack is unchanged.** The new POST route (`POST /profile/delete`) automatically inherits CSRF, rate-limit, and signed-session protections.

### 1.4 The implementation touches

- **One new backend module**: `backend/app/services/account_service.py` (parameterized DELETE, password verification via `auth_service.verify_password`).
- **Existing files**: `backend/app/api/routes/auth.py` (one new route), `frontend/templates/profile.html` (additive Delete Account card), `frontend/static/css/styles.css` (small additive block), `backend/app/db/session.py` (no schema change — deletion removes the row, no new column).
- **Documentation**: `README.md` (Feature Enhancements row, release row), `CLAUDE.md` (Important Rule, hierarchy entry).
- **Spec/plan docs**: `.claude/specs/delete-account.md` (this file), `.claude/specs/delete-account-plan.md`.

**No other file is touched.** In particular, `backend/app/main.py`, `backend/app/services/auth_service.py`, `backend/app/services/profile_service.py`, `backend/app/services/lockout_service.py`, `backend/app/services/verification_service.py`, `backend/app/services/oauth_service.py`, `backend/app/services/otp_service.py`, `backend/app/services/totp_service.py`, `backend/app/core/security.py`, `backend/app/core/csrf.py`, `backend/app/core/rate_limit.py`, `backend/app/core/oauth.py`, `backend/app/core/qr_login.py`, `backend/app/core/captcha.py`, `backend/app/core/mailer.py`, `backend/app/core/config.py`, `backend/app/db/session.py`, and every template except `profile.html` remain unchanged.

This feature introduces **no database-schema change** — deletion removes a row, no column is added.

### 1.5 What this slice does NOT do

- Does **NOT** implement soft-delete with an `is_deleted` flag. This is a hard delete.
- Does **NOT** send a deletion confirmation email. Silent deletion.
- Does **NOT** archive user data before deletion. The row is permanently removed.
- Does **NOT** clean up QR login tokens. Stale tokens remain in memory (acceptable — they have TTL).
- Does **NOT** require 2FA re-verification. The password is the authorization.
- Does **NOT** allow deletion without password confirmation. Password is mandatory.
- Does **NOT** invalidate other sessions (single-device model). Only the deleting session is cleared.
- Does **NOT** add CAPTCHA to the delete flow. Session-gated, no bot risk.

### 1.6 Explicit Preservation Note — All Eight Closed Vulnerabilities Stay Closed

- **VULN-1 (SQL Injection):** the DELETE query uses parameterized `?` placeholders (`DELETE FROM users WHERE id = ? AND password = ?`). The user ID comes from the session (not user input), and the password is verified via `auth_service.verify_password`.
- **VULN-2 (Stored XSS):** no new user-controlled content is rendered. The delete form does not reflect any user input into the response.
- **VULN-3 (Reflected XSS):** the POST does not reflect the submitted password into the response body. The JSON response is a fixed set of keys (`success`, `error`).
- **VULN-4 (Session Hijacking):** `main.py` is not modified; the env-sourced `SECRET_KEY` is untouched. The session is cleared via `request.session.clear()`.
- **VULN-5 (Weak Password Storage):** `core/security.py` is not modified; bcrypt is unchanged. Password verification uses the existing `verify_password` function.
- **VULN-6 (Exposed Database):** no new route is added. The DELETE is a standard SQL statement, not a file download.
- **VULN-7 (No Rate Limiting):** `RateLimitMiddleware` stays registered and unchanged; the new `POST /profile/delete` is a POST, so it inherits the same per-IP throttle.
- **VULN-8 (CSRF):** the new `POST /profile/delete` carries the hidden `csrf_token` field; `CSRFMiddleware` validates it.

---

## 2. Scope & Non-Goals

### 2.1 In Scope

- **Delete account service.** `backend/app/services/account_service.py`:
  - `delete_account(user_id: int, password: str) -> dict` — the workhorse:
    1. SELECT the row by primary key to get the password hash (parameterized).
    2. Verify the password using `auth_service.verify_password(password, row["password"])`. If verification fails, return `{"status": "invalid_password"}`.
    3. DELETE the row (`DELETE FROM users WHERE id = ?`, parameterized).
    4. Return `{"status": "ok"}`.
  - **All SQL is parameterized.** No string concatenation.
- **Delete account route.** `backend/app/api/routes/auth.py`:
  - **Add `POST /profile/delete`**: thin wrapper over `account_service.delete_account`. Session-gated. CSRF + rate-limit are enforced by middleware before this runs. Returns JSON: `{"success": true}` on success; `{"error": "Incorrect password."}` on invalid password; `401` on no session.
- **Profile template.** `frontend/templates/profile.html`:
  - **Additive** Delete Account card, placed at the bottom of the page (after all other cards). Mirrors the existing card structure: `<div class="profile-card">` > `<h2 class="section-title">Delete Account</h2>` > `<form id="delete-account-form">` (with hidden `csrf_token`) > one `<div class="form-group">` with password field > a `<div id="delete-account-message">` feedback > a "Delete my account" button.
  - The card's title says "Delete Account" and the section subtitle says "Permanently delete your account. This action cannot be undone."
  - A small inline `<script>` at the bottom of the card submits via `URLSearchParams(new FormData(form))` and `fetch('/profile/delete', { method: 'POST', body })`. On success, clears the session (via a `POST /logout` call or session clear), then redirects to `/login?deleted=1`. On error, shows the message in the feedback div.
- **CSS.** `frontend/static/css/styles.css`:
  - Append a small additive `.delete-account-btn` block (red/danger styled button) matching the existing `.btn` patterns.
  - **No existing rule is modified.**
- **Login page (optional).** `frontend/templates/login.html`:
  - Add a `{{deleted}}` placeholder that, when present, shows a flash message "Your account has been deleted." This is the post-deletion redirect target.

### 2.2 Out of Scope (Intentionally)

- **Soft-delete with `is_deleted` flag.** Hard delete only.
- **Email notification of deletion.** Silent deletion.
- **Data archival before deletion.** Row is permanently removed.
- **QR login token cleanup.** Not modified.
- **2FA re-verification.** Password is the authorization.
- **Invalidation of other sessions.** Single-device model.
- **CAPTCHA on delete.** Session-gated, no bot risk.
- **No new env var.** No configuration needed.
- **No new template engine.** Uses existing `str.replace()` pattern.

### 2.3 Files that MUST NOT be modified

- `backend/app/main.py` — middleware wiring / `SECRET_KEY` / `RATE_LIMIT_*` / port.
- `backend/app/services/auth_service.py` — unchanged (used via import for password verification).
- `backend/app/services/profile_service.py`, `lockout_service.py`, `verification_service.py`, `oauth_service.py`, `otp_service.py`, `totp_service.py` — unchanged.
- `backend/app/core/security.py`, `core/csrf.py`, `core/rate_limit.py`, `core/oauth.py`, `core/qr_login.py`, `core/captcha.py`, `core/mailer.py`, `core/config.py`.
- `backend/app/db/session.py` — no schema change.
- `frontend/templates/signup.html`, `dashboard.html`, `verify_result.html`, `check_email.html`, `email_not_configured.html`, `oauth_not_configured.html`, `qr_approve.html`, `otp_verify.html`, `totp_verify.html`.
- `pyproject.toml` — no dependency change.
- `.env.example` — no new tunable.
- `uv.lock` — regenerated by `uv sync` if needed.

---

## 3. Affected Files

The change MUST touch only the following files.

| Path | Change Type | Purpose |
|------|-------------|---------|
| `.claude/specs/delete-account.md` | **New** | This spec doc. |
| `.claude/specs/delete-account-plan.md` | **New** | Per-file task list. |
| `backend/app/services/account_service.py` | **New** | The workhorse service: `delete_account`. |
| `backend/app/api/routes/auth.py` | Modified | One new route (`POST /profile/delete`). |
| `frontend/templates/profile.html` | Modified | Additive Delete Account card. |
| `frontend/static/css/styles.css` | Modified | Small additive block (`.delete-account-btn`). |
| `frontend/templates/login.html` | Modified | Optional flash message on `{{deleted}}`. |
| `README.md` | Modified | Feature Enhancements row + release row. |
| `CLAUDE.md` | Modified | Important Rule + hierarchy entry. |

**Files that MUST NOT be modified by this change:**

- `backend/app/main.py`
- `backend/app/services/auth_service.py`, `profile_service.py`, `lockout_service.py`, `verification_service.py`, `oauth_service.py`, `otp_service.py`, `totp_service.py`
- `backend/app/core/security.py`, `core/csrf.py`, `core/rate_limit.py`, `core/oauth.py`, `core/qr_login.py`, `core/captcha.py`, `core/mailer.py`, `core/config.py`
- `backend/app/db/session.py`
- `pyproject.toml`'s `dependencies` array
- `.env.example`
- `uv.lock`

---

## 4. Functional Requirements

### FR-01: Delete Account Service — `account_service.py`
- `delete_account(user_id: int, password: str) -> dict` MUST:
  1. Open a fresh `get_db()` connection.
  2. SELECT the row by primary key (parameterized) — if not found, return `{"status": "not_found"}`.
  3. Verify the password using `auth_service.verify_password(password, row["password"])`. If verification fails, return `{"status": "invalid_password"}`.
  4. DELETE the row (`DELETE FROM users WHERE id = ?`, parameterized).
  5. Return `{"status": "ok"}`.
- Every SQL statement MUST be parameterized (`?` placeholders, bound values as a separate list). No string concatenation.

### FR-02: `POST /profile/delete` — New Route
- The route MUST be a thin wrapper over `account_service.delete_account`. Session-gated (no `user_id` → 401 JSON). CSRF + rate-limit are enforced by middleware before this runs.
- The route MUST read `password: str = Form(...)` (required field).
- On success, the route MUST clear the session: `request.session.clear()`. This is what causes `SessionMiddleware` to emit the session-cleared cookie.
- The route MUST return JSON for every outcome so the page's `fetch()` handler can render feedback:
  - `200 {"success": true}` on success.
  - `400 {"error": "Incorrect password."}` on invalid password.
  - `401 {"error": "Not authenticated."}` on no session.
  - `500 {"error": "Could not delete account."}` on unexpected DB error.

### FR-03: Profile Template — Additive Card
- `frontend/templates/profile.html` MUST add a Delete Account card at the bottom of the page. The card MUST follow the same `profile-card > section-title + form + profile-message` structure as every other card.
- The card MUST contain:
  - A hidden `<input type="hidden" name="csrf_token" value="{{csrf_token}}">` field.
  - A `<div class="form-group">` with label "Confirm password" and an `<input type="password" id="delete_password" name="password" required class="form-input">`.
  - A "Delete my account" button (`<button type="submit" class="btn btn-danger">Delete my account</button>`).
  - A feedback `<div id="delete-account-message" role="status" aria-live="polite" style="display: none;">`.
- The card's title MUST be "Delete Account" with subtitle "Permanently delete your account. This action cannot be undone."
- The card MUST have an inline `<script>` block that:
  1. Listens to the form's `submit` event with `e.preventDefault()`.
  2. Submits via `URLSearchParams(new FormData(form))` and `fetch('/profile/delete', { method: 'POST', body })`.
  3. On `200`, clears the session (calls `POST /logout` or uses `sessionStorage.clear()`), then redirects to `/login?deleted=1`.
  4. On `400`, displays the error in the feedback div.

### FR-04: Login Template — Optional Flash Message
- `frontend/templates/login.html` MUST add a `{{deleted}}` placeholder.
- When `{{deleted}}` is `"1"`, display a flash message "Your account has been deleted." (styled as a success message).
- The message MUST be `html.escape`d if rendered server-side.

### FR-05: CSS — Additive Block
- `frontend/static/css/styles.css` MUST append:
  - A `.btn-danger` block: red background, white text, hover darkens — matching the existing `.btn` patterns.
- **No existing rule MUST be modified.**

### FR-06: Rate Limit + CSRF Apply
- The new `POST /profile/delete` is a POST, so it MUST inherit the existing `RateLimitMiddleware` and `CSRFMiddleware` without any modification.
- A POST without a valid `csrf_token` form field MUST be rejected with 403.
- The 6th POST in a 60-second window MUST be rejected with 429.

### FR-07: Session Clearance
- On successful deletion, the session MUST be cleared via `request.session.clear()`. This logs the user out completely.
- The redirect to `/login?deleted=1` happens after the session is cleared.

### FR-08: Password Verification Uses Existing Function
- The password verification MUST use `auth_service.verify_password()` which wraps `bcrypt.checkpw`. This ensures consistent password handling with the rest of the app.

---

## 5. Non-Functional Requirements

### NFR-01: Surgical Scope
- The change MUST touch only the files in §3. `main.py`, all existing services, all core modules, and all other templates MUST remain unchanged.

### NFR-02: No Regressions to Closed Vulnerabilities
- All eight previously-closed vulnerabilities MUST remain closed.

### NFR-03: Performance
- The delete operation MUST complete in under 100ms on a warm SQLite.
- No new queries are introduced beyond the SELECT (for password verification) and DELETE.

### NFR-04: Observability
- The `account_service` MUST log a `logger.info` line on successful deletion (with user_id — no PII).

### NFR-05: Idempotency
- A second delete attempt for the same user_id MUST fail with "not_found" (the row is already gone).

### NFR-06: No Hardcoded Secrets
- No new secret is introduced.

### NFR-07: Documentation Discipline
- `README.md` and `CLAUDE.md` MUST be updated to reflect the v2.2.0 feature.

---

## 6. Open Questions (resolved before merge)

1. **Soft-delete vs hard-delete: hard-delete.** Resolved: permanent row removal.
2. **Email confirmation: no.** Resolved: silent deletion.
3. **Password required: yes.** Resolved: password confirmation mandatory.

---

## 7. Out of Scope (Future Slices)

- **Soft-delete with archival** — separate spec.
- **Email notification of deletion** — future hardening.
- **Session invalidation across devices** — future hardening.
- **2FA re-verification** — future hardening.

---

## 8. Verification

### 8.1 Manual smoke test
```bash
uv run backend/app/main.py    # boot the app on :3001
# 1. Sign up a new user.
# 2. Visit /profile; scroll to the bottom; the new Delete Account card is visible.
# 3. Try to delete without entering password. Expected: validation error.
# 4. Enter wrong password. Expected: "Incorrect password." error.
# 5. Enter correct password. Expected: success, redirect to /login?deleted=1,
#    flash message "Your account has been deleted."
# 6. Try to log in with the deleted credentials. Expected: "Invalid username or password."
```

### 8.2 Security spot-check
```bash
# VULN-1: try SQLi on the password field
curl -X POST -d "csrf_token=$TOKEN&password=' OR '1'='1" \
  -b cookies.txt http://localhost:3001/profile/delete
# Expected: 400 with "Incorrect password."; the row is unchanged.

# VULN-8: POST /profile/delete without csrf_token. Expected: 403 from
# CSRFMiddleware; the handler does not run.
```

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Accidental deletion without password | Low | High | Password field is required; form validation prevents empty submit. |
| SQL injection via password field | Low | High | Parameterized query; password goes through `verify_password` (bcrypt), not SQL. |
| Session not cleared on error | Very low | Medium | `request.session.clear()` is called only on success; on failure, session persists. |

---

## 10. References

- v2.1.0 spec: `.claude/specs/display-name-and-email-edit.md` — the profile editing feature this builds on.
- v1.0.2 spec: `.claude/specs/user-profile-page.md` — the existing `/profile` page.
- `CLAUDE.md` — the project-wide rules this slice must honour.