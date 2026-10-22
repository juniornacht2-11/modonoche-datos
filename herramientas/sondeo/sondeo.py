"""Sondeo: diagnóstico de geocodificación de destacadas sin ubicar (solo lectura)."""
import os, json, time, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    except Exception as e: return {'error': str(e)[:200]}
NOM = ['Mare Nostrum Resort, Adeje', 'Marmarela', 'Dique de Levante, Alicante', 'Muelle de Honor, Marbella', 'Club de Mar, Marbella',
 'Pueblo Canario, Las Palmas de Gran Canaria', 'Paseo Alonso Quesada, Las Palmas de Gran Canaria', 'Carrer de Carles Buïgas 6, Salou', 'Carrer de Carles Buïgas 60, Salou',
 'Passatge de Domingo 3, Barcelona', 'Calle José Luis Pérez Pujadas, Granada', 'Centro Comercial Cita, Playa del Inglés', 'Centro Comercial Kasbah', 'Veronicas, Arona', 'Centro Comercial Starco, Arona']
CC = ['Carles Buigas 6, 43840 Salou', 'Carles Buigas 60, 43840 Salou', 'Passatge de Domingo 3, 08007 Barcelona', 'Domingo 3, Barcelona', 'Passatge Domingo 3, 08007 Barcelona']
out = {'nominatim': {}, 'cartociudad': {}}
for q in NOM:
    r = get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'countrycodes': 'es', 'limit': 5}))
    out['nominatim'][q] = [[x.get('name'), x.get('category'), x.get('type'), x.get('lat'), x.get('lon'), x.get('osm_type'), x.get('osm_id'), x.get('display_name', '')[:90]] for x in r] if isinstance(r, list) else r
    time.sleep(1.2)
for q in CC:
    r = get('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(q))
    out['cartociudad'][q] = {k: r.get(k) for k in ('type', 'address', 'portalNumber', 'muniCode', 'muni', 'geom', 'error', 'stateMsg')} if isinstance(r, dict) else r
    c = get('https://www.cartociudad.es/geocoder/api/geocoder/candidatesJsonp?limit=3&q=' + urllib.parse.quote(q))
    out['cartociudad'][q + ' [cand]'] = c if not isinstance(c, list) else [{k: x.get(k) for k in ('type', 'address', 'portalNumber', 'muniCode', 'muni')} for x in c]
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
