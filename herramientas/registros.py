"""MODO NOCHE · alojamientos de los registros oficiales de turismo de las comunidades autónomas.

Fuentes (datos abiertos, se descargan cada semana):
  · Canarias       viviendas vacacionales del Registro General Turístico (con coordenadas)
  · Andalucía      Registro de Turismo de Andalucía, OpenRTA (con coordenadas UTM)
  · Cataluña       Registre de Turisme de Catalunya (se sitúa con la referencia catastral)
  · C. Valenciana  viviendas de uso turístico (se sitúa con la referencia catastral)
  · Castilla y León viviendas de uso turístico (coordenadas propias o dirección)
  · C. de Madrid   alojamientos turísticos (se sitúan por la dirección con CartoCiudad, IGN)
Ubicación: Catastro (INSPIRE, parcelas catastrales, © Dirección General del Catastro) y CartoCiudad (© IGN/CNIG).

PRIVACIDAD: nunca se guardan titulares, NIF, teléfonos ni emails particulares, ni piso o puerta.
De las viviendas turísticas solo se publica la calle (sin número), el nombre comercial si lo hay,
las plazas y el número de registro.

Salida: publico/registros/CÓDIGO_INE.json y publico/registros/indice.json
"""
import concurrent.futures as cf
import csv, io, json, math, os, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile
from collections import Counter, defaultdict

csv.field_size_limit(10 ** 9)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICO = os.environ.get('SALIDA_REGISTROS') or os.path.join(RAIZ, 'publico', 'registros')
CACHE = os.path.join(RAIZ, 'cache')
TMP = os.path.join(RAIZ, 'tmp_registros')
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
LIMITE_GEOCOD = int(os.environ.get('LIMITE_GEOCOD', '12000'))   # direcciones nuevas por ejecución (el resto, la semana siguiente)
ST = Counter()


LOG = []


def log(*a):
    s = time.strftime('%H:%M:%S') + ' ' + ' '.join(str(x) for x in a)
    LOG.append(s[:300]); print(s, flush=True)


def bajar(url, ruta=None, t=300, intentos=4):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t) as r:
                if not ruta:
                    return r.read()
                with open(ruta, 'wb') as f:
                    while True:
                        c = r.read(1 << 20)
                        if not c:
                            break
                        f.write(c)
                return ruta
        except Exception as e:
            log('  reintento', i + 1, url[:90], repr(e)[:100])
            time.sleep(3 * (i + 1))
    raise RuntimeError('no se ha podido descargar ' + url)


def texto(b):
    for e in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass


def tabla(txt, delim=None):
    delim = delim or max([';', ',', '\t', '|'], key=txt[:5000].count)
    rr = list(csv.reader(io.StringIO(txt), delimiter=delim))
    return rr[0], rr[1:]


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def num(v):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return None


# ---------- UTM (ETRS89 / GRS80) → latitud y longitud ----------
def utm_a_geo(E, N, zona):
    a, f, k0 = 6378137.0, 1 / 298.257222101, 0.9996
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    x, y = E - 500000.0, N
    M = y / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    p1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    s1, c1, t1 = math.sin(p1), math.cos(p1), math.tan(p1)
    N1 = a / math.sqrt(1 - e2 * s1 ** 2); T1 = t1 ** 2; C1 = ep2 * c1 ** 2
    R1 = a * (1 - e2) / (1 - e2 * s1 ** 2) ** 1.5; D = x / (N1 * k0)
    lat = p1 - (N1 * t1 / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24
                                 + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / c1
    return round(math.degrees(lat), 6), round((zona - 1) * 6 - 180 + 3 + math.degrees(lon), 6)


def en_espana(lat, lng):
    return lat is not None and lng is not None and 27.4 < lat < 44.0 and -18.4 < lng < 4.5


# ---------- municipios del INE ----------
MUNIS = json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))
PROV = {p[0]: p[1] for p in MUNIS['provincias']}


def variantes(nombre):
    out = set()
    for parte in re.split(r'\s*/\s*', nombre):
        n = norm(parte); out.add(n)
        m = re.match(r'^(.*?) (el|la|los|las|l|lo|els|les|o|a|os|as|s|sa|es|ses|na)$', n)
        if m:
            out.add(f'{m.group(2)} {m.group(1)}'); out.add(m.group(1))
        out.add(re.sub(r'^(el|la|los|las|l|els|les|o|a|os|as|sa|es|ses) ', '', n))
    out |= {re.sub(r' (de|del|de la|de los|de las|d) ', ' ', x) for x in list(out)}
    return {x for x in out if x}


