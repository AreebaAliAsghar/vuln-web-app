# Implementation Plan — Delete Account (v2.2.0)

**Feature:** Delete Account
**Target Release Tag:** v2.2.0
**Spec:** `.claude/specs/delete-account.md`

---

## 1. New Files

### 1.1 `backend/app/services/account_service.py`
**Purpose:** Delete account service with password verification and parameterized DELETE.

**Steps:**
1. Create `backend/app/services/account_service.py`.
2. Import `get_db`, `logger`, `auth_service`, `html`.
3. Define `delete_account(user_id: int, password: str) -> dict`:
   - `conn = get_db()`
   - `cursor = conn.cursor()`
   - `cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))`
   - If no row: return `{"status": "not_found"}`
   - `if not auth_service.verify_password(password, row["password"]): return {"status": "invalid_password"}`
   - `cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))`
   - `conn.commit()`
   - `logger.info(f"Account deleted: user_id={user_id}")`
   - Return `{"status": "ok"}`

---

## 2. Modified Files

### 2.1 `backend/app/api/routes/auth.py`
**Purpose:** Add `POST /profile/delete` route.

**Steps:**
1. Import `account_service` at the top (after other service imports).
2. Add new route handler function:
   ```python
   @router.post("/profile/delete")
   async def delete_account_post(request: Request, password: str = Form(...)):
       user_id = request.session.get("user_id")
       if not user_id:
           return JSONResponse({"error": "Not authenticated."}, status_code=401)
       
       result = account_service.delete_account(user_id, password)
       
       if result["status"] == "invalid_password":
           return JSONResponse({"error": "Incorrect password."}, status_code=400)
       if result["status"] == "not_found":
           return JSONResponse({"error": "Could not delete account."}, status_code=500)
       if result["status"] != "ok":
           return JSONResponse({"error": "Could not delete account."}, status_code=500)
       
       request.session.clear()
       return JSONResponse({"success": True})
   ```

### 2.2 `frontend/templates/profile.html`
**Purpose:** Add Delete Account card at bottom of profile page.

**Steps:**
1. Read the file.
2. Find the closing `</div>` of the last profile card (before `</main>`).
3. Insert new card HTML before that closing tag:
   ```html
   <div class="profile-card">
       <h2 class="section-title">Delete Account</h2>
       <p class="section-subtitle">Permanently delete your account. This action cannot be undone.</p>
       <form id="delete-account-form">
           <input type="hidden" name="csrf_token" value="{{csrf_token}}">
           <div class="form-group">
               <label for="delete_password">Confirm password</label>
               <input type="password" id="delete_password" name="password" required class="form-input" placeholder="Enter your password">
           </div>
           <div id="delete-account-message" role="status" aria-live="polite" style="display: none;"></div>
           <button type="submit" class="btn btn-danger">Delete my account</button>
       </form>
   </div>
   ```
4. Add inline `<script>` block after the form:
   ```html
   <script>
   (function() {
       const form = document.getElementById('delete-account-form');
       const message = document.getElementById('delete-account-message');
       form.addEventListener('submit', async function(e) {
           e.preventDefault();
           message.style.display = 'none';
           message.className = 'profile-message';
           const formData = new FormData(form);
           const body = new URLSearchParams(formData);
           try {
               const resp = await fetch('/profile/delete', {
                   method: 'POST',
                   body: body
               });
               const data = await resp.json();
               if (data.success) {
                   // Clear session and redirect
                   await fetch('/logout', { method: 'POST' });
                   window.location.href = '/login?deleted=1';
               } else {
                   message.textContent = data.error || 'Could not delete account.';
                   message.classList.add('is-error');
                   message.style.display = 'block';
               }
           } catch (err) {
               message.textContent = 'An error occurred.';
               message.classList.add('is-error');
               message.style.display = 'block';
           }
       });
   })();
   </script>
   ```

### 2.3 `frontend/templates/login.html`
**Purpose:** Add flash message for deleted account.

**Steps:**
1. Read the file.
2. Find a suitable location (after the form, before the footer/links).
3. Add a `{{deleted}}` placeholder and conditional rendering:
   - Add `deleted` parameter to the `login_page` route in `auth.py`
   - Or add simple JS to parse URL parameter `?deleted=1`
   
   **Alternative (simpler):** Add JS to parse `?deleted=1` from URL:
   ```html
   <script>
   (function() {
       const params = new URLSearchParams(window.location.search);
       if (params.get('deleted') === '1') {
           const msg = document.createElement('div');
           msg.className = 'profile-message is-success';
           msg.textContent = 'Your account has been deleted.';
           msg.style.display = 'block';
           msg.style.marginBottom = '1rem';
           document.querySelector('.login-container').prepend(msg);
       }
   })();
   </script>
   ```

### 2.4 `frontend/static/css/styles.css`
**Purpose:** Add danger button styling.

**Steps:**
1. Read the file.
2. Append at end of file:
   ```css
   /* Delete Account Button */
   .btn-danger {
       background-color: #dc3545;
       color: #fff;
       border: none;
       padding: 0.75rem 1.5rem;
       border-radius: 4px;
       font-size: 1rem;
       cursor: pointer;
       transition: background-color 0.2s;
   }

   .btn-danger:hover {
       background-color: #c82333;
   }

   [data-theme="dark"] .btn-danger {
       background-color: #dc3545;
   }

   [data-theme="dark"] .btn-danger:hover {
       background-color: #bd2130;
   }
   ```

### 2.5 `README.md`
**Purpose:** Document v2.2.0 feature.

**Steps:**
1. Add row to Feature Enhancements table (#11).
2. Add row to Release History table (v2.2.0).

### 2.6 `CLAUDE.md`
**Purpose:** Document the new feature.

**Steps:**
1. Add integration paragraph to "Frontend-Backend Integration" section.
2. Add new Important Rule for delete account.
3. Add entry to Specification Hierarchy (item 22).

---

## 3. Files That MUST NOT Be Modified

- `backend/app/main.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/profile_service.py`
- `backend/app/services/lockout_service.py`
- `backend/app/services/verification_service.py`
- `backend/app/services/oauth_service.py`
- `backend/app/services/otp_service.py`
- `backend/app/services/totp_service.py`
- `backend/app/core/security.py`
- `backend/app/core/csrf.py`
- `backend/app/core/rate_limit.py`
- `backend/app/core/oauth.py`
- `backend/app/core/qr_login.py`
- `backend/app/core/captcha.py`
- `backend/app/core/mailer.py`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `pyproject.toml`
- `.env.example`
- `uv.lock`

---

## 4. Implementation Order

1. Create `account_service.py` (new service)
2. Add route in `auth.py` (new endpoint)
3. Add Delete Account card in `profile.html` (UI)
4. Add flash message in `login.html` (UI)
5. Add `.btn-danger` CSS (styling)
6. Update `README.md` (docs)
7. Update `CLAUDE.md` (docs)

---

## 5. Manual Test Checklist

- [ ] Sign up a new user
- [ ] Visit /profile, verify Delete Account card is visible at bottom
- [ ] Try to delete without password → validation error
- [ ] Enter wrong password → "Incorrect password." error
- [ ] Enter correct password → success, redirect to /login?deleted=1
- [ ] Verify flash message "Your account has been deleted." appears
- [ ] Try to log in with deleted credentials → should fail
- [ ] Verify no SQL injection via password field works
- [ ] Verify CSRF protection works (no token → 403)