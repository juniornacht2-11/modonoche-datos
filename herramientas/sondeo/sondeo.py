"""Sondeo: variantes de la API de Open Data BCN (solo lectura)."""
import os, json, time, urllib.request
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-agenda/1.0 (https://github.com/juniornacht2-11/modonoche-datos; actualizacion diaria)'}
B = 'https://opendata-ajuntament.barcelona.cat/data/api/action/datastore_search?resource_id=877ccf66-9106-4ae2-be51-95a9f6469e4c'
out = {}
for k, q in [('sin_orden_1000', '&limit=1000'), ('orden_fin', '&limit=1000&sort=end_date%20desc'), ('orden_fin2', '&limit=100&sort=end_date+desc'),
             ('filtro_q', '&limit=1000&q=2026'), ('total', '&limit=1')]:
    t = time.time()
    try:
        j = json.loads(urllib.request.urlopen(urllib.request.Request(B + q, headers=UA), timeout=150).read())
        r = j.get('result') or {}; rec = r.get('records') or []
        out[k] = {'s': round(time.time() - t, 1), 'total': r.get('total'), 'n': len(rec), 'fines': [str(x.get('end_date'))[:10] for x in rec[:3]] + [str(x.get('end_date'))[:10] for x in rec[-3:]]}
    except Exception as e: out[k] = {'s': round(time.time() - t, 1), 'err': str(e)[:200]}
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
