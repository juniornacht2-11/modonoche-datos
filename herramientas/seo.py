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
MIN_LOCALES = int(os.environ.get('MIN_LOCALES', '1'))
MAX_MUNI = int(os.environ.get('MAX_MUNI', '5000'))      # páginas de municipio (los de más locales primero)
MAX_ESTILO = int(os.environ.get('MAX_ESTILO', '1800'))  # páginas «Discotecas en X», «Música en directo en X»…
MAX_ZONA = int(os.environ.get('MAX_ZONA', '1500'))      # páginas de pueblos y barrios (Magaluf, Malasaña…)
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


AMB = {'directo': ('Música en directo', 'musica-en-directo'), 'coctel': ('Coctelerías y cócteles', 'cocteles'), 'lgtb': ('Ambiente LGTBI+', 'ambiente-lgtbi'),
       'terraza': ('Terrazas para tomar algo', 'terrazas-de-copas'), 'karaoke': ('Karaoke', 'karaoke'), 'latino': ('Música latina y reguetón', 'musica-latina'),
       'electronica': ('Música electrónica y techno', 'musica-electronica'), 'rock': ('Rock e indie', 'rock-e-indie'), 'jazz': ('Jazz y blues', 'jazz-y-blues'),
       'flamenco': ('Flamenco y rumba', 'flamenco'), 'hiphop': ('Hip hop y R&B', 'hip-hop'), 'pop': ('Pop y música comercial', 'pop-y-comercial')}
AMB_RX = {'latino': r'latin|salsa|bachata|regga?eton|reguet|merengue|cumbia|kizomba|dembow', 'electronica': r'techno|tecno|\bhouse\b|electr[oó]nic|\bedm\b|trance|drum.?n.?bass|\bdnb\b|minimal',
          'rock': r'\brock|metal|punk|\bindie\b|grunge', 'jazz': r'jazz|blues|swing|\bsoul\b', 'flamenco': r'flamenc|rumba|sevillana|tablao', 'hiphop': r'hip.?hop|\brap\b|\btrap\b|r&b|\brnb\b',
          'pop': r'\bpop\b|comercial|remember|revival|\b(80|90)s\b|ochenta|noventa'}


def ambiente(t, n):
    out = set(x for x in str(t.get('mn:estilos') or '').split(';') if x in AMB)
    txt = ' '.join(str(t.get(k) or '') for k in ('music', 'music:genre', 'genre', 'dance:style'))
    for k, rx in AMB_RX.items():
        if re.search(rx, txt, re.I) or re.search(rx, n, re.I) or (t.get('description') and re.search(rx, t['description'], re.I)):
            out.add(k)
    if t.get('live_music') == 'yes': out.add('directo')
    if t.get('outdoor_seating') in ('yes', 'only'): out.add('terraza')
    if t.get('lgbtq') in ('primary', 'only', 'welcome', 'yes') or re.search(r'\b(lgtb|lgbt|gay|queer|lesbi)', n, re.I): out.add('lgtb')
    if t.get('drink:cocktail') in ('yes', 'only') or t.get('cocktails') == 'yes' or re.search(r'cocktail|c[oò]ctel|mixolog', n, re.I): out.add('coctel')
    if t.get('karaoke') == 'yes' or re.search('karaoke', n, re.I): out.add('karaoke')
    return sorted(out)


