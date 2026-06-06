Inventario de assets y origen de datos
Actualizado: 6 junio 2026

Objetivo
Este directorio guarda los archivos visuales usados por la pagina publica y por
los perfiles de seleccion exportados a Supabase. No se agregan assets
autogenerados cuando el dato debe ser verificable.

Resumen de cobertura
- 48 banderas locales en assets/flags.
- 46 imagenes locales de XI probable en assets/xi.
- 24 retratos locales de jugadores destacados en assets/players.
- 46 selecciones con plantel de 26 jugadores en data/teams.json.
- 46 selecciones con perfil HTML publicado en index.html.
- 46 selecciones con analyzed=true en data/teams.json.
- 1196 jugadores con pais/club asignado desde la tabla de AlterFutbol.
- 2 selecciones pendientes sin articulo directo/lista confiable: ksa y jor.

Fuentes principales
- Convocatorias, tabla de jugadores, club, pais del club, ELO mostrado por club,
  textos tacticos, ausencias y enlaces de imagen: AlterFutbol.
- Pagina base scrapeada: https://www.alterfutbol.com/noticias/
- Manifest de fuentes por equipo: data/alterfutbol_sources.json.
- Datos consolidados para la app: data/teams.json.
- Ratings ELO de clubes usados por el pipeline: worldclubratings.com.

Flujo de datos local
- scripts/scrape_alterfutbol_news.py encuentra articulos desde /noticias/,
  extrae enlaces, imagen destacada, tablas de jugadores y metadatos de fuente.
- scripts/enrich_alterfutbol_xi_assets.py descarga/enriquece las imagenes de XI
  y guarda xi_source_url en data/teams.json.
- scripts/derive_schemes_from_xi.py completa scheme desde la imagen del XI cuando
  el articulo no trae la formacion explicita.
- scripts/mark_team_starters.py marca players[].titular a partir del XI probable.
- scripts/render_team_sections.py publica las secciones HTML fuenteadas, completa
  ausencias desde el articulo, actualiza analyzed=true y mantiene el bloque de
  pendientes.
- scripts/export_to_supabase.py exporta team_profiles, team_profile_premium,
  players, national_elo_ratings y snapshots/simulacion a Supabase.

assets/flags
- Convencion: {codigo-equipo}.svg.
- Cobertura: 48/48 selecciones.

assets/xi
- Convencion: {codigo-equipo}-xi.png.
- Cobertura: 46/48 selecciones.
- Origen: imagen de formacion publicada en el articulo de AlterFutbol o captura
  verificable de esa imagen.
- Campos alimentados: xi_image, xi_source_url, scheme cuando aplica,
  players[].titular y, para los 22 equipos squad-only, dt/dt_source/dt_source_url.
- Pendientes sin XI local: ksa Arabia Saudita, jor Jordania.
- Ver detalle por archivo en assets/xi/README.txt.

assets/players
- Convencion: {codigo-equipo}-{apellido}.jpg|webp|png.
- Cobertura actual: 24 retratos locales.
- Para los 22 perfiles nuevos, la pagina deja placeholder en "Jugador destacado"
  hasta subir retratos verificables en el siguiente commit.
- No usar imagenes generadas para retratos de jugadores.
- Ver detalle por archivo en assets/players/README.txt.

Codigos legacy de assets
- Japon usa jap para assets historicos, aunque el codigo de datos es jpn.
- Curazao usa cur para assets historicos, aunque el codigo de datos es cuw.

Estado de publicacion
- Publicados con perfil completo: 46 selecciones.
- Pendientes de perfil por falta de fuente directa confiable: Arabia Saudita
  (ksa) y Jordania (jor).
- Los perfiles nuevos usan el mismo layout que los perfiles existentes:
  sistema de juego, ausencias notables, imagen XI ideal, tabla de jugadores,
  partidos de grupo y ruta eliminatoria posible.

Notas de calidad
- dt_source se conserva solo como auditoria local en data/teams.json y no se
  muestra en la pagina ni se exporta a Supabase.
- Las ausencias se extraen de frases con senal directa de baja/lesion/exclusion
  dentro del articulo. Menciones historicas no relacionadas con la convocatoria
  actual se filtran.
- Si falta una fuente directa y verificable, el dato queda pendiente.
