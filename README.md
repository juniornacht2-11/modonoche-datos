# MODO NOCHE · datos de locales

Cada lunes, GitHub descarga el extracto de OpenStreetMap de España (Geofabrik), prepara un archivo de locales
(discotecas, bares, pubs, salas, restaurantes y alojamientos con nombre) por municipio y lo publica en
https://juniornacht2-11.github.io/modonoche-datos/

- `locales/CÓDIGO_INE.json`: locales de cada municipio (formato de elementos de Overpass: type, id, lat, lon, tags).
- `indice.json`: fecha de los datos y número de locales por municipio.

Datos © colaboradores de OpenStreetMap, licencia ODbL 1.0. No hace falta tocar nada: todo es automático.