POR_NOMBRE = defaultdict(list)      # (prov, nombre normalizado) → código
CENTROS = []
for fila in MUNIS['municipios']:
    cod, nombre, lat, lng = fila[:4]
    for v in variantes(nombre):
        POR_NOMBRE[(cod[:2], v)].append(cod)
        POR_NOMBRE[('*', v)].append(cod)
    if lat is not None:
        CENTROS.append((cod, lat, lng))
PROV_POR_NOMBRE = {}
for c, n in PROV.items():
    for v in variantes(n):
        PROV_POR_NOMBRE[v] = c
PROV_POR_NOMBRE.update({'tenerife': '38', 'santa cruz de tenerife': '38', 'palmas': '35', 'las palmas': '35', 'palmas las': '35',
                        'alava': '01', 'guipuzcoa': '20', 'vizcaya': '48', 'gerona': '17', 'lerida': '25', 'orense': '32', 'la coruna': '15', 'baleares': '07'})


def prov_de(nombre):
    n = norm(nombre)
    return PROV_POR_NOMBRE.get(n) or PROV_POR_NOMBRE.get(re.sub(r'^(la|las|el|los) ', '', n)) or PROV_POR_NOMBRE.get(n.split(' ')[0])


def muni_de(nombre, prov=None, lat=None, lng=None):
    n = norm(nombre)
    for clave in [n, re.sub(r'^(el|la|los|las|l|els|les|o|a|sa|es|ses) ', '', n), re.sub(r' (de|del|de la|de los|de las|d) ', ' ', n)]:
        lst = POR_NOMBRE.get((prov or '*', clave))
        if lst and len(set(lst)) == 1:
            return lst[0]
    if lat is not None:     # el más cercano (dentro de la provincia si se sabe)
        best, bd = None, 1e9
        for cod, la, lo in CENTROS:
            if prov and cod[:2] != prov:
                continue
            d = (la - lat) ** 2 + ((lo - lng) * math.cos(math.radians(lat))) ** 2
            if d < bd:
                best, bd = cod, d
        if best and bd < 0.25 ** 2:
            return best
    return None


# ---------- utilidades de dirección (sin piso ni puerta) ----------
VIA = {'cl': 'Calle', 'c': 'Calle', 'calle': 'Calle', 'av': 'Avenida', 'avda': 'Avenida', 'avenida': 'Avenida', 'pz': 'Plaza', 'plaza': 'Plaza',
       'ps': 'Paseo', 'paseo': 'Paseo', 'ur': 'Urbanización', 'urb': 'Urbanización', 'ctra': 'Carretera', 'cr': 'Carretera', 'trva': 'Travesía', 'cmno': 'Camino'}


def bonito(s):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s.title() if s.isupper() or s.islower() else s


def solo_calle(s):
    """«CALLE MAYOR Nº 12, 3º B» → «Calle Mayor» (para viviendas turísticas no se publica el número)."""
    s = str(s or '')
    s = re.split(r'(,|\bn[ºo°.]?\s*\d|\bnum\.?\s*\d|\bs/n\b|\d)', s, maxsplit=1, flags=re.I)[0]
    return bonito(s.strip(' ,.-'))[:120]


def con_numero(via, nombre, numero):
    return ' '.join(x for x in [VIA.get(norm(via)) or bonito(via), bonito(nombre), str(numero or '').strip()] if x and str(x).strip())[:140]


def url_ok(u):
    u = str(u or '').strip()
    if not u or ' ' in u or '@' in u:
        return ''
    if not re.match(r'^https?://', u, re.I):
        u = 'https://' + u
    return u[:200] if re.match(r'^https?://[a-z0-9.-]+\.[a-z]{2,}', u, re.I) else ''


# ---------- registros que se van juntando ----------
SALIDA = defaultdict(list)


def anadir(fuente, idd, tipo, muni, lat, lng, nombre='', dir_='', plazas=None, lic='', web=''):
    if not muni or not en_espana(lat, lng):
        ST[fuente + ' · sin ubicar'] += 1
        return
    r = {'id': f'{fuente}/{idd}', 't': tipo, 'lat': round(lat, 6), 'lng': round(lng, 6)}
    if nombre and norm(nombre) not in ('', 'vivienda', 'vivienda turistica', 'vut', 'piso'):
        r['n'] = bonito(nombre)[:100]
    if dir_:
        r['dir'] = dir_
    p = num(plazas)
    if p and 0 < p < 5000:
        r['pl'] = int(p)
    if lic:
        r['lic'] = str(lic).strip()[:40]
    w = url_ok(web)
    if w:
        r['web'] = w
    SALIDA[muni].append(r)
    ST[fuente] += 1
    ST['tipo ' + tipo] += 1


