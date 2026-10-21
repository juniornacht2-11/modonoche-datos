#!/usr/bin/env python3
"""
MODO NOCHE · datos semanales de locales (OpenStreetMap)
=======================================================
Descarga el extracto de OpenStreetMap de España (Geofabrik, una sola descarga por ejecución),
se queda con discotecas, bares, pubs, salas, restaurantes y alojamientos con nombre, asigna cada uno
a su municipio (límites municipales de OSM con código INE) y escribe un archivo por municipio:

  publico/locales/MMMMM.json   {"m": código INE, "gen": fecha, "datos": fecha de OSM, "elements": [...]}
  publico/indice.json          municipios con datos y cuántos locales tiene cada uno
  publico/index.html           página informativa

Los «elements» siguen el formato de Overpass (type, id, lat, lon, tags) para que la web los lea igual.
No consulta Overpass ni Nominatim. Solo biblioteca estándar de Python + osmium-tool (apt install osmium-tool).

Uso:  python3 herramientas/generar.py                 (descarga y procesa todo)
      python3 herramientas/generar.py --geojsonseq F    (pruebas: procesa una salida de osmium ya hecha)
"""
from __future__ import annotations
import argparse, datetime as dt, json, math, os, re, subprocess, sys, unicodedata

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PUBLICO = os.path.join(RAIZ, 'publico')
TRABAJO = os.path.join(RAIZ, '.trabajo')
UA = 'MODO-NOCHE-datos/1.0 (https://github.com/juniornacht2-11/modonoche-datos; actualizacion semanal)'
EXTRACTOS = ['https://download.geofabrik.de/europe/spain-latest.osm.pbf',
             'https://download.geofabrik.de/africa/canary-islands-latest.osm.pbf']
FILTRO = ['nwr/amenity=nightclub,music_venue,concert_hall,bar,pub,events_venue,restaurant,theatre',
          'nwr/tourism=hotel,hostel,guest_house,apartment,motel', 'r/admin_level=8']
# Etiquetas que usa la web (app.js · osmRecord). Nada más se publica.
ETIQUETAS = ['name', 'amenity', 'tourism', 'leisure', 'theatre:type', 'cuisine', 'stars', 'rooms',
             'addr:street', 'addr:place', 'addr:housenumber', 'addr:postcode', 'addr:city',
             'website', 'contact:website', 'url', 'reservation:website', 'reservation:url', 'booking',
             'phone', 'contact:phone', 'opening_hours', 'reservation', 'wheelchair', 'live_music', 'diet:vegetarian',
             'website:menu', 'menu:url', 'url:menu', 'outdoor_seating', 'description', 'wikidata', 'wikimedia_commons', 'image',
             'lgbtq', 'music', 'music:genre', 'genre', 'drink:cocktail', 'cocktails', 'karaoke', 'dance:style', 'fee']
FIESTA = {'nightclub', 'music_venue', 'concert_hall', 'bar', 'pub', 'events_venue'}
ALOJ = {'hotel', 'hostel', 'guest_house', 'apartment', 'motel'}
AHORA = dt.datetime.now(dt.timezone.utc)


def log(*a):
    print(*a, flush=True)


def norm(s: str) -> str:
    s = unicodedata.normalize('NFD', s or '')
    return re.sub(r'[^a-z0-9ñ]+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()).strip()


def interesa(t: dict) -> str | None:
    """Tipo de establecimiento que muestra la web, o None."""
    if not (t.get('name') or '').strip():
        return None
    a = t.get('amenity')
    if a == 'restaurant':
        return 'cenas'
    if t.get('tourism') in ALOJ:
        return 'hoteles'
    # leisure=dance no se usa: en España casi siempre son escuelas de baile, no salas de fiesta.
    if a in FIESTA or (a == 'theatre' and t.get('theatre:type') == 'concert_hall'):
        return 'fiesta'
    return None


# ---------- geometría sin dependencias ----------
def anillos(g: dict):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else []


def dentro_anillo(x, y, r):
    d, j = False, len(r) - 1
    for i in range(len(r)):
        xi, yi, xj, yj = r[i][0], r[i][1], r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi:
            d = not d
        j = i
    return d


def dentro(x, y, polis):
    return any(dentro_anillo(x, y, p[0]) and not any(dentro_anillo(x, y, h) for h in p[1:]) for p in polis)


def centroide_anillo(r):
    a = cx = cy = 0.0
    for i in range(len(r) - 1):
        f = r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
        a += f; cx += (r[i][0] + r[i + 1][0]) * f; cy += (r[i][1] + r[i + 1][1]) * f
    if abs(a) < 1e-14:
        return sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r)
    return cx / (3 * a), cy / (3 * a)


