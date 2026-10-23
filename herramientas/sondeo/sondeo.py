"""Sondeo: contactos públicos (web, email, Instagram) de los locales destacados de Barcelona según lo publicado. Solo lectura."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
B = 'https://juniornacht2-11.github.io/modonoche-datos'
j = json.loads(urllib.request.urlopen(urllib.request.Request(B + '/locales/08019.json', headers={'User-Agent': 'MODO-NOCHE-sondeo'}), timeout=120).read())
out = []
for e in j.get('elements') or []:
    t = e.get('tags') or {}
    if not t.get('mn:motivo'): continue
    out.append({'n': t.get('name'), 'motivo': t.get('mn:motivo'), 'top': t.get('mn:top'), 'web': t.get('website') or t.get('contact:website') or t.get('url'),
                'email': t.get('email') or t.get('contact:email'), 'ig': t.get('contact:instagram') or t.get('instagram'), 'dir': ' '.join(x for x in [t.get('addr:street'), t.get('addr:housenumber')] if x) or t.get('addr:full'),
                'tipo': t.get('amenity'), 'id': f"{e.get('type')}/{e.get('id')}"})
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
