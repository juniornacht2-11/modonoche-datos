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
import csv, datetime as dt, io, json, math, os, re, sys, unicodedata, urllib.error, urllib.request, urllib.parse

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SALIDA = os.path.join(RAIZ, 'publico', 'eventos')
UA = 'MODO-NOCHE-agenda/1.0 (https://github.com/juniornacht2-11/modonoche-datos; actualizacion diaria)'
HOY = dt.date.today()
HASTA = HOY + dt.timedelta(days=60)
GEN = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
MUSICA = re.compile(r'm[uú]sica|concierto|concert|fiesta|festa|festival|\bdj\b|dj set|jazz|flamenco|rock|\bpop\b|electr[oó]nic|techno|reggae|\brap\b|hip.?hop|indie|\bsoul\b|blues|salsa|verbena|discoteca|kontzertu|\bjai\b|jaialdi|cantante|banda|orquesta|coro\b|zarzuela|[oó]pera\b|cabaret|karaoke|baile', re.I)
NO_MUSICA = re.compile(r'club de lectura|lectura|taller|curso|cuentacuentos|biblioteca|infantil|beb[eé]s|cine|film|zinema|pel[ií]cula|literari|literatura|exposici|erakusketa|conferencia|charla|hitzaldi|^programa\b|ciclo\b|teatro|antzerki', re.I)
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
    if not m or int(m[1]) > 23 or (m[1] in ('0', '00') and m[2] == '00'):
        return ''  # 00:00 suele significar «sin hora publicada»
    return f'{int(m[1]):02d}:{m[2]}'


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
    if (fin - ini).days > 31:  # programas permanentes o de temporada: no son planes de una noche
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
    if MUSICA.search(' '.join([titulo or '', cat or ''])) and not NO_MUSICA.search(' '.join([titulo or '', cat or ''])): e['mus'] = 1
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
    urls = ['https://opendata-ajuntament.barcelona.cat/data/dataset/a25e60cd-3083-4252-9fce-81f733871cb1/resource/877ccf66-9106-4ae2-be51-95a9f6469e4c/download',
            'https://opendata-ajuntament.barcelona.cat/resources/bcn/Agenda/opendatabcn_agenda-csv.csv']
    raw, err = None, None
    for u in urls:
        try:
            raw = bajar(u, timeout=180)
            if raw[:200].lstrip().lower().startswith((b'<!doctype', b'<html')):
                err = f'{u}: devuelve una página web (control antirobots), no datos'; raw = None; continue
            break
        except Exception as ex:
            err = f'{u}: {ex}'; raw = None
    if raw is None:
        raise RuntimeError(err)
    for enc in ('utf-8-sig', 'utf-16', 'latin-1'):
        try: txt = raw.decode(enc); break
        except UnicodeDecodeError: pass
    head = txt[:4000]
    delim = max([',', ';', '\t'], key=head.count)
    filas = list(csv.DictReader(io.StringIO(txt), delimiter=delim))
    MUESTRAS['barcelona'] = filas[:2]
    out = []
    for r in filas:
        g = lambda *ks: next(((r.get(k) or '').strip() for k in ks if (r.get(k) or '').strip()), '')
        via = ' '.join(x for x in (g('addresses_road_name'), g('addresses_start_street_number')) if x)
        e = evento(g('name'), g('start_date'), g('end_date'), hora(g('start_date')), g('institution_name', 'addresses_neighborhood_name'),
                   ', '.join(x for x in (via, g('addresses_zip_code')) if x), g('geo_epgs_4326_lat', 'geo_epgs_4326_y'), g('geo_epgs_4326_lon', 'geo_epgs_4326_x'),
                   '', '', False, 'Ajuntament de Barcelona (Open Data BCN, CC BY 4.0)', g('secondary_filters_name', 'values_value', 'values_category'))
        if e: out.append(('08019', e))
    return out, len(filas)


# ---------------- Euskadi (Kulturklik) ----------------
def euskadi(nombres):
    out, total, pagina = [], 0, 1
    while pagina <= 120:
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


