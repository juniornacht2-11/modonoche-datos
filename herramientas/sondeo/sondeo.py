"""Sondeo: comprobar lo publicado en GitHub Pages (destacadas, pueblos y barrios, redes)."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
B = 'https://juniornacht2-11.github.io/modonoche-datos'
def get(p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(B + p, headers={'User-Agent': 'MODO-NOCHE-sondeo'}), timeout=60).read())
    except Exception as e: return {'error': str(e)[:200]}
ix = get('/indice.json'); d = get('/destacados.json'); l = get('/lugares.json'); r = get('/redes/piezas.json')
out = {'indice': {k: ix.get(k) for k in ('gen', 'datos', 'total', 'municipios_con_datos', 'destacados', 'estadisticas')},
       'destacados': {k: (len(v) if isinstance(v, list) else v) for k, v in d.items()}, 'sin_ubicar': d.get('sin_ubicar'), 'anadidos': d.get('anadidos'),
       'encontrados': d.get('encontrados'),
       'lugares': {'n': len(l.get('l') or []), 'ej': [x for x in (l.get('l') or []) if x[0] in ('Magaluf', 'Puerto Banús', "Platja d'en Bossa", 'Playa de las Américas', 'Malasaña', 'Chueca', 'Maspalomas', 'Playa del Inglés', 'Gràcia', 'Ruzafa', 'Russafa', 'Triana')], 'error': l.get('error')},
       'redes': {'n': len(r.get('piezas') or []), 'titulos': [p['titulo'] for p in r.get('piezas') or []], 'error': r.get('error')}}
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
