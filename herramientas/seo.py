"""MODO NOCHE · páginas por ciudad para buscadores (Google, Bing) + sitemap.xml + robots.txt.

Lee los datos ya publicados (locales semanales de OpenStreetMap y alojamientos de los registros oficiales)
y escribe en seo_out/ unas páginas HTML ligeras, una por municipio con locales, que enlazan a la web.
Se suben dentro del ZIP de la web (mismo dominio), así Google encuentra «ocio nocturno en <ciudad>».
"""
import html, json, math, os, re, time, unicodedata, urllib.request
from collections import Counter, defaultdict
import concurrent.futures as cf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.environ.get('DATOS', 'https://juniornacht2-11.github.io/modonoche-datos')
BASE = os.environ.get('BASE', 'https://modonoche.juniornacht2.workers.dev').rstrip('/')
OUT = os.path.join(RAIZ, 'seo_out')
MIN_LOCALES = int(os.environ.get('MIN_LOCALES', '12'))
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
HOY = time.strftime('%Y-%m-%d')
E = html.escape


def get_json(url):
    for i in range(3):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def slug(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def bonito_muni(n):
    m = re.match(r'^(.*), (El|La|Los|Las|L\'|Els|Les|O|A|Os|As|Sa|Es|Ses)$', n)
    if m:
        art = m.group(2)
        return (art + m.group(1)) if art.endswith("'") else f'{art} {m.group(1)}'
    return n


MUN = json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))
PROV = {p[0]: p[1] for p in MUN['provincias']}
INFO = {f[0]: {'nombre': bonito_muni(f[1].split('/')[0].strip()), 'lat': f[2], 'lng': f[3], 'pob': (f[4] if len(f) > 4 else 0) or 0} for f in MUN['municipios']}

FIESTA = {'nightclub': 'Discoteca o club', 'music_venue': 'Música en directo', 'concert_hall': 'Sala de conciertos', 'bar': 'Bar', 'pub': 'Pub', 'events_venue': 'Espacio de eventos', 'theatre': 'Sala de conciertos'}
ALOJ = {'hotel': 'Hotel', 'hostel': 'Albergue', 'guest_house': 'Hostal o pensión', 'apartment': 'Apartamento turístico', 'motel': 'Motel'}
COCINA = {'spanish': 'española', 'regional': 'regional', 'tapas': 'tapas', 'italian': 'italiana', 'pizza': 'pizza', 'japanese': 'japonesa', 'sushi': 'sushi', 'chinese': 'china',
          'mexican': 'mexicana', 'indian': 'india', 'mediterranean': 'mediterránea', 'seafood': 'marisco', 'burger': 'hamburguesas', 'asian': 'asiática', 'international': 'internacional',
          'vegetarian': 'vegetariana', 'vegan': 'vegana', 'steak_house': 'asador', 'argentinian': 'argentina', 'basque': 'vasca', 'catalan': 'catalana', 'galician': 'gallega', 'french': 'francesa',
          'thai': 'tailandesa', 'peruvian': 'peruana', 'greek': 'griega', 'lebanese': 'libanesa', 'kebab': 'kebab', 'fish': 'pescado', 'grill': 'parrilla'}


def ficha(el):
    t = el.get('tags') or {}
    n = (t.get('name') or '').strip()
    if not n:
        return None
    calle = ' '.join(x for x in [t.get('addr:street') or t.get('addr:place') or '', t.get('addr:housenumber') or ''] if x).strip()
    d = {'n': n[:90], 'dir': calle[:90], 'web': bool(t.get('website') or t.get('contact:website')), 'hor': bool(t.get('opening_hours'))}
    a, tu = t.get('amenity'), t.get('tourism')
    if a == 'restaurant':
        c = (t.get('cuisine') or '').split(';')[0].strip().lower()
        d.update(k='cenas', tipo='Restaurante' + (f' · cocina {COCINA[c]}' if c in COCINA else ''), coc=COCINA.get(c))
    elif tu in ALOJ:
        d.update(k='hoteles', tipo=ALOJ[tu])
    elif a in FIESTA:
        d.update(k='fiesta', tipo=FIESTA[a], sub=a)
    else:
        return None
    return d


