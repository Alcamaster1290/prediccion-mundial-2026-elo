Carpeta para banderas SVG de los 48 países clasificados al Mundial 2026.

Convención de nombres: {código ISO 3166-1 alpha-3 en minúsculas}.svg
Ejemplo: bih.svg, sui.svg, swe.svg, kor.svg, bra.svg

Fuente recomendada: https://flagcdn.com/{code}.svg
Script de descarga:
  for code in bih sui swe kor bra hti sco civ bel nzl cpv fra aut por cod mex usa can; do
    curl -o $code.svg https://flagcdn.com/$code.svg
  done
