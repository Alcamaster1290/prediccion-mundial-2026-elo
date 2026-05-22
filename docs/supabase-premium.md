# Supabase Premium — Referencia Técnica

## Arquitectura del flujo de acceso premium

```
Usuario                Frontend (GitHub Pages)         Supabase
──────                 ───────────────────────         ────────
                       index.html
                       js/auth.js                       auth.users
[Registro/Login] ──→   SupaAuth.signUp/signIn ────→    profiles (trigger)
[Ver sección]   ──→    PremiumSection.onAuthChange
                       └─ si premium=false:
[Pago Yape/PP]         renderPaymentModal()
[Recibe código] ──→    PremiumSection.submitCode()
                       └─ SupaAuth.getClient()
                              .rpc('redeem_premium_code') ────→ premium_codes
                                                               profiles.is_premium=true
[Premium activo] ←──   PremiumSection.loadPredictions() ←── predictions (RLS)
```

## Tabla: profiles

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | FK auth.users |
| email | text | Sincronizado del registro |
| full_name | text | Opcional |
| is_premium | boolean | Solo modificable via RPC |
| created_at | timestamptz | Auto |
| updated_at | timestamptz | Auto, actualizado por RPC |

**Políticas RLS:**
- SELECT: `auth.uid() = id`
- UPDATE: `auth.uid() = id` (no puede cambiar `is_premium` directamente)

## Tabla: premium_codes

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| code_hash | text | SHA-256 del código en texto plano |
| is_used | boolean | false hasta ser canjeado |
| used_by | uuid | FK auth.users |
| used_at | timestamptz | Momento del canje |
| notes | text | Uso interno admin |

**Políticas RLS:** NINGUNA — solo accesible via RPC SECURITY DEFINER

## Tabla: predictions

| Campo | Tipo | Notas |
|---|---|---|
| match_id | text | Referencia a match_context.json |
| group_code | text | A-L |
| matchday | integer | 1-3 |
| team_a / team_b | text | Código ISO |
| team_a_win_probability | numeric(5,2) | 0-100 |
| draw_probability | numeric(5,2) | |
| team_b_win_probability | numeric(5,2) | |
| global_tag | text | Etiqueta narrativa |
| team_a_context | text | Análisis equipo A |
| team_b_context | text | Análisis equipo B |
| explanation | text | Razonamiento del pronóstico |
| is_premium | boolean | default true |
| published | boolean | false hasta publicar manualmente |

**Constraint:** suma de probabilidades entre 99.5 y 100.5

**Política RLS:**
```sql
SELECT WHERE published = true AND is_premium = true
AND EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_premium = true)
```

## RPC: redeem_premium_code

**Firma:** `redeem_premium_code(input_code text) RETURNS json`

**Flujo:**
1. Verificar `auth.uid()` — rechazar si null
2. Verificar que el usuario no sea ya premium
3. Hashear `input_code` con SHA-256
4. Buscar `code_hash` en `premium_codes` donde `is_used = false`
5. Si no existe: devolver error genérico (no revelar detalle)
6. Marcar código como usado
7. Actualizar `profiles.is_premium = true`
8. Devolver `{success: true, message: "..."}`

**Seguridad:** `SECURITY DEFINER` — se ejecuta con permisos del owner, bypasea RLS en `premium_codes`. El acceso de usuarios normales a esta función está restringido a `authenticated`.

## Variables de entorno

| Variable | Dónde encontrarla | Seguridad |
|---|---|---|
| `SUPABASE_URL` | Supabase → Settings → API → Project URL | Puede estar en frontend |
| `SUPABASE_ANON_KEY` | Supabase → Settings → API → anon public | Puede estar en frontend (RLS protege) |
| `service_role key` | Supabase → Settings → API → service_role | **NUNCA en frontend** |

## Extensiones requeridas

- `pgcrypto` — para `digest()` y `encode()` en el hash SHA-256

Activar en Supabase: ya viene habilitada por defecto en todos los proyectos.

## Estrategia de generación de códigos premium

**Recomendado para el MVP:** códigos alfanuméricos legibles generados manualmente.

Formato sugerido: `WWCXXXXX-YYYY` donde:
- `WWC` = prefijo fijo
- `XXXXX` = 5 caracteres aleatorios (mayúsculas + números)
- `YYYY` = año o mes abreviado

Ejemplo: `WWCAB3F7-MAY26`

**Generación segura local:**
```python
import secrets, string
chars = string.ascii_uppercase + string.digits
code = 'WWC' + ''.join(secrets.choice(chars) for _ in range(5)) + '-MAY26'
print(code)  # Copiar y usar en el INSERT de 04_admin_codes.sql
```

## Limitaciones del MVP

1. No hay reset de contraseña UI (solo vía Supabase dashboard)
2. No hay OAuth (Google, etc.)
3. Las predicciones se insertan manualmente (no hay panel admin)
4. Un código = un usuario (no se pueden reusar)
5. No hay expiración de códigos premium (perpetuo hasta revocar manualmente)
6. No hay notificaciones automáticas al usuario tras el pago