# ---------- cachés (se guardan entre semanas con actions/cache) ----------
def cargar_cache(nombre):
    try:
        return json.load(open(os.path.join(CACHE, nombre), encoding='utf-8'))
    except Exception:
        return {}


def guardar_cache(nombre, d):
    os.makedirs(CACHE, exist_ok=True)
    json.dump(d, open(os.path.join(CACHE, nombre), 'w', encoding='utf-8'), separators=(',', ':'))


GEO = cargar_cache('geocodificacion.json')
CAT = cargar_cache('catastro.json')
geocodificadas = 0


def geocodificar(q):
    """CartoCiudad (IGN). Devuelve (lat, lng, códigoINE) o None. Con caché."""
    global geocodificadas
    k = norm(q)
    if k in GEO:
        return GEO[k] or None
    if geocodificadas >= LIMITE_GEOCOD:
        return None
    geocodificadas += 1
    try:
        b = bajar('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(q), t=30, intentos=2)
        j = json.loads(b) if b and b.strip()[:1] == b'{' else {}
        m = re.search(r'POINT\(([-\d.]+) ([-\d.]+)\)', j.get('geom') or '')
        res = [round(float(m.group(2)), 6), round(float(m.group(1)), 6), j.get('muniCode') or ''] if m and j.get('type') in ('portal', 'callejero', 'Municipio', 'poblacion', 'toponimo', 'carretera') else []
    except Exception:
        res = None     # error de red: no se guarda en caché, se reintenta otra semana
    if res is not None:
        GEO[k] = res
    time.sleep(0.05)
    return res or None


# ---------- Catastro: referencia catastral → punto de la parcela ----------
def catastro(refs_por_muni):
    """refs_por_muni: {INE: set(ref14)}. Rellena CAT con {ref14: [lat, lng]} descargando las parcelas INSPIRE del municipio."""
    falta = {m: {r for r in rs if r not in CAT} for m, rs in refs_por_muni.items()}
    falta = {m: rs for m, rs in falta.items() if rs}
    if not falta:
        return
    provs = sorted({m[:2] for m in falta})
    zips = {}
    for p in provs:
        try:
            fx = texto(bajar(f'https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/{p}/ES.SDGC.CP.atom_{p}.xml', t=120))
            for u in re.findall(r'href="([^"]+?\.zip)"', fx):
                m = re.search(r'/' + p + r'/(\d{5})-([^/]+)/', u)
                if m:
                    zips[m.group(1)] = (u, m.group(2))
        except Exception as e:
            log('  Catastro: sin índice de la provincia', p, repr(e)[:80])
    # el código del Catastro no siempre coincide con el del INE: se busca por código y, si no, por nombre
    por_nombre = defaultdict(list)
    for c, (u, n) in zips.items():
        por_nombre[(c[:2], norm(urllib.parse.unquote(n)))].append(c)
    nombres = {m[0]: m[1] for m in MUNIS['municipios']}

    def zip_de(ine):
        if ine in zips:
            n_ine = variantes(nombres.get(ine, ''))
            if norm(urllib.parse.unquote(zips[ine][1])) in n_ine:
                return zips[ine][0]
        for v in variantes(nombres.get(ine, '')):
            c = por_nombre.get((ine[:2], v))
            if c:
                return zips[c[0]][0]
        return zips[ine][0] if ine in zips else None

    tareas = [(m, zip_de(m), rs) for m, rs in falta.items()]
    sin = [m for m, u, rs in tareas if not u]
    if sin:
        log('  Catastro: municipios sin archivo', len(sin), sin[:10])

    def una(t):
        m, u, rs = t
        if not u:
            return m, {}
        try:
            b = bajar(u.replace(' ', '%20'), t=600, intentos=3)
            zf = zipfile.ZipFile(io.BytesIO(b))
            g = texto(zf.read(next(n for n in zf.namelist() if n.endswith('cadastralparcel.gml'))))
            out = {}
            for ref, srs, pos in re.findall(r'<cp:nationalCadastralReference>([^<]+)</cp:nationalCadastralReference>.*?<cp:referencePoint>\s*<gml:Point[^>]*srsName="[^"]*?(\d{5})"[^>]*>\s*<gml:pos>([^<]+)</gml:pos>', g, re.S):
                ref = ref.strip()[:14]
                if ref in rs:
                    e, n = map(float, pos.split()[:2])
                    zona = int(srs[-2:]) if srs.startswith('258') else 30
                    out[ref] = list(utm_a_geo(e, n, zona))
            return m, out
        except Exception as e:
            log('  Catastro: error en', m, repr(e)[:100])
            return m, {}
    hechos = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for m, out in ex.map(una, [t for t in tareas if t[1]]):
            CAT.update(out)
            hechos += 1
            if hechos % 100 == 0:
                log(f'  Catastro: {hechos}/{len(tareas)} municipios')
    # las que no se encuentran se marcan para no volver a buscarlas esta vez
    for m, rs in falta.items():
        for r in rs:
            CAT.setdefault(r, [])


# =====================================================================================
def canarias():
    log('Canarias…')
    h, filas = tabla(texto(bajar('https://datos.canarias.es/catalogos/general/dataset/9f4355a2-d086-4384-ba72-d8c99aa2d544/resource/8ff8cc43-c00b-4513-8f42-a5b961c579e1/download/establecimientos-extrahoteleros-de-tipologia-vivienda-vacacional-inscritos-en-el-registro-genera.csv')))
    i = {c: k for k, c in enumerate(h)}
    for r in filas:
        g = lambda c: r[i[c]] if c in i and i[c] < len(r) else ''
        lat, lng = num(g('latitud')), num(g('longitud'))
        prov = prov_de(g('direccion_provincia_nombre'))
        muni = muni_de(g('direccion_municipio_nombre'), prov, lat, lng)
        anadir('ic', g('establecimiento_id'), 'vut', muni, lat, lng, g('establecimiento_nombre_comercial'), solo_calle(g('direccion')), g('plazas'))


def andalucia():
    log('Andalucía…')
    ruta = os.path.join(TMP, 'rta.csv'); bajar('https://datos.juntadeandalucia.es/api/v0/openrta/all?format=csv', ruta, t=600)
    h, filas = tabla(texto(open(ruta, 'rb').read()), '|')
    i = {c: k for k, c in enumerate(h)}
    # El CSV mezcla filas de 72 campos (con cabecera) y de 92 (sin cabecera, mismas columnas en orden alfabético
    # con 20 campos más). Posiciones comprobadas con el sondeo del 19/10/2026; si cambian, esas filas se descartan.
    LARGA = {'coord_x': 6, 'coord_y': 7, 'catastral_ref': 3, 'establishment_address': 13, 'group': 17, 'id': 40, 'municipalities': 51,
             'name': 53, 'objects_type_id': 60, 'provinces': 67, 'registration_code': 69, 'road_name': 73, 'srid': 81, 'tot_gen_places': 86, 'url': 90}
    largas_ok = sum(1 for r in filas[:2000] if len(r) == 92 and (num(r[6]) or 0) > 100000) > 200 or not any(len(r) == 92 for r in filas[:2000])
    if not largas_ok:
        log('  AVISO: las filas largas de OpenRTA han cambiado de formato; se descartan')
    TIPO = {'vivienda de uso turistico': 'vut', 'vivienda turistica de alojamiento rural': 'rural', 'casa rural': 'rural', 'complejo turistico rural': 'rural',
            'apartamento turistico': 'apartamento', 'campamento de turismo': 'camping'}
    GRUPO = {'hotel': 'hotel', 'hotel apartamento': 'hotel', 'hostal': 'hostal', 'pension': 'pension', 'albergue': 'albergue'}
    for r in filas:
        if len(r) == len(h):
            g = lambda c: r[i[c]] if c in i else ''
        elif len(r) == 92 and largas_ok:
            g = lambda c: r[LARGA[c]] if c in LARGA else ''
        else:
            ST['and · fila rara'] += 1
            continue
        ot = norm(g('objects_type_id'))
        tipo = TIPO.get(ot) or (GRUPO.get(norm(g('group'))) if ot == 'establecimiento hotelero' else None)
        if not tipo:
            continue
        x, y = num(g('coord_x')), num(g('coord_y'))
        if not (x and y):
            ST['and · sin coordenadas'] += 1
            continue
        srid = str(g('srid') or '25830')
        lat, lng = utm_a_geo(x, y, int(srid[-2:]) if srid.startswith('258') else 30)
        muni = muni_de(g('municipalities'), prov_de(g('provinces')), lat, lng)
        dir_ = solo_calle(g('road_name') or g('establishment_address')) if tipo in ('vut', 'rural') else bonito(g('establishment_address'))[:140]
        anadir('an', g('id').split('.')[0], tipo, muni, lat, lng, g('name') if tipo not in ('vut',) or len(g('name')) > 3 else '', dir_, g('tot_gen_places'), g('registration_code'), g('url'))


def cataluna():
    log('Cataluña…')
    ruta = os.path.join(TMP, 'cat.csv'); bajar('https://analisi.transparenciacatalunya.cat/resource/t2h3-cgys.csv?$limit=1000000', ruta, t=600)
    h, filas = tabla(texto(open(ruta, 'rb').read()), ',')
    i = {c: k for k, c in enumerate(h)}
    TIPO = {"habitatges d us turistic": 'vut', 'turisme rural': 'rural', 'campings': 'camping', 'apartaments turistics': 'apartamento'}
    regs = []
    for r in filas:
        g = lambda c, r=r: r[i[c]] if c in i and i[c] < len(r) else ''
        te = norm(g('tipus_establiment'))
        tipo = TIPO.get(te)
        if te == 'hotels':
            tipo = 'hostal' if 'hostal' in norm(g('grup')) else 'hotel'
        if not tipo:
            continue     # «llars compartides» (habitaciones en casa del titular) y áreas de autocaravanas no se publican
        muni = (g('codi_municipi_idescat') or '')[:5]
        ref = re.sub(r'\s', '', g('referencia_cadastral'))[:14]
        regs.append((g, tipo, muni, ref))
    refs = defaultdict(set)
    for g, tipo, muni, ref in regs:
        if len(ref) == 14:
            refs[muni].add(ref)
    catastro(refs)
    for g, tipo, muni, ref in regs:
        pt = CAT.get(ref) or []
        lat, lng = (pt[0], pt[1]) if len(pt) == 2 else (None, None)
        dir_ = solo_calle(con_numero(g('tipus_de_via'), g('nom_de_la_via'), '')) if tipo == 'vut' else con_numero(g('tipus_de_via'), g('nom_de_la_via'), g('numero'))
        anadir('ct', (g('n_mero_inscripci') or ref or str(len(SALIDA))).replace('/', '-'), tipo, muni, lat, lng, g('r_tol'), dir_, g('total_places'), g('n_mero_inscripci'))


def valencia():
    log('C. Valenciana…')
    ruta = os.path.join(TMP, 'val.csv'); bajar('https://dadesobertes.gva.es/dataset/758f8f8e-c5af-4622-b268-a6c591710a51/resource/b1bdc28e-9813-422a-ab7a-63c21290493d/download/lista-de-viviendas-turisticas.csv', ruta, t=600)
    h, filas = tabla(texto(open(ruta, 'rb').read()))
    i = {c: k for k, c in enumerate(h)}
    regs = []
    for r in filas:
        g = lambda c, r=r: r[i[c]] if c in i and i[c] < len(r) else ''
        p, m = re.sub(r'\D', '', g('cod_provincia')), re.sub(r'\D', '', g('cod_municipio'))
        muni = m.zfill(5) if len(m) >= 4 else (p.zfill(2) + m.zfill(3)) if p and m else muni_de(g('municipio'), prov_de(g('provincia')))
        ref = re.sub(r'\s', '', g('ref_catastral'))[:14]
        regs.append((g, muni, ref))
    refs = defaultdict(set)
    for g, muni, ref in regs:
        if len(ref) == 14:
            refs[muni].add(ref)
    catastro(refs)
    for g, muni, ref in regs:
        pt = CAT.get(ref) or []
        lat, lng = (pt[0], pt[1]) if len(pt) == 2 else (None, None)
        anadir('vc', g('signatura').replace('/', '-') or ref, 'vut', muni, lat, lng, g('nombre'), solo_calle(g('direccion')), g('plazas_totales'), g('signatura'), g('web'))


def castilla_leon():
    log('Castilla y León…')
    h, filas = tabla(texto(bajar('https://datosabiertos.jcyl.es/web/jcyl/risp/es/turismo/viviendas-uso-turistico/1284748762495.csv')))
    i = {c.strip(): k for k, c in enumerate(h)}
    for r in filas:
        g = lambda c: r[i[c]].strip() if c in i and i[c] < len(r) else ''
        lat, lng = num(g('GPS.Latitud')), num(g('GPS.Longitud'))
        prov = prov_de(g('Provincia'))
        if not en_espana(lat, lng):
            res = geocodificar(f"{g('Dirección')}, {g('Municipio')}, {g('Provincia')}")
            lat, lng = (res[0], res[1]) if res else (None, None)
        muni = muni_de(g('Municipio'), prov, lat, lng)
        anadir('cl', g('N.Registro').replace('/', '-'), 'vut', muni, lat, lng, g('Nombre'), solo_calle(g('Dirección')), g('Plazas'), g('N.Registro'), g('web'))


def madrid():
    log('C. de Madrid…')
    h, filas = tabla(texto(bajar('https://datos.comunidad.madrid/dataset/ef437c50-5b26-4843-92c3-d8eef5507fac/resource/260e80ac-2062-41f6-9f96-4902675b1078/download/alojamientos_turisticos.csv')))
    i = {c.strip(): k for k, c in enumerate(h)}
    TIPO = {'viviendas de uso tu': 'vut', 'hotel': 'hotel', 'hotel rural': 'hotel', 'hotel apart': 'hotel', 'hostal': 'hostal', 'casa huespedes': 'pension',
            'pension': 'pension', 'apart turistico': 'apartamento', 'casa rural': 'rural', 'apartamento rural': 'rural', 'hosterias': 'rural', 'camping': 'camping'}
    for r in filas:
        g = lambda c: r[i[c]].strip() if c in i and i[c] < len(r) else ''
        tipo = TIPO.get(norm(g('alojamiento_tipo')))
        if not tipo:
            continue
        via = con_numero(g('via_tipo'), g('via_nombre'), g('numero'))
        res = geocodificar(f"{via}, {g('cdpostal')} {g('localidad')}, Madrid")
        lat, lng, mc = (res[0], res[1], res[2]) if res else (None, None, '')
        muni = mc if re.fullmatch(r'28\d{3}', mc or '') else muni_de(g('localidad'), '28', lat, lng)
        anadir('md', g('signatura').replace('/', '-') or norm(via), tipo, muni, lat, lng, g('denominacion') if tipo != 'vut' else '',
               solo_calle(via) if tipo == 'vut' else via, None, g('signatura'))


FUENTES = [('Canarias', canarias), ('Andalucía', andalucia), ('Cataluña', cataluna), ('C. Valenciana', valencia), ('Castilla y León', castilla_leon), ('C. de Madrid', madrid)]


def main():
    os.makedirs(TMP, exist_ok=True); os.makedirs(PUBLICO, exist_ok=True)
    estado = {}
    for nombre, fn in FUENTES:
        t0 = time.time()
        try:
            fn(); estado[nombre] = 'ok'
        except Exception as e:
            estado[nombre] = 'error: ' + repr(e)[:150]
            log('ERROR en', nombre, repr(e)[:200])
        log(f'  {nombre}: {round(time.time() - t0)} s')
        guardar_cache('geocodificacion.json', GEO); guardar_cache('catastro.json', CAT)
    gen = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    indice = {}
    for muni, lst in sorted(SALIDA.items()):
        vistos, limpio = set(), []
        for r in lst:
            if r['id'] in vistos:
                continue
            vistos.add(r['id']); limpio.append(r)
        json.dump({'m': muni, 'gen': gen, 'items': limpio}, open(os.path.join(PUBLICO, f'{muni}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        indice[muni] = len(limpio)
    meta = {'gen': gen, 'total': sum(indice.values()), 'municipios_con_datos': len(indice), 'fuentes': estado,
            'por_tipo': {k[5:]: v for k, v in ST.items() if k.startswith('tipo ')}, 'estadisticas': {k: v for k, v in ST.items() if not k.startswith('tipo ')},
            'geocodificadas_esta_vez': geocodificadas,
            'licencias': 'Registros oficiales de turismo de Canarias, Andalucía, Cataluña, Comunitat Valenciana, Castilla y León y Comunidad de Madrid (datos abiertos). Ubicación: © Dirección General del Catastro; CartoCiudad © IGN/CNIG.',
            'registro': LOG[-150:], 'municipios': indice}
    json.dump(meta, open(os.path.join(PUBLICO, 'indice.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    log('TOTAL', meta['total'], 'en', len(indice), 'municipios ·', dict(ST))


if __name__ == '__main__':
    main()
