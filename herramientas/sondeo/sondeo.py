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
    bajar('https://datos.juntadeandalucia.es/api/v0/openrta/all?format=csv', 'rta.csv'); p('bytes', os.path.getsize('rta.csv'))
    raw = open('rta.csv', 'rb').read(); txt = raw.decode('utf-8-sig', 'replace'); p('primeros 300', repr(txt[:300]))
    for d in ['|']:
        rr = list(csv.reader(io.StringIO(txt), delimiter=d)); p('delim', repr(d), 'filas', len(rr) - 1, 'longitudes', Counter(len(r) for r in rr[1:]).most_common(5), 'cab', len(rr[0]))
    rr = list(csv.reader(io.StringIO(txt), delimiter='|'))
    cabs = [(i, len(r)) for i, r in enumerate(rr) if 'coord_x' in r]; p('filas cabecera', cabs[:10])
    for i, n in cabs[:4]: p('cabecera', i, n, rr[i])
    for n in (92,):
        ej = next((r for r in rr if len(r) == n), None); p('ejemplo de longitud', n, 'nº campos no vacíos', sum(1 for x in ej if x.strip()) if ej else None)
    cab = rr[0]; buenas = [dict(zip(cab, r)) for r in rr[1:] if len(r) == len(cab)]; p('filas con longitud correcta', len(buenas))
    for k in ['group', 'group_id', 'object_type_id', 'objects_type_id', 'srid', 'provinces', 'province_id', 'modalities', 'categories', 'state_present_rtadseg', 'rental_type_ind', 'shared_ind', 'private_use_ind', 'ind_pub_open_rta', 'online_ind', 'municipality_id']:
        p(k, Counter(r.get(k) for r in buenas).most_common(25))
    p('municipalities', Counter(r.get('municipalities') for r in buenas).most_common(12))
    p('coord ejemplo', [(r.get('coord_x'), r.get('coord_y'), r.get('srid')) for r in buenas[:10]])
    p('con nombre', sum(1 for r in buenas if r.get('name', '').strip()), 'con url', sum(1 for r in buenas if r.get('url', '').strip()), 'con coord', sum(1 for r in buenas if r.get('coord_x', '').strip()))
except Exception as e: p('ERROR', repr(e)[:300])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
