Carpeta para las imágenes del XI Ideal de cada selección.
Fuente: capturas de pantalla o imágenes de formación publicadas por AlterFutbol.

Convención: {código-equipo}-xi.png
Resolución sugerida: 800 x 900 px
Formato: PNG (con o sin fondo)

NOTA: Dos equipos usan códigos legacy distintos al estándar alpha-3:
  Japón    -> "jap" (no "jpn")
  Curazao  -> "cur" (no "cuw")

Estado auditado: 46 imágenes locales al 6 junio 2026.
No agregar XI autogenerados. Si no hay imagen real o captura validada, dejar pendiente.

Uso de datos:
  data/teams.json guarda xi_image, xi_source_url, scheme, scheme_source y tactics.
  scheme_source diferencia article_text de xi_image cuando la formación se validó
  visualmente desde el XI local. players[].titular está marcado para los 46 equipos
  cargados en data/teams.json, con 11 titulares exactos por selección.

Excepción auditada:
  aus-xi.png tiene título de Australia pero lista nombres de Chequia. Los titulares
  de Australia se marcaron desde el análisis textual por puesto del mismo artículo
  de AlterFutbol, no desde esa lámina.

Schemes derivados desde xi_image:
  qat -> 4-3-3
  egy -> 4-3-3
  sen -> 4-3-3
  uzb -> 3-4-2-1

Imágenes locales disponibles:
  alg-xi.png   OK  Argelia
  arg-xi.png   OK  Argentina
  aus-xi.png   OK  Australia
  aut-xi.png   OK  Austria
  bel-xi.png   OK  Bélgica
  bih-xi.png   OK  Bosnia y Herzegovina
  bra-xi.png   OK  Brasil
  can-xi.png   OK  Canadá
  civ-xi.png   OK  Costa de Marfil
  cod-xi.png   OK  RD Congo
  col-xi.png   OK  Colombia
  cpv-xi.png   OK  Cabo Verde
  cro-xi.png   OK  Croacia
  cur-xi.png   OK  Curazao [usa "cur"]
  cze-xi.png   OK  República Checa
  ecu-xi.png   OK  Ecuador
  egy-xi.png   OK  Egipto
  eng-xi.png   OK  Inglaterra
  esp-xi.png   OK  España
  fra-xi.png   OK  Francia
  ger-xi.png   OK  Alemania
  gha-xi.png   OK  Ghana
  hti-xi.png   OK  Haití
  irn-xi.png   OK  Irán
  irq-xi.png   OK  Irak
  jap-xi.png   OK  Japón [usa "jap"]
  kor-xi.png   OK  Corea del Sur
  mar-xi.png   OK  Marruecos
  mex-xi.png   OK  México
  ned-xi.png   OK  Países Bajos
  nor-xi.png   OK  Noruega
  nzl-xi.png   OK  Nueva Zelanda
  pan-xi.png   OK  Panamá
  por-xi.png   OK  Portugal
  pry-xi.png   OK  Paraguay
  qat-xi.png   OK  Qatar
  sco-xi.png   OK  Escocia
  sen-xi.png   OK  Senegal
  sui-xi.png   OK  Suiza
  swe-xi.png   OK  Suecia
  tun-xi.png   OK  Túnez
  tur-xi.png   OK  Turquía
  ury-xi.png   OK  Uruguay
  usa-xi.png   OK  EE.UU.
  uzb-xi.png   OK  Uzbekistán
  zaf-xi.png   OK  Sudáfrica

Pendientes sin XI local:
  ksa -> Arabia Saudita (sin artículo directo encontrado en /noticias/)
  jor -> Jordania (sin artículo directo encontrado en /noticias/)

Fuentes auditadas:
  Manifiesto completo: data/alterfutbol_sources.json
  Scraper reproducible: scripts/scrape_alterfutbol_news.py
  Descarga/enriquecimiento: scripts/enrich_alterfutbol_xi_assets.py
  Página base scrapeada: https://www.alterfutbol.com/noticias/