CSS = """:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#07070B;color:#F5F3FF;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:#22D3EE}main{max-width:900px;margin:auto;padding:20px 16px 48px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 16px;border-bottom:1px solid #29283A}
.logo{font-weight:800;letter-spacing:-.01em;color:#F5F3FF;text-decoration:none;display:inline-flex;align-items:flex-end;gap:3px;line-height:1}.logo em{font-style:normal;color:transparent;background:linear-gradient(90deg,#C084FC,#A855F7 45%,#22D3EE);-webkit-background-clip:text;background-clip:text}.logo img{transform:translateY(3px)}h1{font-size:clamp(26px,5vw,40px);line-height:1.15;margin:18px 0 10px}
h2{font-size:20px;margin:30px 0 8px;color:#C7FF4A}.lead{color:#A5A2B5}.cta{display:inline-block;margin:14px 0;padding:12px 20px;border-radius:12px;background:#A855F7;color:#fff;font-weight:700;text-decoration:none}
.cta.sec{background:transparent;border:1px solid #3a3850;color:#F5F3FF}ul.l{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
ul.l li{background:#101019;border:1px solid #29283A;border-radius:12px;padding:10px 12px}ul.l b{display:block}ul.l span{font-size:13px;color:#A5A2B5}.n{color:#7C798E;font-size:14px}
.chips a{display:inline-block;margin:4px 6px 0 0;padding:6px 12px;border:1px solid #3a3850;border-radius:999px;text-decoration:none;color:#F5F3FF;font-size:14px}
footer{margin-top:40px;font-size:13px;color:#7C798E;border-top:1px solid #29283A;padding-top:14px}"""


