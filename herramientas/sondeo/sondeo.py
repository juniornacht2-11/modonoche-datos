"""Sondeo: discotecas de Barcelona con contacto público (OpenStreetMap). Escribe salida/discotecas_bcn.json."""
import json, os, urllib.request
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
j = json.loads(urllib.request.urlopen(urllib.request.Request('https://juniornacht2-11.github.io/modonoche-datos/locales/08019.json', headers=UA), timeout=120).read())
out = []
for e in j.get('elements', []):
    t = e.get('tags') or {}
    if t.get('amenity') not in ('nightclub',) or not t.get('name'): continue
    out.append({'id': f"{e.get('type')}/{e.get('id')}", 'nombre': t.get('name'), 'email': t.get('email') or t.get('contact:email') or '',
                'web': t.get('website') or t.get('contact:website') or t.get('url') or '', 'instagram': t.get('contact:instagram') or '',
                'telefono': t.get('phone') or t.get('contact:phone') or '', 'calle': ' '.join(x for x in [t.get('addr:street', ''), t.get('addr:housenumber', '')] if x)})
out.sort(key=lambda x: x['nombre'].lower())
os.makedirs('salida', exist_ok=True); json.dump(out, open('salida/discotecas_bcn.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open('salida/sondeo.txt', 'w').write(f"total {len(out)} con email {sum(1 for x in out if x['email'])} con web {sum(1 for x in out if x['web'])}\n")
