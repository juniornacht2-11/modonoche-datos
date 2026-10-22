"""Sondeo: ubicar Exito Gay Club (antes Babylon) y Avyca Ibiza (antes Octan). Solo lectura."""
import os, json, time, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    except Exception as e: return {'error': str(e)[:150]}
out = {}
for q in ['Exito Gay Club', 'Exito, Adeje', 'Exito, Arona', 'Centro Comercial Verónicas', 'Verónicas, Adeje', 'Avyca Ibiza']:
    r = get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'countrycodes': 'es', 'limit': 5, 'addressdetails': 1}))
    out['N ' + q] = [[x.get('name'), x.get('category'), x.get('type'), x.get('lat'), x.get('lon'), x.get('osm_type'), x.get('osm_id'), (x.get('address') or {}).get('town') or (x.get('address') or {}).get('village') or (x.get('address') or {}).get('city'), x.get('display_name', '')[:110]] for x in r] if isinstance(r, list) else r
    time.sleep(1.2)
for q in ['Avenida Rafael Puig Lluvina 5, Adeje', 'Avenida Rafael Puig Lluvina 5, Arona', 'Rafael Puig Lluvina 5, Adeje', 'Carrer de les Alzines 5, Sant Josep de sa Talaia']:
    r = get('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(q))
    out['C ' + q] = {k: r.get(k) for k in ('type', 'address', 'portalNumber', 'muniCode', 'muni', 'geom', 'error')} if isinstance(r, dict) else r
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
