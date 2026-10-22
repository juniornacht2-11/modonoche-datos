"""Sondeo: comprobar lo publicado en GitHub Pages (destacadas y agenda)."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
B = 'https://juniornacht2-11.github.io/modonoche-datos'
def get(p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(B + p + '?x=' + str(os.getpid()), headers={'User-Agent': 'MODO-NOCHE-sondeo'}), timeout=60).read())
    except Exception as e: return {'error': str(e)[:200]}
ix = get('/indice.json'); d = get('/destacados.json'); ev = get('/eventos/indice.json')
out = {'indice': {k: ix.get(k) for k in ('gen', 'destacados')}, 'sin_ubicar': d.get('sin_ubicar'), 'anadidos': d.get('anadidos'),
       'agenda': {'gen': ev.get('gen'), 'fuentes': ev.get('fuentes'), 'vigo': (ev.get('municipios') or {}).get('36057'), 'n_munis': len(ev.get('municipios') or {})}}
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
