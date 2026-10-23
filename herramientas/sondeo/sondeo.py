"""Sondeo: alojamientos de registros publicados por tipo (solo lectura)."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
B = 'https://juniornacht2-11.github.io/modonoche-datos'
def get(p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(B + p, headers={'User-Agent': 'MODO-NOCHE-sondeo'}), timeout=60).read())
    except Exception as e: return {'error': str(e)[:200]}
ix = get('/registros/indice.json'); bcn = get('/registros/08019.json')
json.dump({'gen': ix.get('gen'), 'por_tipo': ix.get('por_tipo'), 'error': ix.get('error'), 'bcn_hab': [x for x in (bcn.get('items') or []) if x.get('t') == 'habitacion'][:3]}, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
