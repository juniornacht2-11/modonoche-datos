#!/usr/bin/env python3
"""Ciudades de otros países para el buscador de MODO NOCHE (GeoNames, CC BY 4.0).
Salida: salida_ciudades/ciudades.json  -> se copia a la web como datos/ciudades.json
Formato: {"meta":{...}, "paises":{"PT":"Portugal",...}, "ciudades":[[codigo, nombre, lat, lng, poblacion, pais, region, [variantes]], ...]}
- codigo: país + id de GeoNames (p. ej. «PT2267057»), para no chocar con los códigos INE de España (5 cifras).
- nombre: el nombre en español si GeoNames lo tiene (Londres, Lisboa, Múnich); si no, el local.
- variantes: nombre local y nombres en otros idiomas (para encontrar «London», «Lisbon», «München»…)."""
import io, os, sys, json, zipfile, urllib.request, collections, re
PAISES = {'PT': 'Portugal', 'IT': 'Italia', 'FR': 'Francia', 'DE': 'Alemania', 'NL': 'Países Bajos', 'BE': 'Bélgica', 'GB': 'Reino Unido', 'IE': 'Irlanda',
          'GR': 'Grecia', 'HR': 'Croacia', 'AT': 'Austria', 'CH': 'Suiza'}
MIN_POB = int(os.environ.get('MIN_POB', '8000'))
OUT = 'salida_ciudades'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE/1.0 (datos abiertos; github.com/juniornacht2-11/modonoche-datos)'}
def bajar(url):
    print('descargando', url, flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r: return r.read()
z = zipfile.ZipFile(io.BytesIO(bajar('https://download.geonames.org/export/dump/cities5000.zip')))
ciudades = {}
for line in z.read('cities5000.txt').decode('utf-8').splitlines():
    f = line.split('\t')
    gid, name, ascii_, alt, lat, lng, fclass, fcode, cc, admin1, pop = f[0], f[1], f[2], f[3], float(f[4]), float(f[5]), f[6], f[7], f[8], f[10], int(f[14] or 0)
    if cc not in PAISES or fclass != 'P' or pop < MIN_POB or fcode in ('PPLX',): continue
    ciudades[gid] = {'name': name, 'lat': round(lat, 4), 'lng': round(lng, 4), 'pop': pop, 'cc': cc, 'a1': admin1}
print('ciudades', len(ciudades), flush=True)
regiones = {}
for line in bajar('https://download.geonames.org/export/dump/admin1CodesASCII.txt').decode('utf-8').splitlines():
    k, nombre, *_ = line.split('\t'); regiones[k] = nombre
# nombres en otros idiomas (el archivo es grande: se lee en streaming)
LANGS = {'es', 'en', 'pt', 'it', 'fr', 'de', 'nl', 'ca'}
alt = collections.defaultdict(dict)
z2 = zipfile.ZipFile(io.BytesIO(bajar('https://download.geonames.org/export/dump/alternateNamesV2.zip')))
with z2.open('alternateNamesV2.txt') as fh:
    for raw in io.TextIOWrapper(fh, encoding='utf-8'):
        p = raw.rstrip('\n').split('\t')
        if len(p) < 4 or p[1] not in ciudades or p[2] not in LANGS: continue
        if len(p) > 7 and (p[6] == '1' or p[7] == '1'): continue   # coloquiales o históricos
        pref = len(p) > 4 and p[4] == '1'
        d = alt[p[1]]
        if p[2] not in d or pref: d[p[2]] = p[3]
salida = []
for gid, c in sorted(ciudades.items(), key=lambda kv: -kv[1]['pop']):
    a = alt.get(gid, {})
    nombre = a.get('es') or c['name']
    vars_ = []
    for v in [c['name']] + [a[l] for l in ('en', 'pt', 'it', 'fr', 'de', 'nl', 'ca') if l in a]:
        if v and v != nombre and v not in vars_ and len(v) <= 40 and not re.search(r'[Ͱ-ϿЀ-ӿ]', v): vars_.append(v)
    salida.append([c['cc'] + gid, nombre, c['lat'], c['lng'], c['pop'], c['cc'], regiones.get(f"{c['cc']}.{c['a1']}", ''), vars_[:6]])
# Barrios que GeoNames da como «ciudad» (freguesias de Lisboa, distritos de grandes ciudades…): pasan a ser barrios de su ciudad
import math
def kmd(a, b): return math.hypot((a[2] - b[2]) * 111, (a[3] - b[3]) * 111 * math.cos(math.radians(a[2])))
def radio(pop): return 12.0 if pop >= 1_000_000 else 8.0 if pop >= 300_000 else 5.0 if pop >= 100_000 else 3.5 if pop >= 30_000 else 2.5
grandes = [x for x in salida if x[4] >= 300_000]
finales, barrios = [], []
for x in salida:
    madre = next((g for g in grandes if g is not x and g[5] == x[5] and g[4] >= 3 * x[4] and kmd(g, x) < 0.55 * radio(g[4])), None)
    if madre: barrios.append([x[1], madre[0], x[2], x[3], 's'])
    else: finales.append(x)
print('pasan a barrio', len(barrios), barrios[:8])
salida = finales
meta = {'fuente': 'GeoNames (www.geonames.org), licencia CC BY 4.0', 'poblacion_minima': MIN_POB, 'paises': len(PAISES), 'ciudades': len(finales), 'barrios': len(barrios)}
json.dump({'meta': meta, 'paises': PAISES, 'ciudades': salida, 'barrios': barrios}, open(f'{OUT}/ciudades.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('escritas', len(salida), 'tamaño', os.path.getsize(f'{OUT}/ciudades.json'))
por_pais = collections.Counter(x[5] for x in salida); print(dict(por_pais))
