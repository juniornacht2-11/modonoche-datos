"""Sondeo: Barcelona (Open Data BCN) y Gijón: por qué fallan (solo lectura)."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-agenda/1.0 (https://github.com/juniornacht2-11/modonoche-datos; actualizacion diaria)'}
def raw(u, n=3000):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90); b = r.read()
        return {'st': r.status, 'ct': r.headers.get('Content-Type'), 'len': len(b), 'ini': b[:n].decode('utf-8', 'replace')}
    except Exception as e: return {'err': str(e)[:200]}
O = 'https://opendata-ajuntament.barcelona.cat'
out = {
 'pkg': raw(O + '/data/api/3/action/package_show?id=agenda-diaria', 6000),
 'pkg2': raw(O + '/data/api/action/package_search?q=agenda&rows=5', 4000),
 'ds': raw(O + '/data/api/action/datastore_search?resource_id=877ccf66-9106-4ae2-be51-95a9f6469e4c&limit=2', 4000),
 'dl': raw(O + '/data/dataset/a25e60cd-3083-4252-9fce-81f733871cb1/resource/877ccf66-9106-4ae2-be51-95a9f6469e4c/download', 600),
}
try:
    g = json.loads(urllib.request.urlopen(urllib.request.Request('https://opendata.gijon.es/descargar.php?id=728&tipo=JSON', headers=UA), timeout=120).read().decode('utf-8-sig'))
    out['gijon_n'] = len(g); out['gijon_ej'] = g[:3]; out['gijon_claves'] = sorted(g[0].keys()) if g else None
    out['gijon_fechas'] = sorted(set(str(r.get('fechas') or r.get('fecha_inicio'))[:25] for r in g))[-8:]
except Exception as e: out['gijon_err'] = str(e)[:200]
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
