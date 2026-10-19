#!/usr/bin/env python3
"""
MODO NOCHE · agenda de eventos de fuentes oficiales y abiertas (sin claves)
==========================================================================
  - Ayuntamiento de Madrid · «Agenda de actividades y eventos» (datos.madrid.es, CC BY 4.0)
  - Ajuntament de Barcelona · «Agenda diària» (Open Data BCN, CC BY 4.0)
  - Gobierno Vasco · agenda cultural Kulturklik (api.euskadi.eus, datos abiertos)
Escribe:
  publico/eventos/MMMMM.json   {"m": INE, "gen": fecha, "eventos": [...]} (próximos 60 días)
  publico/eventos/indice.json  municipios con eventos y estado de cada fuente
  publico/eventos/_muestras.json  2 registros originales por fuente (para revisar el formato)
Cada fuente es independiente: si una falla, las demás se publican igual y el fallo queda anotado.
Solo biblioteca estándar.
"""
from __future__ import annotations
import csv, datetime as dt, io, json, math, os, re, sys, unicodedata, urllib.request, urllib.parse

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SALIDA = os.path.join(RAIZ, 'publico', 'eventos')
UA = 'MODO-NOCHE-agenda/1.0 (https://github.com/juniornacht2-11/modonoche-datos; actualizacion diaria)'
HOY = dt.date.today()
HASTA = HOY + dt.timedelta(days=60)
GEN = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
MUSICA = re.compile(r'm[uú]sica|concierto|concert|fiesta|festa|festival|\bdj\b|dj set|jazz|flamenco|rock|\bpop\b|electr[oó]nic|techno|reggae|rap\b|hip.?hop|indie|soul|blues|salsa|verbena|sesi[oó]n|club|discoteca|kontzertu|jai', re.I)
MUESTRAS = {}