def pagina(titulo, desc, canon, cuerpo, og_img='og.png', ld=None):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titulo)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="MODO NOCHE"><meta property="og:title" content="{E(titulo)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(canon)}"><meta property="og:image" content="{BASE}/{og_img}"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#07070B">
<link rel="icon" href="/icono-192.png"><link rel="apple-touch-icon" href="/icono-180.png">{f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ''}
<style>{CSS}</style></head><body><header class="top"><a class="logo" href="/">MODO <em>NOCHE</em><img src="/logo-pin.svg" alt="" width="17" height="23"></a><a href="/ocio-nocturno/">Ciudades</a></header><main>{cuerpo}
<footer>Datos de locales: © colaboradores de <a href="https://www.openstreetmap.org/copyright" rel="nofollow">OpenStreetMap</a> (ODbL). Alojamientos: registros oficiales de turismo de las comunidades autónomas (datos abiertos). Municipios: INE. Sin precios inventados: la información de cada local la publica el propio local.</footer></main></body></html>"""


def lista(items, n=24):
    out = []
    for d in items[:n]:
        out.append(f"<li><b>{E(d['n'])}</b><span>{E(d['tipo'])}{(' · ' + E(d['dir'])) if d.get('dir') else ''}</span></li>")
    return '<ul class="l">' + ''.join(out) + '</ul>'


def main():
    ix = get_json(DATOS + '/indice.json') or {}
    rix = (get_json(DATOS + '/registros/indice.json') or {}).get('municipios', {})
    cand = [c for c, n in (ix.get('municipios') or {}).items() if n >= MIN_LOCALES and c in INFO]
    print('municipios candidatos', len(cand), flush=True)
    datos = {}

    def uno(c):
        j = get_json(f'{DATOS}/locales/{c}.json')
        return c, [f for f in (ficha(e) for e in (j or {}).get('elements', [])) if f]
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for c, lst in ex.map(uno, cand):
            if lst:
                datos[c] = lst
    os.makedirs(os.path.join(OUT, 'ocio-nocturno'), exist_ok=True)
    url = {c: f"{BASE}/ocio-nocturno/{slug(INFO[c]['nombre'])}-{c}" for c in datos}
    por_prov = defaultdict(list)
    for c in datos:
        por_prov[c[:2]].append(c)
    rank = lambda d: (not d['web'], not d['hor'], d['n'].lower())
    for c, lst in datos.items():
        i = INFO[c]; nom = i['nombre']; prov = PROV.get(c[:2], '')
        F = sorted([d for d in lst if d['k'] == 'fiesta'], key=rank); C = sorted([d for d in lst if d['k'] == 'cenas'], key=rank); H = sorted([d for d in lst if d['k'] == 'hoteles'], key=rank)
        clubs = [d for d in F if d.get('sub') in ('nightclub', 'music_venue', 'concert_hall', 'theatre')]; bares = [d for d in F if d.get('sub') in ('bar', 'pub')]
        vut = rix.get(c, 0)
        coc = Counter(d['coc'] for d in C if d.get('coc')).most_common(4)
        partes = [f'{len(clubs)} discotecas y salas' if clubs else '', f'{len(bares)} bares y pubs' if bares else '', f'{len(C)} restaurantes' if C else '',
                  f'{len(H) + vut} alojamientos' if (H or vut) else '']
        partes = [re.sub(r'^(\d+)', lambda m: f'{int(m.group(1)):,}'.replace(',', '.'), x) for x in partes if x]
        resumen = (', '.join(partes[:-1]) + ' y ' + partes[-1]) if len(partes) > 1 else (partes[0] if partes else 'locales')
        titulo = f'Ocio nocturno en {nom}: discotecas, bares, cenas y dónde dormir | MODO NOCHE'
        desc = f'Planes para salir de noche en {nom} ({prov}): {resumen}. Horarios, webs y combinaciones cerca a pie, con datos abiertos y sin precios inventados.'
        vecinos = sorted((x for x in datos if x != c and INFO[x]['lat'] is not None and i['lat'] is not None), key=lambda x: (INFO[x]['lat'] - i['lat']) ** 2 + ((INFO[x]['lng'] - i['lng']) * math.cos(math.radians(i['lat']))) ** 2)[:10] if i['lat'] is not None else []
        app = f'/#/plan/{c}'
        cuerpo = f"""<p class="n"><a href="/ocio-nocturno/">Ciudades</a> › <a href="/ocio-nocturno/provincia-{slug(prov)}">{E(prov)}</a></p>
