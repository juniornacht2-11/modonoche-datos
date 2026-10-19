"""Sondeo (solo recuentos): estructura de OpenRTA (Andalucía) en JSON. Escribe salida/sondeo.txt."""
import json, os, urllib.request
from collections import Counter
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
try:
    b = urllib.request.urlopen(urllib.request.Request('https://datos.juntadeandalucia.es/api/v0/openrta/all?format=json', headers=UA), timeout=300).read()
    j = json.loads(b); p('tipo raíz', type(j).__name__, list(j)[:10] if isinstance(j, dict) else len(j))
    rows = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
    p('filas', len(rows))
    for k in ['group', 'group_id', 'object_type_id', 'objects_type_id', 'srid', 'provinces', 'province_id', 'modalities', 'categories', 'state_present_rtadseg', 'rental_type_ind', 'shared_ind', 'private_use_ind', 'ind_pub_open_rta', 'online_ind']:
        p(k, Counter(str(r.get(k)) for r in rows).most_common(30))
    p('municipalities tipo', Counter(type(r.get('municipalities')).__name__ for r in rows).most_common(3), 'ejemplo', str(rows[0].get('municipalities'))[:200])
    p('municipality_id ejemplo', [r.get('municipality_id') for r in rows[:5]])
    p('coord ejemplo', [(r.get('coord_x'), r.get('coord_y'), r.get('srid')) for r in rows[:8]])
    p('con nombre', sum(1 for r in rows if (r.get('name') or '').strip()), 'con url', sum(1 for r in rows if (r.get('url') or '').strip()))
    p('claves', sorted(rows[0].keys()))
except Exception as e: p('ERROR', repr(e)[:300])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