def centro(g: dict):
    t = g.get('type')
    if t == 'Point':
        return g['coordinates'][0], g['coordinates'][1]
    polis = anillos(g)
    if polis:
        big = max(polis, key=lambda p: len(p[0]))
        c = centroide_anillo(big[0])
        if dentro(c[0], c[1], polis):
            return c
        return big[0][len(big[0]) // 2][0], big[0][len(big[0]) // 2][1]
    pts = []
    def rec(a):
        if a and isinstance(a[0], (int, float)): pts.append(a)
        else:
            for b in a: rec(b)
    rec(g.get('coordinates') or [])
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None


def simplificar(r, tol=0.0002):
    n = len(r)
    if n < 8:
        return r
    keep = [False] * n; keep[0] = keep[-1] = True; st = [(0, n - 1)]
    while st:
        i, j = st.pop(); ax, ay, bx, by = r[i][0], r[i][1], r[j][0], r[j][1]
        dx, dy = bx - ax, by - ay; ln = math.hypot(dx, dy) or 1e-12; dm, km_ = -1.0, -1
        for k in range(i + 1, j):
            d = abs(dy * r[k][0] - dx * r[k][1] + bx * ay - by * ax) / ln
            if d > dm: dm, km_ = d, k
        if dm > tol and km_ > 0:
            keep[km_] = True; st += [(i, km_), (km_, j)]
    out = [r[k] for k in range(n) if keep[k]]
    return out if len(out) >= 4 else r


class Indice:
    """Rejilla de 0,05° con los términos municipales."""
    def __init__(self):
        self.m, self.g = [], {}
    def anadir(self, cod, polis):
        xs = [p[0] for pl in polis for p in pl[0]]; ys = [p[1] for pl in polis for p in pl[0]]
        b = (min(xs), min(ys), max(xs), max(ys)); i = len(self.m); self.m.append((cod, polis, b))
        for gx in range(math.floor(b[0] * 20), math.floor(b[2] * 20) + 1):
            for gy in range(math.floor(b[1] * 20), math.floor(b[3] * 20) + 1):
                self.g.setdefault((gx, gy), []).append(i)
    def buscar(self, x, y):
        for i in self.g.get((math.floor(x * 20), math.floor(y * 20)), []):
            cod, polis, b = self.m[i]
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and dentro(x, y, polis):
                return cod
        return None


def km(lat1, lng1, lat2, lng2):
    r = math.pi / 180
    a = math.sin((lat2 - lat1) * r / 2) ** 2 + math.cos(lat1 * r) * math.cos(lat2 * r) * math.sin((lng2 - lng1) * r / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def tipo_id(fid: str):
    if fid[:1] == 'a':
        n = int(fid[1:]); return ('way', n // 2) if n % 2 == 0 else ('relation', (n - 1) // 2)
    return {'n': 'node', 'w': 'way', 'r': 'relation'}.get(fid[:1], 'node'), int(re.sub(r'\D', '', fid[1:]) or 0)


def procesar(ruta: str, munis: list) -> dict:
    codigos = {m[0]: m for m in munis}
    idx, crudos = Indice(), []
    st = {'lineas': 0, 'limites': 0, 'limites_validos': 0, 'locales_leidos': 0, 'sin_municipio': 0, 'por_cercania': 0, 'duplicados': 0}
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip().lstrip('\x1e')
            if not linea:
                continue
            try:
                feat = json.loads(linea)
            except ValueError:
                continue
            st['lineas'] += 1
            p, g = feat.get('properties') or {}, feat.get('geometry') or {}
            if p.get('boundary') == 'administrative' and p.get('admin_level') == '8' and g.get('type') in ('Polygon', 'MultiPolygon'):
                st['limites'] += 1
                cod = re.sub(r'\D', '', p.get('ine:municipio') or p.get('ref:ine') or '')
                cod = cod[:5] if len(cod) in (5, 6, 11) else ''
                if cod in codigos:
                    idx.anadir(cod, [[simplificar(r) for r in pl] for pl in anillos(g)]); st['limites_validos'] += 1
                continue
            k = interesa(p)
            if not k:
                continue
            c = centro(g)
            if not c:
                continue
            st['locales_leidos'] += 1
            t, i = tipo_id(str(feat.get('id') or ''))
            tags = {e: str(p[e])[:250] for e in ETIQUETAS if p.get(e) not in (None, '')}
            crudos.append({'type': t, 'id': i, 'lat': round(c[1], 6), 'lon': round(c[0], 6), 'tags': tags, '_k': k})
    por_muni, vistos = {}, {}
    for el in crudos:
        cod = idx.buscar(el['lon'], el['lat'])
        if not cod:
            # punto en el borde (muelle, playa) o municipio sin límite en OSM: el centro municipal más cercano a menos de 3 km
            best, bd = None, 3.0
            for m in munis:
                if m[2] is None: continue
                if abs(m[2] - el['lat']) > 0.05 or abs(m[3] - el['lon']) > 0.07: continue
                d = km(el['lat'], el['lon'], m[2], m[3])
                if d < bd: best, bd = m[0], d
            if not best:
                st['sin_municipio'] += 1; continue
            cod = best; st['por_cercania'] += 1
        clave = (el['_k'], norm(el['tags'].get('name', '')), cod)
        dup = None
        for o in vistos.get(clave, []):
            if abs(o['lat'] - el['lat']) < 0.00045 and abs(o['lon'] - el['lon']) < 0.0006:
                dup = o; break
        if dup:
            for kk, vv in el['tags'].items(): dup['tags'].setdefault(kk, vv)
            st['duplicados'] += 1; continue
        vistos.setdefault(clave, []).append(el)
        por_muni.setdefault(cod, []).append(el)
    for lst in por_muni.values():
        for el in lst: el.pop('_k', None)
        lst.sort(key=lambda e: (e['tags'].get('amenity') or e['tags'].get('tourism') or '', norm(e['tags'].get('name', ''))))
    return {'por_muni': por_muni, 'st': st}


def escribir(res: dict, fecha_osm: str | None):
    os.makedirs(os.path.join(PUBLICO, 'locales'), exist_ok=True)
    gen = AHORA.isoformat(timespec='seconds')
    indice = {}
    for cod, lst in sorted(res['por_muni'].items()):
        with open(os.path.join(PUBLICO, 'locales', f'{cod}.json'), 'w', encoding='utf-8') as f:
            json.dump({'m': cod, 'gen': gen, 'datos': fecha_osm, 'elements': lst}, f, ensure_ascii=False, separators=(',', ':'))
        indice[cod] = len(lst)
    por_tipo = {}
    for lst in res['por_muni'].values():
        for e in lst:
            t = e.get('tags') or {}
            k = ('tourism=' + t['tourism']) if t.get('tourism') in ALOJ else ('amenity=' + str(t.get('amenity')))
            por_tipo[k] = por_tipo.get(k, 0) + 1
    meta = {'gen': gen, 'datos': fecha_osm, 'fuente': 'OpenStreetMap vía Geofabrik',
            'licencia': 'ODbL 1.0 · © colaboradores de OpenStreetMap', 'total': sum(indice.values()),
            'municipios_con_datos': len(indice), 'por_tipo': dict(sorted(por_tipo.items(), key=lambda x: -x[1])),
            'estadisticas': res['st'], 'municipios': indice}
    with open(os.path.join(PUBLICO, 'indice.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(PUBLICO, '.nojekyll'), 'w') as f:
        f.write('')
    with open(os.path.join(PUBLICO, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(f'''<!doctype html><meta charset="utf-8"><title>MODO NOCHE · datos</title>
<body style="font-family:system-ui;background:#07070B;color:#eee;padding:24px;line-height:1.5">
<h1>MODO NOCHE · datos de locales</h1>
<p>Generado: {gen}. Datos de OpenStreetMap del {fecha_osm or "(fecha desconocida)"}.</p>
<p>{meta["total"]} locales en {len(indice)} municipios. Licencia ODbL · © colaboradores de OpenStreetMap.</p>
<p>Archivos: <a href="indice.json" style="color:#22D3EE">indice.json</a> y locales/CÓDIGO_INE.json</p></body>''')
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--geojsonseq')
    ap.add_argument('--min-limites', type=int, default=int(os.environ.get('MN_MIN_LIMITES', 7000)))
    ap.add_argument('--min-locales', type=int, default=int(os.environ.get('MN_MIN_LOCALES', 50000)))
    a = ap.parse_args(argv)
    munis = json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))['municipios']
    fecha = None
    if a.geojsonseq:
        salida = a.geojsonseq
    else:
        os.makedirs(TRABAJO, exist_ok=True)
        pbfs = []
        for url in EXTRACTOS:
            dst = os.path.join(TRABAJO, url.rsplit('/', 1)[1])
            log('Descargando', url)
            subprocess.run(['curl', '-fsSL', '--retry', '4', '--retry-delay', '20', '-A', UA, '-o', dst, url], check=True)
            pbfs.append(dst)
        try:
            fecha = subprocess.run(['osmium', 'fileinfo', '-g', 'header.option.osmosis_replication_timestamp', pbfs[0]],
                                   capture_output=True, text=True).stdout.strip() or None
        except Exception:
            pass
        filtrados = []
        for i, pbf in enumerate(pbfs):
            out = os.path.join(TRABAJO, f'filtrado{i}.osm.pbf'); log('Filtrando', pbf)
            subprocess.run(['osmium', 'tags-filter', '--overwrite', '-o', out, pbf, *FILTRO], check=True); filtrados.append(out)
        unido = os.path.join(TRABAJO, 'unido.osm.pbf')
        subprocess.run(['osmium', 'merge', '--overwrite', '-o', unido, *filtrados], check=True)
        salida = os.path.join(TRABAJO, 'unido.geojsonseq')
        subprocess.run(['osmium', 'export', '--overwrite', '-f', 'geojsonseq', '--add-unique-id=type_id', '-o', salida, unido], check=True)
    res = procesar(salida, munis)
    total = sum(len(v) for v in res['por_muni'].values())
    log('Estadísticas:', json.dumps(res['st'], ensure_ascii=False), '| locales publicados:', total, '| municipios:', len(res['por_muni']))
    if res['st']['limites_validos'] < a.min_limites or total < a.min_locales:
        log(f'ERROR: resultado sospechoso ({res["st"]["limites_validos"]} límites, {total} locales). No se publica nada.')
        return 1
    meta = escribir(res, fecha)
    resumen = os.environ.get('GITHUB_STEP_SUMMARY')
    if resumen:
        with open(resumen, 'a', encoding='utf-8') as f:
            f.write(f"## MODO NOCHE · datos\n\n- Datos de OSM: {fecha}\n- Locales: {meta['total']} en {len(meta['municipios'])} municipios\n"
                    f"- Límites municipales usados: {res['st']['limites_validos']}\n- Estadísticas: `{json.dumps(res['st'], ensure_ascii=False)}`\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
