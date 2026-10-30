import json, os, urllib.request
B = 'https://juniornacht2-11.github.io/modonoche-datos/'
def j(p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(B + p, headers={'User-Agent': 'mn-sondeo'}), timeout=60).read())
    except Exception as e: return {'error': str(e)}
out = {}
ii = j('indice-int.json'); out['indice_int'] = {'error': ii.get('error'), 'ciudades': len(ii.get('municipios', {})), 'paises': list((ii.get('paises') or {}).keys())}
l = j('locales/GB2643743.json'); out['londres'] = {'n': len(l.get('elements', [])), 'error': l.get('error')}
lg = j('lugares-int.json'); out['barrios_int'] = len(lg.get('l', [])) if isinstance(lg, dict) else lg
ev = j('eventos/indice.json'); out['fuentes'] = ev.get('fuentes'); m = ev.get('municipios', {})
out['eventos_int'] = {k: v for k, v in sorted(m.items(), key=lambda x: -x[1]) if k[:2].isalpha()}
out['eventos_int'] = dict(list(out['eventos_int'].items())[:15]); out['n_ciudades_int_con_eventos'] = sum(1 for k in m if k[:2].isalpha())
os.makedirs('salida', exist_ok=True); json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
