"""Sondeo: tipos de OpenRTA y prueba de búsqueda por tipo y provincia."""
import json, os, urllib.request, urllib.parse
from collections import Counter
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
B = 'https://datos.juntadeandalucia.es/api/v0/openrta/'
def g(u, t=300): return urllib.request.urlopen(urllib.request.Request(B + u, headers=UA), timeout=t).read()
for u in ['option-values/objects_type_id', 'option-values/objects_type', 'option-values/provinces', 'option-values/groups', 'count']:
    try: p(u, g(u, 60)[:1500])
    except Exception as e: p('ERROR', u, repr(e)[:150])
for q in ['search?object_type_id=46&province=CÁDIZ&format=json', 'search?object_type_id=46&province=MÁLAGA&format=json', 'search?object_type_id=1&format=json']:
    try:
        b = g(urllib.parse.quote(q, safe='?=&')); j = json.loads(b); rows = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
        p(q, 'bytes', len(b), 'tipo', type(j).__name__, (list(j)[:8] if isinstance(j, dict) else ''), 'filas', len(rows))
        if rows: p('  claves', sorted(rows[0].keys())); p('  srid', Counter(str(r.get('srid')) for r in rows).most_common(3), 'coord', sum(1 for r in rows if r.get('coord_x')))
    except Exception as e: p('ERROR', q, repr(e)[:200])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
