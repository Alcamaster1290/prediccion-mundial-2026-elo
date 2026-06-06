Carpeta para la foto de la figura clave de cada selección.
Máximo UNA imagen por equipo.

Convención: {código-equipo}-{apellido}.jpg  (o .webp / .png)
Resolución mínima recomendada: 400 x 500 px (retrato, portrait)

NOTA: Dos equipos usan códigos legacy distintos al estándar alpha-3:
  Japón    -> "jap" (no "jpn")
  Curazao  -> "cur" (no "cuw")

Estado auditado: 24 imágenes locales al 6 junio 2026.
No agregar retratos autogenerados. Si falta imagen real/verificable, dejar pendiente.

Figuras con imagen local:
  aut-alaba.webp       -> David Alaba          (Austria)
  bel-debruyne.webp    -> Kevin De Bruyne      (Bélgica)
  bih-dzeko.jpg        -> Edin Džeko           (Bosnia)
  bra-vinicius.webp    -> Vinicius Jr.         (Brasil)
  civ-adingra.jpg      -> Simon Adingra        (Costa de Marfil)
  cod-mbemba.webp      -> Chancel Mbemba       (RD del Congo)
  col-diaz.webp        -> Luis Díaz            (Colombia)
  cpv-rodrigues.jpg    -> Garry Rodrigues      (Cabo Verde)
  cur-bacuna.jpg       -> Leandro Bacuna       (Curazao) [usa "cur"]
  eng-kane.webp        -> Harry Kane           (Inglaterra)
  esp-yamal.png        -> Lamine Yamal         (España)
  fra-mbappe.webp      -> Kylian Mbappé        (Francia)
  ger-wirtz.webp       -> Florian Wirtz        (Alemania)
  hti-bellegarde.webp  -> Jean-Ricner Bellegarde (Haití)
  jap-kubo.webp        -> Takefusa Kubo        (Japón) [usa "jap"]
  kor-son.jpg          -> Son Heung-min        (Corea del Sur)
  nor-haaland.webp     -> Erling Haaland       (Noruega)
  nzl-wood.jpg         -> Chris Wood           (Nueva Zelanda)
  por-ronaldo.jpg      -> Cristiano Ronaldo    (Portugal)
  sco-mcginn.jpg       -> John McGinn          (Escocia)
  sui-xhaka.webp       -> Granit Xhaka         (Suiza)
  swe-gyokeres.jpg     -> Viktor Gyökeres      (Suecia)
  tun-mejbri.jpg       -> Hannibal Mejbri      (Túnez)
  usa-pulisic.webp     -> Christian Pulisic    (EE.UU.)

Fuente auditada de convocatorias:
  Manifiesto completo: data/alterfutbol_sources.json
  Scraper reproducible: scripts/scrape_alterfutbol_news.py
  Página base scrapeada: https://www.alterfutbol.com/noticias/

Resumen del scrape:
  42 selecciones con artículo directo y lista de 26 jugadores parseada.
  1 selección con artículo directo pero lista no parseada automáticamente: Noruega.
  5 selecciones sin artículo directo encontrado en /noticias/: Curazao, Japón, Túnez,
    Arabia Saudita y Jordania.

Artículos directos principales (AlterFutbol):
  mex México        -> https://www.alterfutbol.com/concacaf/mexico/los-convocados-de-mexico-al-mundial-2026-el-analisis-de-la-lista/
  zaf Sudáfrica    -> https://www.alterfutbol.com/africa/sudafrica/sudafrica-anuncio-sus-convocados-para-el-mundial-2026-el-analisis-de-la-lista/
  kor Corea del Sur-> https://www.alterfutbol.com/asia/corea-del-sur/corea-del-sur-confirmo-sus-26-convocados-para-el-mundial-2026-analisis-historia-y-mejores-jugadores/
  cze Rep. Checa   -> https://www.alterfutbol.com/europa/republica-checa/republica-checa-oficializo-su-lista-para-el-mundial-2026-analisis-tactico/
  can Canadá       -> https://www.alterfutbol.com/concacaf/canada/canada-oficializo-sus-convocados-para-el-mundial-2026-el-analisis-de-la-lista/
  bih Bosnia       -> https://www.alterfutbol.com/europa/bosnia/bosnia-dio-la-primera-lista-del-mundial-2026-los-convocados-y-el-analisis-tactico/
  qat Qatar        -> https://www.alterfutbol.com/asia/medio-oriente/qatar/qatar-anuncio-los-convocados-al-mundial-2026-el-analisis-de-la-lista/
  sui Suiza        -> https://www.alterfutbol.com/europa/suiza/suiza-confirmo-sus-26-convocados-para-el-mundial/
  bra Brasil       -> https://www.alterfutbol.com/sudamerica/brasil/brasil-anuncio-los-convocados-para-el-mundial-2026-la-sorpresa-de-neymar-y-las-principales-ausencias/
  mar Marruecos    -> https://www.alterfutbol.com/africa/marruecos/marruecos-confirmo-los-convocados-al-mundial-2026-el-analisis-de-la-lista/
  hti Haití        -> https://www.alterfutbol.com/concacaf/haiti/haiti-confirmo-sus-26-convocados-para-el-mundial-2026-analisis-su-historia-y-mejores-jugadores/
  sco Escocia      -> https://www.alterfutbol.com/europa/escocia/escocia-anuncio-sus-convocados-al-mundial-2026-lista-ausencias-y-analisis-tactico/
  usa EE.UU.       -> https://www.alterfutbol.com/concacaf/estados-unidos/estados-unidos-anuncio-sus-convocados-al-mundial-2026-analisis-de-la-lista/
  mar/pan antes pendientes ahora tienen artículo directo en AlterFutbol y assets XI locales.

Imágenes de portada/equipo:
  Las URL exactas de imagen destacada por selección están en data/alterfutbol_sources.json
  como "featured_image". No se usan como retrato de figura clave salvo validación manual.
