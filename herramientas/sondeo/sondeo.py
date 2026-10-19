"""Sondeo (solo recuentos): estructura del CSV de OpenRTA (Andalucía). Escribe salida/sondeo.txt."""
import csv, io, os, sys, urllib.request
from collections import Counter
csv.field_size_limit(10**8)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
def bajar(url, ruta):
    for intento in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(ruta, 'wb') as f:
                while True:
                    c = r.read(1 << 20)
                    if not c: break
                    f.write(c)
            return True
        except Exception as e: p('reintento', intento, repr(e)[:120])
    return False
try:
    b = urllib.request.urlopen(urllib.request.Request('https://datos.juntadeandalucia.es/api/v0/openrta/openapi.json', headers=UA), timeout=60).read()
    import json; spec = json.loads(b)
    for path, ops in spec.get('paths', {}).items():
        for m, op in ops.items():
            p('RUTA', m, path, [(x.get('name'), x.get('in'), str(x.get('schema'))[:80]) for x in op.get('parameters', [])])
except Exception as e: p('ERROR openapi', repr(e)[:200])
try:
    ok = bajar('https://datos.juntadeandalucia.es/api/v0/openrta/all?format=json', 'rta.json'); p('json bajado', ok, os.path.getsize('rta.json'))
    import json; j = json.load(open('rta.json', encoding='utf-8')); rows = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
    p('filas json', len(rows)); p('conjuntos de claves', Counter(len(r) for r in rows).most_common(5))
    ks = Counter(k for r in rows for k in r); p('claves', ks.most_common(120))
    for k in ['objects_type_id', 'group', 'srid', 'provinces']: p(k, Counter(str(r.get(k)) for r in rows).most_common(20))
    p('con coord', sum(1 for r in rows if r.get('coord_x')), 'con nombre', sum(1 for r in rows if (r.get('name') or '').strip()))
except Exception as e: p('ERROR json', repr(e)[:300])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
