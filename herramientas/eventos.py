#!/usr/bin/env python3
"""
MODO NOCHE · agenda de eventos de fuentes oficiales y abiertas (sin claves)
==========================================================================
  - Ayuntamiento de Madrid · «Agenda de actividades y eventos» (datos.madrid.es, CC BY 4.0)
  - Ajuntament de Barcelona · «Agenda diària» (Open Data BCN, CC BY 4.0)
  - Gobierno Vasco · agenda cultural Kulturklik (api.euskadi.eus, datos abiertos)
  - Ayuntamiento de Málaga · agenda (datosabiertos.malaga.eu) y Ayuntamiento de Zaragoza · agenda (API zaragoza.es)
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
    if re.search(r'^\s*test\b|\btest\s*\d{3,}|\bcase\s*\d{3,}|evento de prueba', str(titulo), re.I):
        return None  # registros de prueba de la propia fuente
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


# ---------------- Cataluña (Agenda cultural de la Generalitat, toda Cataluña) ----------------
def cataluna(nombres_cat):
    hasta = HASTA.isoformat()
    q = urllib.parse.urlencode({'$limit': 50000, '$where': f"data_fi >= '{HOY.isoformat()}T00:00:00' AND data_inici <= '{hasta}T23:59:59' AND permanent = 'No'"})
    filas = json.loads(bajar('https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json?' + q, timeout=180))
    MUESTRAS['cataluna'] = [{k: v for k, v in r.items() if k not in ('descripcio', 'descripcio_html', 'email', 'tel_fon')} for r in filas[:2]]
    out = []
    for r in filas:
        g = lambda k: str(r.get(k) or '').strip()
        slug = (g('municipi') or g('comarca_i_municipi')).rstrip('/').split('/')[-1]
        cod = nombres_cat.get(norm(slug.replace('-', ' ')))
        if not cod:
            continue
        h = hora(g('horari'))
        if not h:
            m = re.search(r'\b(\d{1,2})(?:[.,:](\d{2}))?\s*h\b', g('horari'))
            if m and int(m[1]) < 24: h = f'{int(m[1]):02d}:{m[2] or "00"}'
        enlace = g('url') or g('linkbotoentrades') or (g('enlla_os').split(',')[0] if g('enlla_os') else '')
        if enlace and not enlace.startswith('http'): enlace = 'https://' + enlace
        titulo = g('denominaci') + (f' · {g("subt_tol")}' if g('subt_tol') else '')
        cat = ' '.join([g('tags_mbits'), g('tags_categor_es')]).replace('agenda:ambits/', '').replace('agenda:categories/', '').replace('-', ' ')
        e = evento(titulo, g('data_inici'), g('data_fi'), h, g('espai'), ', '.join(x for x in (g('adre_a'), g('codi_postal')) if x),
                   g('latitud'), g('longitud'), enlace, g('entrades'), g('gratuita') == 'Sí', 'Generalitat de Catalunya · Agenda cultural (dades obertes)', cat)
        if e: out.append((cod, e))
    return out, len(filas)


# ---------------- Castilla y León (agenda cultural geolocalizada) ----------------
def castilla_leon(nombres_prov):
    filas = json.loads(bajar('https://datosabiertos.jcyl.es/web/jcyl/risp/es/cultura-ocio/agenda_cultural/1284806871500.json', timeout=180))
    MUESTRAS['castilla_leon'] = [{k: v for k, v in r.items() if k not in ('descripcion',)} for r in filas[:2]]
    out = []
    for r in filas:
        g = lambda k: str(r.get(k) if r.get(k) is not None else '').strip()
        prov = g('codigo_provincia').zfill(2)
        cod = nombres_prov.get((prov, norm(g('nombre_localidad'))))
        if not cod:
            continue
        e = evento(g('titulo'), g('fecha_inicio'), g('fecha_fin') or g('fecha_inicio'), hora(g('hora_inicio')), g('lugar_celebracion'),
                   ', '.join(x for x in (g('calle'), g('cp')) if x), r.get('latitud'), r.get('longitud'), g('enlace_contenido'),
                   g('precio'), 'gratu' in g('precio').lower(), 'Junta de Castilla y León · Agenda cultural (datos abiertos)', g('categoria') + ' ' + g('tematica'))
        if e: out.append((cod, e))
    return out, len(filas)


# ---------------- Gijón (agenda municipal) ----------------
def gijon():
    filas = json.loads(bajar('https://opendata.gijon.es/descargar.php?id=728&tipo=JSON', timeout=120).decode('utf-8-sig'))
    MUESTRAS['gijon'] = filas[:2]
    out = []
    for r in filas:
        g = lambda k: str(r.get(k) or '').strip()
        fechas = re.findall(r'\d{4}-\d{2}-\d{2}', g('fechas') or g('fecha_inicio'))
        if not fechas:
            continue
        e = evento(g('titulo'), fechas[0], fechas[-1], hora(g('hora_inicio')), g('titulo_directorio') or g('field_lo_name'),
                   g('direccion_directorio') or g('field_lo_address'), None, None, g('alias'), '', False, 'Ayuntamiento de Gijón (datos abiertos)',
                   ' '.join([g('materia'), g('tipo'), g('etiquetas')]))
        if e: out.append(('33024', e))
    return out, len(filas)

# ---------------- Málaga (Ayuntamiento, datos abiertos, se actualiza cada día) ----------------
def malaga():
    b = bajar(f'https://datosabiertos.malaga.eu/recursos/cultura/agenda/{HOY.year}.csv', timeout=180)
    try: txt = b.decode('utf-8-sig')
    except UnicodeDecodeError: txt = b.decode('latin-1')
    filas = list(csv.DictReader(io.StringIO(txt)))
    MUESTRAS['malaga'] = filas[:2]
    out = []
    for r in filas:
        g = lambda k: str(r.get(k) or '').strip()
        precio = g('PRECIO')
        e = evento(g('NOMBRE') or g('EVENTO'), g('F_INICIO'), g('F_FIN'), hora(g('HORARIO')), g('EQP_DESCRIPCION'), g('EQP_NOMBRECALLE'), None, None,
                   g('DIRECCION_WEB'), '' if re.search(r'gratu|libre', precio, re.I) else precio[:80], bool(re.search(r'gratu|libre', precio, re.I)),
                   'Ayuntamiento de Málaga (datos abiertos)', ' '.join([g('CATEGORIA'), g('ESPECIALIDAD'), g('PALABRAS_CLAVE')]))
        if e: out.append(('29067', e))
    return out, len(filas)


def utm30_a_latlng(x, y):
    """ETRS89 / UTM 30N (EPSG:25830) → latitud y longitud (fórmulas estándar de Transverse Mercator)."""
    a, f = 6378137.0, 1 / 298.257222101; e2 = f * (2 - f); k0 = 0.9996; e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    x -= 500000.0; m = y / k0; mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    n1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); t1 = math.tan(p1) ** 2; ep2 = e2 / (1 - e2); c1 = ep2 * math.cos(p1) ** 2
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5; d = x / (n1 * k0)
    lat = p1 - (n1 * math.tan(p1) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24 + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lng = (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p1)
    return round(math.degrees(lat), 6), round(math.degrees(lng) - 3.0, 6)


# ---------------- Zaragoza (Ayuntamiento, API de datos abiertos) ----------------
def zaragoza():
    res, start, total = [], 0, None
    while total is None or start < min(total, 6000):
        j = json.loads(bajar(f'https://www.zaragoza.es/sede/servicio/cultura/evento/list.json?rows=500&start={start}', timeout=120).decode('utf-8'))
        total = j.get('totalCount') or 0; lote = j.get('result') or []
        res += lote; start += 500
        if not lote: break
    MUESTRAS['zaragoza'] = res[:2]
    out = []
    for r in res:
        cats = ' '.join(c.get('title', '') for c in (r.get('category') or []) if isinstance(c, dict))
        precio = ' '.join(str(p.get('fareGroup') or '') + ' ' + str(p.get('hasCurrencyValue') or '') for p in (r.get('price') or []) if isinstance(p, dict)).strip()
        for se in (r.get('subEvent') or [{}])[:20]:
            loc = se.get('location') or {}
            lat = lng = None
            co = ((loc.get('geometry') or {}).get('coordinates') or [])
            if len(co) == 2 and co[0] > 1000:
                try: lat, lng = utm30_a_latlng(float(co[0]), float(co[1]))
                except Exception: lat = lng = None
            h = ''
            for oh in se.get('openingHours') or []:
                h = hora(oh.get('startTime'))
                if h: break
            e = evento(r.get('title'), se.get('startDate') or r.get('startDate'), se.get('endDate') or r.get('endDate'), h, loc.get('title'), loc.get('streetAddress'), lat, lng,
                       r.get('url') if url_ok(r.get('url')) else f"https://www.zaragoza.es/sede/servicio/cultura/evento/{r.get('id')}", precio[:80], bool(re.search(r'gratu', precio + ' ' + str(r.get('description') or ''), re.I)),
                       'Ayuntamiento de Zaragoza (datos abiertos)', cats)
            if e: out.append(('50297', e))
    return out, len(res)



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
    nombres_cat, nombres_prov = {}, {}
    for m in munis:
        for parte in [m[1]] + re.split(r'[/]', m[1]):
            p = parte.strip(); mm = re.match(r'^(.*), (.+)$', p)
            variantes = [p] + ([mm[2] + ' ' + mm[1], mm[1]] if mm else [])
            for v in variantes:
                nombres_prov.setdefault((m[0][:2], norm(v)), m[0])
                if m[0][:2] in ('08', '17', '25', '43'): nombres_cat.setdefault(norm(v), m[0])
    for nombre, fn in (('Madrid', madrid), ('Barcelona', barcelona), ('Cataluña', lambda: cataluna(nombres_cat)), ('Castilla y León', lambda: castilla_leon(nombres_prov)),
                       ('Gijón', gijon), ('Málaga', malaga), ('Zaragoza', zaragoza), ('Euskadi', lambda: euskadi(nombres)), ('Ticketmaster', lambda: ticketmaster(nombres, munis))):
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