# ---------------- Ticketmaster (clave en el secreto TICKETMASTER_KEY de GitHub) ----------------
def ticketmaster(nombres, munis):
    import time
    clave = os.environ.get('TICKETMASTER_KEY', '').strip()
    if not clave:
        raise RuntimeError('sin clave: falta el secreto TICKETMASTER_KEY en GitHub')
    centros = [(m[0], m[2], m[3]) for m in munis if m[2] is not None]
    def municipio(ciudad, lat, lng):
        cod = nombres.get(norm(ciudad))
        if cod: return cod
        if lat is None: return None
        best, bd = None, 15.0
        for c, la, lo in centros:
            if abs(la - lat) > 0.2 or abs(lo - lng) > 0.25: continue
            d = math.hypot((la - lat) * 111, (lo - lng) * 111 * math.cos(math.radians(lat)))
            if d < bd: best, bd = c, d
        return best
    def pedir(desde, hasta, pagina):
        q = urllib.parse.urlencode({'apikey': clave, 'countryCode': 'ES', 'size': 200, 'page': pagina, 'sort': 'date,asc', 'locale': '*',
                                    'startDateTime': desde.strftime('%Y-%m-%dT00:00:00Z'), 'endDateTime': hasta.strftime('%Y-%m-%dT23:59:59Z')})
        for intento in range(4):
            try:
                time.sleep(0.3)
                return json.loads(bajar('https://app.ticketmaster.com/discovery/v2/events.json?' + q, timeout=60))
            except urllib.error.HTTPError as ex:
                if ex.code == 401: raise RuntimeError('la clave de Ticketmaster no es válida (HTTP 401)')
                if ex.code == 429 and intento < 3: time.sleep(5); continue
                raise
    out, total, ventanas = [], 0, []
    d = HOY
    while d <= HASTA:
        ventanas.append((d, min(d + dt.timedelta(days=6), HASTA))); d += dt.timedelta(days=7)
    while ventanas:
        a, b = ventanas.pop(0)
        res = pedir(a, b, 0)
        n = int((res.get('page') or {}).get('totalElements') or 0)
        if n > 1000 and a < b:  # Ticketmaster solo deja ver 1000 resultados por consulta: se parte la ventana
            m = a + (b - a) // 2
            ventanas[:0] = [(a, m), (m + dt.timedelta(days=1), b)]; continue
        paginas = min(int((res.get('page') or {}).get('totalPages') or 0), 5)
        for pg in range(paginas):
            data = res if pg == 0 else pedir(a, b, pg)
            for ev in (data.get('_embedded') or {}).get('events') or []:
                total += 1
                if total <= 2: MUESTRAS.setdefault('ticketmaster', []).append(ev)
                ven = ((ev.get('_embedded') or {}).get('venues') or [{}])[0]
                loc = ven.get('location') or {}
                try: lat, lng = float(loc.get('latitude')), float(loc.get('longitude'))
                except (TypeError, ValueError): lat = lng = None
                cod = municipio((ven.get('city') or {}).get('name', ''), lat, lng)
                if not cod: continue
                st = (ev.get('dates') or {}).get('start') or {}
                pr = (ev.get('priceRanges') or [{}])[0]
                precio = ''
                if pr.get('min') is not None:
                    mon = pr.get('currency', 'EUR').replace('EUR', '€')
                    precio = f"de {pr['min']:.0f} a {pr['max']:.0f} {mon}" if pr.get('max') and pr['max'] != pr['min'] else f"{pr['min']:.0f} {mon}"
                cls = (ev.get('classifications') or [{}])[0]
                cat = ' '.join(x.get('name', '') for x in (cls.get('segment') or {}, cls.get('genre') or {}) if isinstance(x, dict))
                e = evento(ev.get('name'), st.get('localDate'), st.get('localDate'), hora(st.get('localTime')), ven.get('name'),
                           ', '.join(x for x in ((ven.get('address') or {}).get('line1'), ven.get('postalCode')) if x), lat, lng,
                           ev.get('url'), precio, False, 'Ticketmaster', cat)
                if e:
                    if (cls.get('segment') or {}).get('name') == 'Music': e['mus'] = 1
                    out.append((cod, e))
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
    for nombre, fn in (('Madrid', madrid), ('Barcelona', barcelona), ('Euskadi', lambda: euskadi(nombres)), ('Ticketmaster', lambda: ticketmaster(nombres, munis))):
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
