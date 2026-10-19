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
import urllib.error
for q in ['search?object_type_id=1&size=50', 'search?object_type=Establecimiento Hotelero&size=50', 'search?object_type_id=1&size=50&format=json', 'search?province=CÁDIZ&object_type_id=46&size=20000&format=csv', 'search?mode=AND&object_type_id=1&size=50']:
    try:
        b = g(urllib.parse.quote(q, safe='?=&')); p('OK', q, len(b), b[:600])
    except urllib.error.HTTPError as e: p('HTTP', e.code, q, e.read()[:700])
    except Exception as e: p('ERROR', q, repr(e)[:200])
try:
    spec = json.loads(g('openapi.json', 60)); sc = spec.get('components', {}).get('schemas', {})
    for k in ['_Enum_Mode', 'OutputFormats', 'DownloadFormats', '_Enum_fields']: p(k, str(sc.get(k))[:600])
except Exception as e: p('ERROR spec', repr(e)[:150])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