def ficha(el):
    t = el.get('tags') or {}
    n = (t.get('name') or '').strip()
    if not n:
        return None
    calle = ' '.join(x for x in [t.get('addr:street') or t.get('addr:place') or '', t.get('addr:housenumber') or ''] if x).strip()
    d = {'n': n[:90], 'dir': (calle or t.get('addr:full') or '')[:90], 'web': bool(t.get('website') or t.get('contact:website')), 'hor': bool(t.get('opening_hours')),
         'lat': el.get('lat'), 'lng': el.get('lon'), 'amb': ambiente(t, n), 'id': f"{el.get('type')}/{el.get('id')}"}
    if t.get('mn:motivo'):
        d['dest'] = {'m': t['mn:motivo'][:140], 'f': t.get('mn:fuente') or '', 'top': t.get('mn:top') == 'yes'}
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
a{color:#22D3EE}main{max-width:900px;margin:auto;padding:20px 16px 48px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:16px max(16px,calc((100% - 868px)/2));border-bottom:1px solid #29283A}
.logo{font-family:"Unbounded",system-ui,sans-serif;font-weight:800;font-size:19px;letter-spacing:-.015em;color:#F5F3FF;text-decoration:none;display:inline-flex;align-items:baseline;line-height:1}.logo em{font-style:normal;color:transparent;background:linear-gradient(90deg,#C084FC,#A855F7 45%,#22D3EE);-webkit-background-clip:text;background-clip:text}.logo img{height:1.22em;width:auto;margin-left:.28em;filter:drop-shadow(0 0 .3em rgba(168,85,247,.5))}h1{font-size:clamp(26px,5vw,40px);line-height:1.15;margin:18px 0 10px}
h2{font-size:20px;margin:30px 0 8px;color:#C7FF4A}.lead{color:#A5A2B5}.cta{display:inline-block;margin:14px 0;padding:12px 20px;border-radius:12px;background:#A855F7;color:#fff;font-weight:700;text-decoration:none}
.cta.sec{background:transparent;border:1px solid #3a3850;color:#F5F3FF}ul.l{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
ul.l li{background:#101019;border:1px solid #29283A;border-radius:12px;padding:10px 12px}ul.l b{display:block}ul.l b a{color:#F5F3FF;text-decoration:none}ul.l b a:hover{text-decoration:underline}ul.l span{font-size:13px;color:#A5A2B5}.n{color:#7C798E;font-size:14px}
.chips a{display:inline-block;margin:4px 6px 0 0;padding:6px 12px;border:1px solid #3a3850;border-radius:999px;text-decoration:none;color:#F5F3FF;font-size:14px}
ul.l em.dest{display:inline-block;font:700 10px/1 ui-monospace,monospace;letter-spacing:.1em;padding:4px 7px;border-radius:99px;margin-bottom:5px;background:rgba(168,85,247,.18);color:#d8b4fe;font-style:normal}
ul.l em.dest.dtop{background:#C7FF4A;color:#0b0b10}ul.l span.mot{display:block;font-size:12px;color:#7C798E;margin-top:3px}
footer{margin-top:40px;font-size:13px;color:#7C798E;border-top:1px solid #29283A;padding-top:14px}"""


def pagina(titulo, desc, canon, cuerpo, og_img='og.png', ld=None):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titulo)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="MODO NOCHE"><meta property="og:title" content="{E(titulo)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(canon)}"><meta property="og:image" content="{BASE}/{og_img}"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#07070B">
<link rel="icon" href="/icono-192.png"><link rel="apple-touch-icon" href="/icono-180.png">{f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ''}
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@800&amp;text=MODNCHE%20&amp;display=swap"><style>{CSS}</style></head><body><header class="top"><a class="logo" href="/"><span>MODO <em>NOCHE</em></span><img src="/logo-pin.svg" alt="" width="17" height="23"></a><a href="/ocio-nocturno/">Ciudades</a></header><main>{cuerpo}
<footer>Datos de locales: © colaboradores de <a href="https://www.openstreetmap.org/copyright" rel="nofollow">OpenStreetMap</a> (ODbL). Alojamientos: registros oficiales de turismo de las comunidades autónomas (datos abiertos). Municipios: INE. Sin precios inventados: la información de cada local la publica el propio local.</footer></main></body></html>"""


def lista(items, n=24, c=None):
    from urllib.parse import quote
    out = []
    for d in items[:n]:
        de = d.get('dest'); ins = mot = ''
        if de:
            ins = '<em class="dest dtop">TOP MUNDIAL</em>' if de['top'] else '<em class="dest">DESTACADA</em>'
            fu = (' · <a href="' + E(de['f']) + '" rel="nofollow noopener" target="_blank">fuente</a>') if de.get('f') else ''
            mot = '<span class="mot">' + E(de['m']) + fu + '</span>'
        nom = f"<a href=\"/#/local/{c}/{quote(d['id'], safe='')}/{d['k']}\">{E(d['n'])}</a>" if c and d.get('id') else E(d['n'])
        out.append(f"<li>{ins}<b>{nom}</b><span>{E(d['tipo'])}{(' · ' + E(d['dir'])) if d.get('dir') else ''}</span>{mot}</li>")
    return '<ul class="l">' + ''.join(out) + '</ul>'


def km(a, b, c, d):
    return math.hypot((a - c) * 111.2, (b - d) * 111.2 * math.cos(math.radians(a)))


def main():
    ix = get_json(DATOS + '/indice.json') or {}
    rix = (get_json(DATOS + '/registros/indice.json') or {}).get('municipios', {})
    cnt = ix.get('municipios') or {}
    cand = sorted([c for c, n in cnt.items() if n >= MIN_LOCALES and c in INFO], key=lambda c: -cnt[c])[:MAX_MUNI]
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
    rel = lambda u: u[len(BASE):]
    por_prov = defaultdict(list)
    for c in datos:
        por_prov[c[:2]].append(c)
    rank = lambda d: (0 if d.get('dest') and d['dest']['top'] else 1 if d.get('dest') else 2, not d['web'], not d['hor'], d['n'].lower())
    extra = []   # (url, título) de páginas de estilo y de zona, para el sitemap

    # ---- zonas: pueblos, pedanías y barrios con vida nocturna (lugares.json)
    lug = (get_json(DATOS + '/lugares.json') or {}).get('l') or []
    zonas = defaultdict(list)
    cands_z = []
    for nm, c, la, lo, tp in lug:
        if c not in datos or tp not in ('t', 'v', 's', 'q', 'n') or la is None:
            continue
        cerca = [d for d in datos[c] if d['k'] in ('fiesta', 'cenas') and d.get('lat') is not None and km(la, lo, d['lat'], d['lng']) <= 1.2]
        nf = sum(1 for d in cerca if d['k'] == 'fiesta')
        if nf >= 4 and len(cerca) >= 10:
            cands_z.append((len(cerca), nm, c, la, lo, cerca))
    cands_z.sort(key=lambda x: -x[0])
    usados = set()
    for n_, nm, c, la, lo, cerca in cands_z:
        sl = f"{slug(nm)}-{slug(INFO[c]['nombre'])}-{c}"
        if sl in usados or len(usados) >= MAX_ZONA:
            continue
        usados.add(sl); zonas[c].append((nm, sl, cerca, la, lo))

    # ---- páginas de municipio
    n_estilo = 0
    for c, lst in datos.items():
        i = INFO[c]; nom = i['nombre']; prov = PROV.get(c[:2], '')
        F = sorted([d for d in lst if d['k'] == 'fiesta'], key=rank); C = sorted([d for d in lst if d['k'] == 'cenas'], key=rank); H = sorted([d for d in lst if d['k'] == 'hoteles'], key=rank)
        clubs = [d for d in F if d.get('sub') in ('nightclub', 'music_venue', 'concert_hall', 'theatre')]; bares = [d for d in F if d.get('sub') in ('bar', 'pub')]
        dest = [d for d in F if d.get('dest')]
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
        # páginas de estilo de este municipio
        estilos = []
        if n_estilo < MAX_ESTILO and (i['pob'] >= 15000 or len(clubs) >= 3):
            grupos = []
            if len(clubs) >= 3:
                grupos.append(('Discotecas y clubes', 'discotecas', clubs))
            for k, (tit, sl) in AMB.items():
                g = sorted([d for d in F if k in d['amb']], key=rank)
                if len(g) >= 3:
                    grupos.append((tit, sl, g))
            for tit, sl, g in grupos:
                if n_estilo >= MAX_ESTILO:
                    break
                u = f"{BASE}/ocio-nocturno/{sl}-en-{slug(nom)}-{c}"
                cu = f"""<p class="n"><a href="/ocio-nocturno/">Ciudades</a> › <a href="/ocio-nocturno/provincia-{slug(prov)}">{E(prov)}</a> › <a href="{rel(url[c])}">{E(nom)}</a></p>
<h1>{E(tit)} en {E(nom)}</h1><p class="lead">{len(g)} sitios en {E(nom)} según los datos abiertos de OpenStreetMap{', con los destacados por rankings y guías primero' if any(d.get('dest') for d in g) else ''}. Toca para ver horarios, cómo llegar y planes cerca.</p>
<a class="cta" href="/#/resultados/{c}/hoy/2/fiesta">Ver en el mapa y con horarios</a>""" + lista(g, 60, c)
                tt = f'{tit} en {nom} | MODO NOCHE'
                open(os.path.join(OUT, 'ocio-nocturno', u.rsplit('/', 1)[1] + '.html'), 'w', encoding='utf-8').write(
                    pagina(tt, f'{tit} en {nom} ({prov}): {len(g)} sitios con dirección, horario y web. Datos abiertos, sin precios inventados.', u, cu))
                estilos.append((tit, u)); extra.append(u); n_estilo += 1
        cuerpo = f"""<p class="n"><a href="/ocio-nocturno/">Ciudades</a> › <a href="/ocio-nocturno/provincia-{slug(prov)}">{E(prov)}</a></p>
<h1>Ocio nocturno en {E(nom)}</h1>
<p class="lead">En {E(nom)} hay {E(resumen)} en MODO NOCHE. Elige con quién sales y te proponemos planes con sitios reales y cercanos entre sí: cena y copa, ruta de bares, discoteca o la noche completa con hotel.</p>
<a class="cta" href="{app}">Organiza tu noche en {E(nom)}</a> <a class="cta sec" href="/#/resultados/{c}/hoy/2/fiesta">Ver locales para salir</a>"""
        if dest:
            cuerpo += f'<h2>Las discotecas más destacadas de {E(nom)}</h2><p class="n">Por rankings internacionales (The World\'s 100 Best Clubs, DJ Mag Top 100 Clubs), guías de ocio y prensa. Cada una con su fuente.</p>' + lista(dest, 30, c)
        if estilos:
            cuerpo += f'<h2>Por estilo en {E(nom)}</h2><p class="chips">' + ''.join(f'<a href="{rel(u)}">{E(t)}</a>' for t, u in estilos) + '</p>'
        if zonas.get(c):
            cuerpo += f'<h2>Zonas para salir en {E(nom)}</h2><p class="chips">' + ''.join(f'<a href="/ocio-nocturno/{sl}">{E(nm)}</a>' for nm, sl, *_ in zonas[c]) + '</p>'
        if clubs:
            cuerpo += f'<h2>Discotecas, clubes y música en directo en {E(nom)}</h2>' + lista(clubs, 24, c)
        if bares:
            cuerpo += f'<h2>Bares y pubs en {E(nom)}</h2>' + lista(bares, 24, c)
        if C:
            cuerpo += f'<h2>Dónde cenar en {E(nom)}</h2>' + (f'<p class="n">Cocinas más habituales: {E(", ".join(k for k, v in coc))}.</p>' if coc else '') + lista(C, 24, c) + f'<p><a href="/#/resultados/{c}/hoy/2/cenas">Ver todos los restaurantes de {E(nom)}</a></p>'
        if H or vut:
            cuerpo += f'<h2>Dónde dormir en {E(nom)}</h2>' + (lista(H, 16, c) if H else '') + (f'<p class="n">Además, {vut:,} alojamientos inscritos en el registro oficial de turismo (viviendas turísticas, casas rurales, apartamentos…).</p>'.replace(',', '.') if vut else '') + f'<p><a href="/#/resultados/{c}/hoy/2/hoteles">Ver alojamientos y precios en {E(nom)}</a></p>'
        if vecinos:
            cuerpo += '<h2>Cerca de ' + E(nom) + '</h2><p class="chips">' + ''.join(f'<a href="{rel(url[x])}">{E(INFO[x]["nombre"])}</a>' for x in vecinos) + '</p>'
        ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Ciudades', 'item': f'{BASE}/ocio-nocturno/'},
            {'@type': 'ListItem', 'position': 2, 'name': prov, 'item': f'{BASE}/ocio-nocturno/provincia-{slug(prov)}'},
            {'@type': 'ListItem', 'position': 3, 'name': nom, 'item': url[c]}]}
        open(os.path.join(OUT, 'ocio-nocturno', f"{slug(nom)}-{c}.html"), 'w', encoding='utf-8').write(pagina(titulo, desc, url[c], cuerpo, ld=ld))
        # página propia de cada discoteca destacada
        from urllib.parse import quote
        for d in dest:
            sl = f"local-{slug(d['n'])}-{c}"; u = f'{BASE}/ocio-nocturno/{sl}'; de = d['dest']
            fu = f' (<a href="{E(de["f"])}" rel="nofollow noopener" target="_blank">ver fuente</a>)' if de.get('f') else ''
            mapa = f'https://www.google.com/maps/search/?api=1&query={d["lat"]},{d["lng"]}' if d.get('lat') is not None else ''
            cu = f"""<p class="n"><a href="/ocio-nocturno/">Ciudades</a> › <a href="/ocio-nocturno/provincia-{slug(prov)}">{E(prov)}</a> › <a href="{rel(url[c])}">{E(nom)}</a></p>
<h1>{E(d['n'])}</h1><p class="lead">{E(d['tipo'])} en {E(nom)}{(' · ' + E(d['dir'])) if d.get('dir') else ''}.</p>
<p>{'<b style="color:#C7FF4A">TOP MUNDIAL</b> · ' if de['top'] else '<b style="color:#d8b4fe">DESTACADA</b> · '}{E(de['m'])}{fu}.</p>
{('<p>Estilo: ' + E(', '.join(AMB[k][0] for k in d['amb'])) + '.</p>') if d.get('amb') else ''}
<a class="cta" href="/#/local/{c}/{quote(d['id'], safe='')}/fiesta">Ver horario, cómo llegar y planes cerca</a> {f'<a class="cta sec" href="{mapa}" rel="nofollow noopener" target="_blank">Ver en el mapa</a>' if mapa else ''}
<h2>Más para salir en {E(nom)}</h2>""" + lista([x for x in F if x is not d], 12, c)
            open(os.path.join(OUT, 'ocio-nocturno', sl + '.html'), 'w', encoding='utf-8').write(
                pagina(f"{d['n']} ({nom}): {de['m']} | MODO NOCHE", f"{d['n']}, {d['tipo'].lower()} en {nom}. {de['m']}. Horario, dirección y planes cerca en MODO NOCHE.", u, cu))
            extra.append(u)
        # páginas de zona
        for nm, sl, cerca, la, lo in zonas.get(c, []):
            Fz = sorted([d for d in cerca if d['k'] == 'fiesta'], key=lambda d: (rank(d)[0], km(la, lo, d['lat'], d['lng'])))
            Cz = sorted([d for d in cerca if d['k'] == 'cenas'], key=lambda d: (rank(d)[0], km(la, lo, d['lat'], d['lng'])))
            u = f'{BASE}/ocio-nocturno/{sl}'
            from urllib.parse import quote
            cu = f"""<p class="n"><a href="/ocio-nocturno/">Ciudades</a> › <a href="/ocio-nocturno/provincia-{slug(prov)}">{E(prov)}</a> › <a href="{rel(url[c])}">{E(nom)}</a></p>
<h1>Ocio nocturno en {E(nm)} ({E(nom)})</h1><p class="lead">A menos de 1 km de {E(nm)} hay {len(Fz)} sitios para salir y {len(Cz)} restaurantes en MODO NOCHE. Planes con sitios reales y cerca a pie.</p>
<a class="cta" href="/#/plan/{c}~{quote(nm)}">Organiza tu noche en {E(nm)}</a>""" + (f'<h2>Para salir en {E(nm)}</h2>' + lista(Fz, 30, c) if Fz else '') + (f'<h2>Para cenar en {E(nm)}</h2>' + lista(Cz, 18, c) if Cz else '') + \
                f'<p><a href="{rel(url[c])}">Todo el ocio nocturno de {E(nom)}</a></p>'
            open(os.path.join(OUT, 'ocio-nocturno', sl + '.html'), 'w', encoding='utf-8').write(
                pagina(f'Ocio nocturno en {nm} ({nom}): dónde salir, bares y discotecas | MODO NOCHE', f'Dónde salir de noche en {nm} ({nom}, {prov}): {len(Fz)} bares, pubs y discotecas y {len(Cz)} restaurantes cerca. Datos abiertos.', u, cu))
            extra.append(u)
    # provincias
    for p, cs in por_prov.items():
        prov = PROV.get(p, p)
        cs.sort(key=lambda x: -INFO[x]['pob'])
        cuerpo = f'<p class="n"><a href="/ocio-nocturno/">Ciudades</a></p><h1>Ocio nocturno en la provincia de {E(prov)}</h1><p class="lead">Elige municipio para ver discotecas, bares, restaurantes y alojamientos.</p><p class="chips">' + \
            ''.join(f'<a href="{rel(url[x])}">{E(INFO[x]["nombre"])}</a>' for x in cs) + '</p>'
        open(os.path.join(OUT, 'ocio-nocturno', f'provincia-{slug(prov)}.html'), 'w', encoding='utf-8').write(
            pagina(f'Ocio nocturno en {prov}: dónde salir por municipios | MODO NOCHE', f'Discotecas, bares, restaurantes y alojamientos en los municipios de {prov}.', f'{BASE}/ocio-nocturno/provincia-{slug(prov)}', cuerpo))
    # índice
    top = sorted(datos, key=lambda x: -INFO[x]['pob'])[:40]
    cuerpo = '<h1>Ocio nocturno en España, ciudad por ciudad</h1><p class="lead">Discotecas, bares, restaurantes y alojamientos de toda España con datos abiertos.</p><a class="cta" href="/">Organiza tu noche</a><h2>Ciudades más buscadas</h2><p class="chips">' + \
        ''.join(f'<a href="{rel(url[x])}">{E(INFO[x]["nombre"])}</a>' for x in top) + '</p><h2>Por provincias</h2><p class="chips">' + \
        ''.join(f'<a href="/ocio-nocturno/provincia-{slug(PROV.get(p, p))}">{E(PROV.get(p, p))}</a>' for p in sorted(por_prov, key=lambda p: slug(PROV.get(p, p)))) + '</p>'
    open(os.path.join(OUT, 'ocio-nocturno', 'index.html'), 'w', encoding='utf-8').write(pagina('Ocio nocturno en España por ciudades | MODO NOCHE', 'Dónde salir de noche en cada ciudad de España: discotecas, bares, cenas y alojamientos.', f'{BASE}/ocio-nocturno/', cuerpo))
    # sitemap y robots
    urls = [f'{BASE}/', f'{BASE}/para-locales', f'{BASE}/ocio-nocturno/'] + [f'{BASE}/ocio-nocturno/provincia-{slug(PROV.get(p, p))}' for p in por_prov] + [url[c] for c in datos] + extra
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join(f'<url><loc>{E(u)}</loc><lastmod>{HOY}</lastmod></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(OUT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    print('páginas', len(datos), 'estilo', n_estilo, 'zonas', sum(len(v) for v in zonas.values()), 'provincias', len(por_prov), 'urls', len(urls), flush=True)


if __name__ == '__main__':
    main()