def log(*a):
    print(*a, flush=True)


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return re.sub(r'[^a-z0-9ñ]+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()).strip()


def bajar(url, timeout=90):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json, text/csv, */*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fecha(v):
    """Acepta 2026-10-24, 2026-10-24 00:00:00.0, 24/10/2026, 2026-10-24T20:00:00Z…"""
    if not v:
        return None
    s = str(v).strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        return dt.date(int(m[3]), int(m[2]), int(m[1]))
    return None


def hora(v):
    m = re.search(r'(\d{1,2}):(\d{2})', str(v or ''))
    return f'{int(m[1]):02d}:{m[2]}' if m and int(m[1]) < 24 else ''


def url_ok(u):
    u = str(u or '').strip()
    return u if re.match(r'^https?://[^\s"<>]+$', u) else ''


def limpio(t, n=300):
    t = re.sub(r'<[^>]+>', ' ', str(t or ''))
    return re.sub(r'\s+', ' ', t).strip()[:n]


def evento(titulo, ini, fin, h, lugar, direccion, lat, lng, url, precio, gratis, fuente, cat=''):
    ini = fecha(ini); fin = fecha(fin) or ini
    if not titulo or not ini or fin < HOY or ini > HASTA:
        return None
    try:
        lat = float(lat) if lat not in (None, '') else None; lng = float(lng) if lng not in (None, '') else None
    except ValueError:
        lat = lng = None
    if lat is not None and not (27 < lat < 44.5 and -18.5 < lng < 4.6):
        lat = lng = None
    e = {'t': limpio(titulo, 160), 'ini': ini.isoformat(), 'fin': fin.isoformat(), 'f': fuente}
    if h: e['h'] = h
    if lugar: e['lugar'] = limpio(lugar, 120)
    if direccion: e['dir'] = limpio(direccion, 160)
    if lat is not None: e['lat'] = round(lat, 6); e['lng'] = round(lng, 6)
    if url_ok(url): e['url'] = url_ok(url)
    if precio: e['precio'] = limpio(precio, 80)
    if gratis: e['gratis'] = 1
    if MUSICA.search(' '.join([titulo or '', cat or '', lugar or ''])): e['mus'] = 1
    return e


# ---------------- Madrid ----------------
def madrid():
    urls = ['https://datos.madrid.es/dataset/300107-0-agenda-actividades-eventos/resource/300107-2-agenda-actividades-eventos-csv/download/300107-0-agenda-actividades-eventos.csv',
            'https://datos.madrid.es/en/dataset/300107-0-agenda-actividades-eventos/resource/300107-2-agenda-actividades-eventos-csv/download/300107-2-agenda-actividades-eventos-csv.csv']
    err = None
    for u in urls:
        try:
            raw = bajar(u)
            break
        except Exception as ex:
            err = ex; raw = None
    if raw is None:
        raise RuntimeError(f'descarga: {err}')
    txt = None
    for enc in ('utf-8-sig', 'latin-1'):
        try: txt = raw.decode(enc); break
        except UnicodeDecodeError: pass
    sample = txt[:4000]
    delim = ';' if sample.count(';') > sample.count(',') else ','
    filas = list(csv.DictReader(io.StringIO(txt), delimiter=delim))
    MUESTRAS['madrid'] = filas[:2]
    out = []
    for r in filas:
        g = lambda k: (r.get(k) or '').strip()
        via = ' '.join(x for x in (g('CLASE-VIAL-INSTALACION'), g('NOMBRE-VIA-INSTALACION'), g('NUM-INSTALACION')) if x)
        e = evento(g('TITULO') or g('TITULO-ACTIVIDAD'), g('FECHA'), g('FECHA-FIN'), hora(g('HORA')), g('NOMBRE-INSTALACION'),
                   ', '.join(x for x in (via, g('CODIGO-POSTAL-INSTALACION')) if x), g('LATITUD'), g('LONGITUD'),
                   g('CONTENT-URL') or g('URL-ACTIVIDAD'), g('PRECIO'), g('GRATUITO') == '1', 'Ayuntamiento de Madrid (datos.madrid.es, CC BY 4.0)', g('TIPO'))
        if e: out.append(('28079', e))
    return out, len(filas)


# ---------------- Barcelona ----------------
def _buscar(d, *claves):
    for k in claves:
        if isinstance(d, dict) and d.get(k) not in (None, '', []):
            return d[k]
    return None


def barcelona():
    meta = json.loads(bajar('https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_show?id=agenda-diaria'))
    recursos = meta['result']['resources']
    js = [r for r in recursos if (r.get('format') or '').lower() == 'json'] or [r for r in recursos if r.get('url', '').endswith('.json')]
    if not js:
        raise RuntimeError('sin recurso JSON en el catálogo')
    datos = json.loads(bajar(js[0]['url'], timeout=180))
    filas = datos if isinstance(datos, list) else datos.get('result', {}).get('records') or datos.get('records') or datos.get('data') or []
    MUESTRAS['barcelona'] = filas[:2]
    out = []
    for r in filas:
        addr = (_buscar(r, 'addresses') or [{}])
        addr = addr[0] if isinstance(addr, list) and addr else (addr if isinstance(addr, dict) else {})
        lat = lng = None
        loc = _buscar(addr, 'location') or {}
        geoms = (loc.get('geometries') or []) if isinstance(loc, dict) else []
        if geoms and isinstance(geoms[0], dict):
            c = geoms[0].get('coordinates') or []
            if len(c) >= 2 and abs(c[0]) <= 180: lng, lat = c[0], c[1]
        if lat is None:
            lat, lng = _buscar(r, 'geo_epgs_4326_lat', 'geo_epgs_4326_y', 'latitude', 'lat'), _buscar(r, 'geo_epgs_4326_lon', 'geo_epgs_4326_x', 'longitude', 'lon')
        via = ' '.join(str(x) for x in (_buscar(addr, 'road_name', 'addresses_road_name'), _buscar(addr, 'start_street_number', 'addresses_start_street_number')) if x)
        cats = r.get('secondary_filters_name') or r.get('values') or ''
        e = evento(_buscar(r, 'name', 'nom', 'title'), _buscar(r, 'start_date', 'data_inici'), _buscar(r, 'end_date', 'data_fi'),
                   hora(_buscar(r, 'start_date', 'hora_inici')), _buscar(r, 'institution_name', 'equipament', 'place') or _buscar(addr, 'district_name'),
                   ', '.join(x for x in (via, str(_buscar(addr, 'zip_code', 'addresses_zip_code') or '')) if x), lat, lng,
                   _buscar(r, 'url', 'link'), '', False, 'Ajuntament de Barcelona (Open Data BCN, CC BY 4.0)', json.dumps(cats, ensure_ascii=False)[:300])
        if e: out.append(('08019', e))
    return out, len(filas)


# ---------------- Euskadi (Kulturklik) ----------------
def euskadi(nombres):
    out, total, pagina = [], 0, 1
    while pagina <= 40:
        d = json.loads(bajar(f'https://api.euskadi.eus/culture/events/v1.0/events/upcoming?_elements=100&_page={pagina}&lang=SPANISH'))
        items = d.get('items') or []
        if pagina == 1: MUESTRAS['euskadi'] = items[:2]
        if not items: break
        for r in items:
            total += 1
            muni = r.get('municipalityEs') or r.get('municipalityEu') or ''
            cod = nombres.get(norm(muni))
            if not cod:
                for parte in re.split(r'[/-]', muni):
                    cod = nombres.get(norm(parte))
                    if cod: break
            if not cod: continue
            e = evento(r.get('nameEs') or r.get('nameEu'), r.get('startDate'), r.get('endDate'), hora(r.get('openingHoursEs') or r.get('startDate')),
                       r.get('establishmentEs') or r.get('placeEs'), '', r.get('municipalityLatitude'), r.get('municipalityLongitude'),
                       r.get('urlEventEs') or r.get('sourceUrlEs'), r.get('priceEs'), False, 'Gobierno Vasco · Kulturklik (Open Data Euskadi)', r.get('typeEs') or '')
            if e:
                e.pop('lat', None); e.pop('lng', None)  # coordenadas del municipio, no del lugar: no sirven para el mapa
                out.append((cod, e))
        if pagina >= int(d.get('totalPages') or 1): break
        pagina += 1
    return out, total


def main():
    munis = json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))['municipios']
    nombres = {}
    for m in munis:
        for parte in [m[1]] + re.split(r'[/]', m[1]):
            p = parte.strip(); mm = re.match(r'^(.*), (.+)$', p)
            if mm: p = mm[2] + ' ' + mm[1]
            nombres.setdefault(norm(p), m[0])
    os.makedirs(SALIDA, exist_ok=True)
    por_muni, fuentes = {}, []
    for nombre, fn in (('Madrid', madrid), ('Barcelona', barcelona), ('Euskadi', lambda: euskadi(nombres))):
        try:
            lst, leidos = fn()
            for cod, e in lst: por_muni.setdefault(cod, []).append(e)
            fuentes.append({'fuente': nombre, 'ok': True, 'leidos': leidos, 'publicados': len(lst)})
            log(f'{nombre}: {leidos} leídos, {len(lst)} próximos publicados')
        except Exception as ex:
            fuentes.append({'fuente': nombre, 'ok': False, 'error': str(ex)[:300]})
            log(f'{nombre}: ERROR {ex}')
    indice = {}
    for cod, lst in por_muni.items():
        vistos, unicos = set(), []
        for e in sorted(lst, key=lambda e: (e['ini'], e.get('h', ''), e['t'])):
            k = (norm(e['t']), e['ini'], norm(e.get('lugar', '')))
            if k in vistos: continue
            vistos.add(k); unicos.append(e)
        with open(os.path.join(SALIDA, f'{cod}.json'), 'w', encoding='utf-8') as f:
            json.dump({'m': cod, 'gen': GEN, 'eventos': unicos}, f, ensure_ascii=False, separators=(',', ':'))
        indice[cod] = len(unicos)
    with open(os.path.join(SALIDA, 'indice.json'), 'w', encoding='utf-8') as f:
        json.dump({'gen': GEN, 'desde': HOY.isoformat(), 'hasta': HASTA.isoformat(), 'fuentes': fuentes, 'municipios': indice}, f, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(SALIDA, '_muestras.json'), 'w', encoding='utf-8') as f:
        json.dump(MUESTRAS, f, ensure_ascii=False, indent=1, default=str)
    resumen = os.environ.get('GITHUB_STEP_SUMMARY')
    if resumen:
        with open(resumen, 'a', encoding='utf-8') as f:
            f.write('## Agenda\n\n' + '\n'.join(f"- {x['fuente']}: " + (f"{x['leidos']} leídos, {x['publicados']} próximos" if x['ok'] else 'ERROR ' + x['error']) for x in fuentes) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
