# Fixture CTA + País en Registro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make group-stage fixture cards clickable to open the auth modal, and add a flat País dropdown to the registration form.

**Architecture:** Two independent features in a vanilla HTML/CSS/JS app with no build step. Feature 1 adds a JS click handler and CSS hover to existing `.cal-match` cards in `.team-fixtures`. Feature 2 adds a `<select>` to the auth form HTML, updates `auth.js` to show/hide it and pass `country` to Supabase signUp, and applies a DB migration to store the value.

**Tech Stack:** Vanilla JS, inline CSS, Supabase JS v2, PostgreSQL (via MCP)

---

### Task 1: Supabase migration — add country column

**Files:**
- Modify: Supabase DB via MCP (`profiles` table, `handle_new_user` trigger)

- [ ] **Step 1: Apply migration via MCP**

SQL to apply:
```sql
-- Add country column to profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS country text;

-- Update handle_new_user trigger to capture country
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, extensions
AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, country)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'country'
  );
  RETURN NEW;
END;
$$;
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat: add country column to profiles + update trigger"
```

---

### Task 2: HTML — add País select to auth form

**Files:**
- Modify: `index.html` (auth modal form, ~line 1347)

- [ ] **Step 1: Add country select after auth-name-wrap**

Insert after `</div>` closing `auth-name-wrap`:
```html
<div id="auth-country-wrap" class="auth-form-field" style="display:none">
  <label for="auth-modal-country">País</label>
  <select id="auth-modal-country">
    <option value="">— Selecciona tu país —</option>
    <!-- flat list: WC2026 + CONMEBOL/CONCACAF non-qualified + Otro -->
  </select>
</div>
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add País select to auth registration form"
```

---

### Task 3: auth.js — wire up country field

**Files:**
- Modify: `js/auth.js`

- [ ] **Step 1: Update setAuthTab() to show/hide country**
- [ ] **Step 2: Update signUp() to accept and pass country**
- [ ] **Step 3: Update handleAuthSubmit() to read country value**
- [ ] **Step 4: Update refreshAuthState() to set window.__authState**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: wire country field in auth.js + expose __authState"
```

---

### Task 4: index.html — fixture cards clickable

**Files:**
- Modify: `index.html` (CSS ~line 965+, renderTeamFixtures ~line 2984, inline script)

- [ ] **Step 1: Add fixture-cta CSS**
- [ ] **Step 2: Add handleFixtureClick() global function**
- [ ] **Step 3: Modify renderTeamFixtures() to add onclick + fixture-cta class**

- [ ] **Step 4: Commit + push**

```bash
git commit -m "feat: make fixture cards clickable — open auth modal"
git push
```