<h1>Ocio nocturno en {E(nom)}</h1>
<p class="lead">En {E(nom)} hay {E(resumen)} en MODO NOCHE. Elige con quién sales y te proponemos planes con sitios reales y cercanos entre sí: cena y copa, ruta de bares, discoteca o la noche completa con hotel.</p>
<a class="cta" href="{app}">Organiza tu noche en {E(nom)}</a> <a class="cta sec" href="/#/resultados/{c}/hoy/2/fiesta">Ver locales para salir</a>"""
        if clubs:
            cuerpo += f'<h2>Discotecas, clubes y música en directo en {E(nom)}</h2>' + lista(clubs)
        if bares:
            cuerpo += f'<h2>Bares y pubs en {E(nom)}</h2>' + lista(bares)
        if C:
            cuerpo += f'<h2>Dónde cenar en {E(nom)}</h2>' + (f'<p class="n">Cocinas más habituales: {E(", ".join(k for k, v in coc))}.</p>' if coc else '') + lista(C) + f'<p><a href="/#/resultados/{c}/hoy/2/cenas">Ver todos los restaurantes de {E(nom)}</a></p>'
        if H or vut:
            cuerpo += f'<h2>Dónde dormir en {E(nom)}</h2>' + (lista(H, 16) if H else '') + (f'<p class="n">Además, {vut:,} alojamientos inscritos en el registro oficial de turismo (viviendas turísticas, casas rurales, apartamentos…).</p>'.replace(',', '.') if vut else '') + f'<p><a href="/#/resultados/{c}/hoy/2/hoteles">Ver alojamientos y precios en {E(nom)}</a></p>'
        if vecinos:
            cuerpo += '<h2>Cerca de ' + E(nom) + '</h2><p class="chips">' + ''.join(f'<a href="{url[x][len(BASE):]}">{E(INFO[x]["nombre"])}</a>' for x in vecinos) + '</p>'
        ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Ciudades', 'item': f'{BASE}/ocio-nocturno/'},
            {'@type': 'ListItem', 'position': 2, 'name': prov, 'item': f'{BASE}/ocio-nocturno/provincia-{slug(prov)}'},
            {'@type': 'ListItem', 'position': 3, 'name': nom, 'item': url[c]}]}
        open(os.path.join(OUT, 'ocio-nocturno', f"{slug(nom)}-{c}.html"), 'w', encoding='utf-8').write(pagina(titulo, desc, url[c], cuerpo, ld=ld))
    # provincias
    for p, cs in por_prov.items():
        prov = PROV.get(p, p)
        cs.sort(key=lambda x: -INFO[x]['pob'])
        cuerpo = f'<p class="n"><a href="/ocio-nocturno/">Ciudades</a></p><h1>Ocio nocturno en la provincia de {E(prov)}</h1><p class="lead">Elige municipio para ver discotecas, bares, restaurantes y alojamientos.</p><p class="chips">' + \
            ''.join(f'<a href="{url[x][len(BASE):]}">{E(INFO[x]["nombre"])}</a>' for x in cs) + '</p>'
        open(os.path.join(OUT, 'ocio-nocturno', f'provincia-{slug(prov)}.html'), 'w', encoding='utf-8').write(
            pagina(f'Ocio nocturno en {prov}: dónde salir por municipios | MODO NOCHE', f'Discotecas, bares, restaurantes y alojamientos en los municipios de {prov}.', f'{BASE}/ocio-nocturno/provincia-{slug(prov)}', cuerpo))
    # índice
    top = sorted(datos, key=lambda x: -INFO[x]['pob'])[:40]
    cuerpo = '<h1>Ocio nocturno en España, ciudad por ciudad</h1><p class="lead">Discotecas, bares, restaurantes y alojamientos de toda España con datos abiertos.</p><a class="cta" href="/">Organiza tu noche</a><h2>Ciudades más buscadas</h2><p class="chips">' + \
        ''.join(f'<a href="{url[x][len(BASE):]}">{E(INFO[x]["nombre"])}</a>' for x in top) + '</p><h2>Por provincias</h2><p class="chips">' + \
        ''.join(f'<a href="/ocio-nocturno/provincia-{slug(PROV.get(p, p))}">{E(PROV.get(p, p))}</a>' for p in sorted(por_prov, key=lambda p: slug(PROV.get(p, p)))) + '</p>'
    open(os.path.join(OUT, 'ocio-nocturno', 'index.html'), 'w', encoding='utf-8').write(pagina('Ocio nocturno en España por ciudades | MODO NOCHE', 'Dónde salir de noche en cada ciudad de España: discotecas, bares, cenas y alojamientos.', f'{BASE}/ocio-nocturno/', cuerpo))
    # sitemap y robots
    urls = [f'{BASE}/', f'{BASE}/para-locales', f'{BASE}/ocio-nocturno/'] + [f'{BASE}/ocio-nocturno/provincia-{slug(PROV.get(p, p))}' for p in por_prov] + [url[c] for c in datos]
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join(f'<url><loc>{E(u)}</loc><lastmod>{HOY}</lastmod></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(OUT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    print('páginas', len(datos), 'provincias', len(por_prov), 'urls', len(urls), flush=True)


if __name__ == '__main__':
    main()
