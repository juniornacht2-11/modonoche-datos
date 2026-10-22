"""Sondeo: diagnóstico de geocodificación de destacadas sin ubicar (solo lectura)."""
import os, json, time, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    except Exception as e: return {'error': str(e)[:200]}
NOM = [  # nombre / lugar a buscar en Nominatim
 'Hyde Club, Barcelona', 'Marmarela, Alicante', 'Vybe, Eivissa', 'Octan Ibiza', 'Octan, Sant Josep de sa Talaia',
 'Dreamers, Marbella', 'Pangea, Marbella', 'Fitz, Marbella', 'NYX, Marbella', 'Magic, Arona', 'Babylon, Arona',
 'China White, San Bartolomé de Tirajana', 'Centro Comercial Kasbah, San Bartolomé de Tirajana', 'Aqua Ocean Club, San Bartolomé de Tirajana',
 'Centro Comercial Meloneras Playa', 'Mama Juana, Meloneras', 'Dubai, Playa del Inglés', 'El Caserío, Playa del Inglés', 'Centro Comercial Yumbo',
 'Metro Dance Club, Bigastro', 'Metro, Bigastro', 'TAO, Las Palmas de Gran Canaria', 'Forum Plaza, Granada', 'Kitsch, Murcia',
 'Marina Botafoc, Eivissa', 'Puerto Banús', 'Hotel Meliá Lebreros, Sevilla', 'Edificio Forum, Granada']
CC = ['Passatge Domingo 3, Barcelona', 'Pasaje Domingo 3, Barcelona', 'Carrer de Carles Buïgas 6, Salou', 'Carrer de Carles Buïgas 60, Salou',
 'Carrer de Murillo 3, Salou', 'Carrer de Murillo 4, Salou', 'Calle San Carlos 13, Murcia', 'Calle Santa Bárbara 3, Granada',
 'Calle Rosalía de Castro 243, Oleiros', 'Rambla Méndez Núñez 19, Alicante', 'Avenida de Villajoyosa 4, Alicante', 'Carrer de Santa Cristina 14, Lloret de Mar',
 'Avenida de Europa 9, Jerez de la Frontera', 'Calle Luis Montoto 118, Sevilla', 'Avenida de Tenerife, San Bartolomé de Tirajana', 'Carrer Port d\'Eivissa 107, Eivissa']
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
