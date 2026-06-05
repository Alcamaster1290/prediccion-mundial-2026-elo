# Guia admin: codigos premium

Esta guia documenta como generar codigos premium y como operar la app interna. Los codigos se guardan como hash SHA-256 en Supabase; el plaintext solo se muestra una vez cuando se genera.

## App interna

URL local o publicada:

```text
admin/premium-codes.html
```

Flujo:

1. Inicia sesion con una cuenta Supabase Auth.
2. La app llama `has_staff_role('admin')`.
3. Si la cuenta es admin, puedes generar un codigo con notas internas.
4. La app llama `admin_create_premium_code`, muestra el plaintext solo se muestra una vez y lista metadata segura con `admin_list_premium_codes`.

La URL puede ser publica. La seguridad no depende de esconder el HTML: depende de Supabase Auth, `app_private.staff_roles`, RLS, permisos SQL y RPCs server-side.

## Requisitos de seguridad

- `SUPABASE_SERVICE_KEY` nunca va en el frontend ni en archivos publicos.
- La app usa solo `SUPABASE_ANON_KEY`, que es publica y esta protegida por RLS/RPCs.
- `premium_codes.code_hash` no se devuelve al navegador.
- El navegador no inserta directo en `premium_codes`.
- Solo usuarios con rol `admin` en `app_private.staff_roles` pueden ejecutar las RPCs admin.

## Advisor de Supabase

Pueden aparecer estas advertencias esperadas:

- `rls_enabled_no_policy` sobre `public.premium_codes`: es intencional porque `anon` y `authenticated` no tienen grants directos sobre la tabla.
- `authenticated_security_definer_function_executable` sobre las RPCs admin: es intencional para que la app estatica pueda llamar RPCs; cada funcion valida `auth.uid()` y `has_staff_role('admin')` antes de hacer trabajo sensible.

Para dar rol admin a un usuario, usa SQL seguro desde Supabase Dashboard o una sesion con service role:

```sql
insert into app_private.staff_roles (user_id, role)
values ('USER_UUID', 'admin')
on conflict (user_id) do update
set role = excluded.role,
    updated_at = now();
```

## Alternativa CLI

La CLI existente sigue disponible para emergencias o tareas desde terminal. Requiere variables de entorno:

```powershell
$env:SUPABASE_URL="https://hqgrgcvtzzsjmjjqqqjf.supabase.co"
$env:SUPABASE_SERVICE_KEY="TU_SERVICE_ROLE_KEY"
python scripts\admin_premium_codes.py create --notes "alvarojohn1290@gmail.com - premium"
```

Para listar metadata sin hashes:

```powershell
python scripts\admin_premium_codes.py list
```

## Checklist operativo

1. Confirma el email o usuario que recibira premium.
2. Genera el codigo desde `admin/premium-codes.html`.
3. Copia el plaintext inmediatamente.
4. Envia el codigo al usuario por el canal acordado.
5. Registra en notas internas una referencia como email, pago o campaña.
6. Si pierdes el plaintext, genera otro codigo; no se puede recuperar desde Supabase.

## Verificacion de usuario

Para revisar manualmente si un usuario ya tiene premium:

```sql
select id, email, full_name, is_premium, created_at
from public.profiles
where email = 'alvarojohn1290@gmail.com';
```

Para revisar codigos usados por un usuario:

```sql
select id, is_used, used_at, created_at, notes
from public.premium_codes
where used_by = 'USER_UUID'
order by created_at desc;
```
