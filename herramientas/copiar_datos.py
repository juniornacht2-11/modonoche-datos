#!/usr/bin/env python3
"""Copia los datos públicos de Barcelona (locales y agenda) y descarga miniaturas de las fotos de Wikimedia Commons que
OpenStreetMap enlaza a esos locales, con autor y licencia, para preparar el diseño con contenido real."""
import json, os, re, sys, time, urllib.parse, urllib.request
LOG = []
def log(*a): LOG.append(' '.join(map(str, a))); print(*a)
B = 'https://juniornacht2-11.github.io/modonoche-datos'
UA = {'User-Agent': 'MODO-NOCHE/1.0 (diseño; github.com/juniornacht2-11/modonoche-datos)'}
os.makedirs('copia/fotos', exist_ok=True)
def get(u, t=60):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r: return r.read()
for f in ['locales/08019.json', 'eventos/08019.json', 'eventos/indice.json']:
    try:
        b = get(f'{B}/{f}'); open('copia/' + f.replace('/', '_'), 'wb').write(b); print(f, len(b))
    except Exception as e: print(f, 'ERROR', e)
els = json.load(open('copia/locales_08019.json'))['elements']
con = []
for e in els:
    t = e.get('tags', {}); c = t.get('wikimedia_commons') or ''
    img = t.get('image') or ''
    m = re.match(r'^(File:.+\.(?:jpe?g|png|webp))$', c, re.I) or re.search(r'commons\.wikimedia\.org/wiki/(File:[^?#]+\.(?:jpe?g|png|webp))', img, re.I)
    if m: con.append((e, urllib.parse.unquote(m.group(1)).replace('_', ' ')))
# Locales con Wikidata: su imagen principal (P18) también es de Commons. Peticiones agrupadas (50 por llamada) y despacio, para no saturar Wikidata.
prio = lambda e: 0 if (e['tags'].get('amenity') in ('nightclub', 'music_venue', 'events_venue', 'bar', 'pub')) else 1 if e['tags'].get('amenity') == 'restaurant' else 2
wd = sorted([e for e in els if e['tags'].get('wikidata') and not any(x[0] is e for x in con)], key=prio)
wd = [e for e in wd if prio(e) < 2] + [e for e in wd if prio(e) == 2][:12]
for k in range(0, len(wd), 50):
    grupo = wd[k:k + 50]
    try:
        j = json.loads(get('https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&ids=' + '|'.join(e['tags']['wikidata'] for e in grupo), 60))
        for e in grupo:
            v = ((j.get('entities', {}).get(e['tags']['wikidata']) or {}).get('claims') or {}).get('P18') or []
            if v: con.append((e, 'File:' + v[0]['mainsnak']['datavalue']['value']))
    except Exception as ex: log('wikidata grupo', k, repr(ex)[:200])
    time.sleep(2)
log('locales con foto de Commons:', len(con))
info = []
for e, fname in con[:80]:
    t = e['tags']
    try:
        api = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=800&titles=' + urllib.parse.quote(fname)
        j = json.loads(get(api)); p = next(iter(j['query']['pages'].values())); ii = p['imageinfo'][0]; md = ii.get('extmetadata', {})
        th = ii.get('thumburl'); out = f"copia/fotos/{e['type']}_{e['id']}.jpg"
        open(out, 'wb').write(get(th))
        info.append({'id': f"{e['type']}/{e['id']}", 'nombre': t.get('name'), 'amenity': t.get('amenity') or t.get('tourism'), 'archivo': fname, 'pagina': ii.get('descriptionurl'),
                     'autor': re.sub('<[^>]+>', '', (md.get('Artist') or {}).get('value', ''))[:120], 'licencia': (md.get('LicenseShortName') or {}).get('value', ''), 'foto': out[6:]})
    except Exception as ex: log('fallo', fname, repr(ex)[:200])
    time.sleep(0.5)
json.dump(info, open('copia/fotos/creditos.json', 'w'), ensure_ascii=False, indent=1)
print('fotos descargadas', len(info))

open('copia/fotos/log.txt', 'w').write('\n'.join(LOG))
