import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_admin_premium_migration_creates_hardened_rpcs():
    sql = read("supabase/17_admin_premium_codes.sql").lower()

    assert "create or replace function public.admin_create_premium_code" in sql
    assert "create or replace function public.admin_list_premium_codes" in sql
    assert sql.count("security definer") >= 2
    assert "set search_path = public, pg_temp" in sql
    assert "(select auth.uid())" in sql
    assert "public.has_staff_role('admin')" in sql
    assert "extensions.gen_random_bytes" in sql
    assert "extensions.digest(trim(v_code), 'sha256')" in sql
    assert "insert into public.premium_codes" in sql
    assert "used_by_email text" in sql
    assert "used_by_name text" in sql
    assert "insert into public.premium_audit_log" in sql
    assert "grant execute on function public.admin_create_premium_code(text) to authenticated" in sql
    assert "grant execute on function public.admin_list_premium_codes() to authenticated" in sql
    assert "revoke all on function public.admin_create_premium_code(text) from public, anon" in sql
    assert "revoke all on function public.admin_list_premium_codes() from public, anon" in sql


def test_admin_premium_list_rpc_never_exposes_code_hash():
    sql = read("supabase/17_admin_premium_codes.sql").lower()
    match = re.search(
        r"create or replace function public\.admin_list_premium_codes\(\).*?as \$\$(.*?)\$\$;",
        sql,
        flags=re.S,
    )

    assert match, "admin_list_premium_codes body not found"
    assert "code_hash" not in match.group(1)
    assert "returns table" in sql
    assert "used_by_email" in match.group(1)
    assert "used_by_name" in match.group(1)
    assert "limit 100" in match.group(1)


def test_admin_premium_migration_removes_direct_table_access():
    sql = read("supabase/17_admin_premium_codes.sql").lower()

    assert "revoke all on table public.premium_codes from anon, authenticated" in sql
    assert 'drop policy if exists "premium codes: admin read"' in sql
    assert 'drop policy if exists "premium codes: admin insert"' in sql
    assert 'drop policy if exists "premium codes: admin update"' in sql
    assert "grant select, insert, update, delete on table public.premium_codes to service_role" in sql


def test_admin_code_crypto_fix_qualifies_pgcrypto_and_removes_dev_fixture():
    sql = read("supabase/20_fix_premium_code_crypto.sql").lower()

    assert "create or replace function public.admin_create_premium_code" in sql
    assert "create or replace function public.redeem_premium_code" in sql
    assert "extensions.gen_random_bytes" in sql
    assert "extensions.digest(trim(v_code), 'sha256')" in sql
    assert "extensions.digest(trim(input_code), 'sha256')" in sql
    assert re.search(r"(?<!\.)gen_random_bytes\(9\)", sql) is None
    assert re.search(r"(?<!\.)digest\(trim\(v_code\), 'sha256'\)", sql) is None
    assert re.search(r"(?<!\.)digest\(trim\(input_code\), 'sha256'\)", sql) is None
    assert "used_by_email text" in sql
    assert "used_by_name text" in sql
    assert "01e3ee6d-6f96-4e44-8737-470a64c2f113" in sql
    assert "desarrollo local" in sql


def test_admin_premium_app_is_static_and_rpc_only():
    html = read("admin/premium-codes.html")
    js = read("js/admin-premium-codes.js")

    assert '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>' in html
    assert '<script src="../js/config.js"></script>' in html
    assert '<script src="../js/admin-premium-codes.js"></script>' in html
    assert 'id="admin-premium-create-form"' in html
    assert 'id="admin-premium-code-output"' in html
    assert "SUPABASE_SERVICE_KEY" not in html + js
    assert "service_role" not in js.lower()
    assert ".from('premium_codes')" not in js
    assert '.from("premium_codes")' not in js
    assert "admin_create_premium_code" in js
    assert "admin_list_premium_codes" in js
    assert "used_by_email" in js
    assert "used_by_name" in js
    assert "has_staff_role" in js
    assert "innerHTML" not in js
    assert "textContent" in js
    assert "navigator.clipboard.writeText" in js


def test_admin_premium_docs_cover_secure_operations():
    doc = read("docs/admin-premium-codes.md").lower()

    assert "admin/premium-codes.html" in doc
    assert "plaintext" in doc
    assert "solo se muestra una vez" in doc
    assert "supabase_service_key" in doc
    assert "nunca va en el frontend" in doc
    assert "app_private.staff_roles" in doc
    assert "admin_create_premium_code" in doc
