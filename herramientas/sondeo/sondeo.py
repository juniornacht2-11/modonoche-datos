"""Sondeo: email de contacto público en la web de cada discoteca de Barcelona (OpenStreetMap). Solo direcciones publicadas por el propio local."""
import json, os, re, urllib.parse, urllib.request, concurrent.futures as cf
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'}
j = json.loads(urllib.request.urlopen(urllib.request.Request('https://juniornacht2-11.github.io/modonoche-datos/locales/08019.json', headers=UA), timeout=120).read())
locs = []
for e in j.get('elements', []):
    t = e.get('tags') or {}
    if t.get('amenity') == 'nightclub' and t.get('name'):
        locs.append({'nombre': t['name'], 'web': t.get('website') or t.get('contact:website') or t.get('url') or '', 'email': t.get('email') or t.get('contact:email') or '',
                     'telefono': t.get('phone') or t.get('contact:phone') or '', 'calle': ' '.join(x for x in [t.get('addr:street', ''), t.get('addr:housenumber', '')] if x)})
MAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
MALOS = re.compile(r'(sentry|wixpress|example|\.png|\.jpg|\.webp|\.svg|godaddy|domain|yourmail|email@|tu@|name@|curriculum|cv@|rrhh|jobs|empleo|privacy|privacidad|dpo|lopd|rgpd|legal)', re.I)
def cfdecode(h):
    k = int(h[:2], 16); return ''.join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
def leer(u):
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read(2_000_000).decode('utf-8', 'replace')
    except Exception: return ''
    return b
def buscar(x):
    if x['email'] or not x['web']: return x
    base = x['web'] if x['web'].startswith('http') else 'https://' + x['web']
    vistos = []
    for ruta in ['', 'contacto', 'contacte', 'contact', 'es/contacto', 'info', 'aviso-legal', 'avis-legal', 'legal']:
        h = leer(urllib.parse.urljoin(base if base.endswith('/') else base + '/', ruta))
        if not h: continue
        for c in re.findall(r'data-cfemail="([0-9a-f]+)"', h): vistos.append(cfdecode(c))
        for m in re.findall(r'mailto:([^"\'?>\s]+)', h): vistos.append(urllib.parse.unquote(m))
        vistos += MAIL.findall(h)
        buenos = [v.strip().lower() for v in vistos if not MALOS.search(v)]
        if buenos: break
    buenos = list(dict.fromkeys(v.strip().lower().rstrip('.') for v in vistos if not MALOS.search(v)))
    dom = urllib.parse.urlparse(base).netloc.replace('www.', '')
    buenos.sort(key=lambda v: (dom.split('.')[0] not in v, not re.match(r'(info|hola|contact|reserv|booking|events|eventos)', v)))
    x['email'] = buenos[0] if buenos else ''; x['otros'] = buenos[1:4]
    return x
with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(buscar, locs))
res.sort(key=lambda x: x['nombre'].lower())
os.makedirs('salida', exist_ok=True); json.dump(res, open('salida/discotecas_bcn.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open('salida/sondeo.txt', 'w').write(f"total {len(res)} con email {sum(1 for x in res if x['email'])}\n")
