"""Sondeo: email de contacto público (publicado en su propia web) de restaurantes, hoteles y discotecas de Barcelona (OpenStreetMap)."""
import json, os, re, urllib.parse, urllib.request, concurrent.futures as cf
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'}
j = json.loads(urllib.request.urlopen(urllib.request.Request('https://juniornacht2-11.github.io/modonoche-datos/locales/08019.json', headers=UA), timeout=120).read())
TIPO = {'restaurant': 'restaurante', 'nightclub': 'discoteca', 'hotel': 'hotel', 'guest_house': 'hostal', 'hostel': 'albergue', 'apartment': 'apartamentos'}
locs = []
for e in j.get('elements', []):
    t = e.get('tags') or {}
    k = TIPO.get(t.get('amenity')) or TIPO.get(t.get('tourism'))
    if k and t.get('name'):
        locs.append({'tipo': k, 'nombre': t['name'], 'web': t.get('website') or t.get('contact:website') or t.get('url') or '', 'email': t.get('email') or t.get('contact:email') or '',
                     'telefono': t.get('phone') or t.get('contact:phone') or ''})
MAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
MALOS = re.compile(r'(sentry|wixpress|example|exemple|ejemplo|\.png|\.jpg|\.webp|\.svg|\.gif|godaddy|domain|yourmail|email@|tu@|name@|nombre@|curriculum|^cv@|rrhh|jobs|empleo|feina|treball|work|privacy|privacidad|privacitat|dpo|lopd|rgpd|gdpr|legal|protecciondatos|abuse|noreply|no-reply|@sentry|@2x)', re.I)
def cfdecode(h):
    k = int(h[:2], 16); return ''.join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
def leer(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15).read(1_500_000).decode('utf-8', 'replace')
    except Exception: return ''
def buscar(x):
    if x['email'] or not x['web']: return x
    base = x['web'] if x['web'].startswith('http') else 'https://' + x['web']
    if any(d in base for d in ('facebook.com', 'instagram.com', 'tripadvisor', 'google.', 'thefork', 'eltenedor', 'booking.com')): return x
    vistos = []
    for ruta in ['', 'contacto', 'contacte', 'contact']:
        h = leer(urllib.parse.urljoin(base if base.endswith('/') else base + '/', ruta))
        if not h: continue
        for c in re.findall(r'data-cfemail="([0-9a-f]+)"', h):
            try: vistos.append(cfdecode(c))
            except Exception: pass
        for m in re.findall(r'mailto:([^"\'?>\s]+)', h): vistos.append(urllib.parse.unquote(m))
        vistos += MAIL.findall(h)
        if any(not MALOS.search(v) for v in vistos): break
    buenos = list(dict.fromkeys(v.strip().lower().rstrip('.\\') for v in vistos if not MALOS.search(v)))
    dom = urllib.parse.urlparse(base).netloc.replace('www.', '').split('.')[0]
    buenos.sort(key=lambda v: (dom not in v, not re.match(r'(info|hola|hello|contact|reserv|booking|events|eventos)', v)))
    x['email'] = buenos[0] if buenos else ''
    return x
with cf.ThreadPoolExecutor(24) as ex: res = list(ex.map(buscar, locs))
res.sort(key=lambda x: (x['tipo'], x['nombre'].lower()))
os.makedirs('salida', exist_ok=True); json.dump(res, open('salida/contactos_bcn.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
from collections import Counter
open('salida/sondeo.txt', 'w').write(json.dumps({'total': Counter(x['tipo'] for x in res), 'con_web': Counter(x['tipo'] for x in res if x['web']), 'con_email': Counter(x['tipo'] for x in res if x['email'])}, ensure_ascii=False))
