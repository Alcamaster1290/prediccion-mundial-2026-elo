# 🌍 Mundial 2026 — Predicciones y Análisis

Proyecto web para análisis táctico, ELO de clubes y predicciones del Mundial 2026 (Canadá · México · Estados Unidos).

Fuente de análisis: [AlterFutbol](https://alterfutbol.com) · ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/)

---

## 📁 Estructura del proyecto

```
mundial-2026/
│
├── index.html              # App principal (dark editorial, navegación por grupo)
├── README.md
│
├── assets/
│   ├── flags/              # Banderas en SVG — código ISO 3166-1 alpha-3
│   │   ├── bih.svg         # Bosnia y Herzegovina
│   │   ├── sui.svg         # Suiza
│   │   ├── swe.svg         # Suecia
│   │   ├── kor.svg         # Corea del Sur
│   │   └── ...             # una por selección clasificada (48 total)
│   │
│   ├── players/            # Foto de la figura clave — UNA por selección
│   │   ├── bih-dzeko.jpg          # Bosnia → Edin Džeko
│   │   ├── sui-xhaka.jpg          # Suiza → Granit Xhaka
│   │   ├── swe-gyokeres.jpg       # Suecia → Viktor Gyökeres
│   │   ├── kor-son.jpg            # Corea del Sur → Son Heung-min
│   │   ├── bra-vinicius.jpg       # Brasil → Vinicius Jr.
│   │   ├── fra-mbappe.jpg         # Francia → Kylian Mbappé
│   │   ├── por-ronaldo.jpg        # Portugal → Cristiano Ronaldo
│   │   └── ...
│   │
│   └── xi/                 # XI Ideal por selección — capturas de AlterFutbol
│       ├── bih-xi.png      # Bosnia XI (4-4-2)
│       ├── sui-xi.png      # Suiza XI (4-3-3)
│       ├── swe-xi.png      # Suecia XI (3-4-2-1)
│       ├── kor-xi.png      # Corea del Sur XI (3-4-2-1)
│       └── ...
│
├── css/
│   └── styles.css          # Estilos extraídos de index.html
│
├── js/
│   ├── main.js             # Inicialización, nav activo, ELO color coding
│   └── filters.js          # Filtros por grupo / estado de análisis (futuro)
│
└── data/
    ├── teams.json          # Planteles completos con ELO por club
    └── groups.json         # Grupos, fixtures y fechas oficiales FIFA
```

---

## 🗂️ Convenciones de nombres

### `assets/flags/`
- Código ISO 3166-1 **alpha-3** en minúsculas: `bih.svg`, `sui.svg`, `swe.svg`, `kor.svg`
- Fuente recomendada: [flagcdn.com](https://flagcdn.com) → `https://flagcdn.com/{code}.svg`
- Alternativa npm: `flag-icons` (CSS sprites)

### `assets/players/`
- Formato: `{código-equipo}-{apellido}.jpg`
- Resolución mínima recomendada: **400 × 500 px** (portrait)
- Máximo **1 jugador por selección** — la figura más reconocida o el mejor ELO de club
- Fuentes libres de derechos: Wikimedia Commons, transfermarkt (preview), sitios oficiales de federaciones

| Equipo | Archivo | Jugador | Club (ELO) |
|--------|---------|---------|------------|
| Bosnia | `bih-dzeko.jpg` | Edin Džeko | Schalke 04 |
| Suiza | `sui-xhaka.jpg` | Granit Xhaka | Sunderland |
| Suecia | `swe-gyokeres.jpg` | Viktor Gyökeres | Arsenal (2102) |
| Corea del Sur | `kor-son.jpg` | Son Heung-min | LAFC |
| Brasil | `bra-vinicius.jpg` | Vinicius Jr. | Real Madrid (2004) |
| Haití | `hti-bellegarde.jpg` | J.-R. Bellegarde | Wolverhampton |
| Escocia | `sco-mcginn.jpg` | John McGinn | Aston Villa |
| Costa de Marfil | `civ-adingra.jpg` | Simon Adingra | AS Monaco |
| Bélgica | `bel-debruyne.jpg` | Kevin De Bruyne | Napoli |
| Nueva Zelanda | `nzl-wood.jpg` | Chris Wood | Nottingham Forest |
| Cabo Verde | `cpv-rodrigues.jpg` | Garry Rodrigues | Apollon Limassol |
| Francia | `fra-mbappe.jpg` | Kylian Mbappé | Real Madrid (2004) |
| Austria | `aut-alaba.jpg` | David Alaba | Real Madrid (2004) |
| Portugal | `por-ronaldo.jpg` | Cristiano Ronaldo | Al-Nassr |
| RD del Congo | `cod-mbemba.jpg` | Chancel Mbemba | Lille |

### `assets/xi/`
- Formato: `{código-equipo}-xi.png`
- Capturas de pantalla de las imágenes de XI Ideal publicadas por AlterFutbol
- Recortar al área del XI (excluir bordes del post si es necesario)
- Resolución sugerida: **800 × 900 px**

---

## 📊 Estructura de `data/teams.json`

```json
{
  "teams": [
    {
      "id": "bih",
      "name": "Bosnia y Herzegovina",
      "group": "B",
      "flag": "assets/flags/bih.svg",
      "xi_image": "assets/xi/bih-xi.png",
      "star_player": {
        "name": "Edin Džeko",
        "image": "assets/players/bih-dzeko.jpg",
        "club": "Schalke 04",
        "elo": null
      },
      "dt": "Sergej Barbarez",
      "scheme": "4-4-2",
      "analyzed": true,
      "players": [
        {
          "number": 22,
          "pos": "DEL",
          "name": "Edin Džeko",
          "age": 40,
          "club": "Schalke 04",
          "country": "Alemania",
          "elo": null,
          "titular": true
        }
      ]
    }
  ]
}
```

---

## 📊 Estructura de `data/groups.json`

```json
{
  "groups": [
    {
      "id": "A",
      "teams": ["mex", "zaf", "kor", "cze"],
      "fixtures": [
        {
          "jornada": 1,
          "date": "2026-06-11",
          "home": "mex",
          "away": "zaf",
          "venue": "Estadio Azteca, Ciudad de México"
        }
      ]
    }
  ]
}
```

---

## 🎨 Paleta de colores por grupo

| Grupo | Color CSS var | Hex |
|-------|--------------|-----|
| A | `--grp-a` | `#e55c5c` |
| B | `--grp-b` | `#3b8beb` |
| C | `--grp-c` | `#10b981` |
| E | `--grp-e` | `#f97316` |
| F | `--grp-f` | `#f59e0b` |
| G | `--grp-g` | `#8b5cf6` |
| H | `--grp-h` | `#ec4899` |
| I | `--grp-i` | `#06b6d4` |
| J | `--grp-j` | `#84cc16` |
| K | `--grp-k` | `#d97706` |
| L | `--grp-l` | `#94a3b8` |

---

## ✅ Estado del análisis

| Selección | Grupo | XI cargado | Tabla ELO | Análisis táctico |
|-----------|-------|-----------|-----------|-----------------|
| 🇧🇦 Bosnia | B | ✅ | ✅ 26 jugadores | ✅ |
| 🇨🇭 Suiza | B | ✅ | ✅ 26 jugadores | ✅ |
| 🇸🇪 Suecia | F | ✅ | ✅ 26 jugadores | ✅ |
| 🇰🇷 Corea del Sur | A | ✅ | ✅ 26 jugadores | ✅ |
| 🇧🇷 Brasil | C | ⏳ | ✅ 26 jugadores | ✅ |
| 🇭🇹 Haití | C | ⏳ | ✅ 26 jugadores | ✅ |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | C | ⏳ | ✅ 26 jugadores | ✅ |
| 🇨🇮 Costa de Marfil | E | ⏳ | ✅ 22 jugadores | ✅ |
| 🇧🇪 Bélgica | G | ⏳ | ✅ 26 jugadores | ✅ |
| 🇳🇿 Nueva Zelanda | G | ⏳ | ✅ 26 jugadores | ✅ |
| 🇨🇻 Cabo Verde | H | ⏳ | ✅ 26 jugadores | ✅ |
| 🇫🇷 Francia | I | ⏳ | ✅ 26 jugadores | ✅ |
| 🇦🇹 Austria | J | ⏳ | ✅ 22 jugadores | ✅ |
| 🇵🇹 Portugal | K | ⏳ | ✅ 26 jugadores | ✅ |
| 🇨🇩 RD del Congo | K | ⏳ | ✅ 22 jugadores | ✅ |

---

## 🚀 Cómo usar

```bash
git clone https://github.com/tu-usuario/mundial-2026.git
cd mundial-2026

# No hay build step — abrir directamente en el navegador
open index.html

# O servir localmente (recomendado para los fetch() de JSON)
npx serve .
# o
python3 -m http.server 8080
```

> **Nota:** Para cargar los archivos JSON con `fetch()` se necesita un servidor local (CORS). Con `open index.html` directo funciona todo excepto la carga dinámica de datos.

---

## 📌 Roadmap

- [ ] Integrar `teams.json` para carga dinámica de planteles
- [ ] Agregar imágenes de jugadores estrella (`assets/players/`)
- [ ] Subir imágenes XI Ideal de los 15 equipos (`assets/xi/`)
- [ ] Completar análisis de todos los grupos (D, F restante, L)
- [ ] Sección de predicciones por partido (fase de grupos)
- [ ] Comparador de ELO entre equipos del mismo grupo
- [ ] Modo predicción: votar resultado de cada partido

---

*Datos actualizados al 20 de mayo de 2026. Fuentes: AlterFutbol · worldclubratings.com · FIFA*
