"""Sondeo: deducir la cabecera de las filas largas del CSV de OpenRTA."""
import csv, io, json, os, re, urllib.request
from collections import Counter
csv.field_size_limit(10**8)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
B = 'https://datos.juntadeandalucia.es/api/v0/openrta/'
def bajar(url, ruta):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(ruta, 'wb') as f:
                while True:
                    c = r.read(1 << 20)
                    if not c: break
                    f.write(c)
            return
        except Exception as e: p('reintento', repr(e)[:100])
spec = json.loads(urllib.request.urlopen(urllib.request.Request(B + 'openapi.json', headers=UA), timeout=60).read())
campos = spec['components']['schemas']['_Enum_fields']['enum']; p('campos en la API', len(campos)); p(sorted(campos))
bajar(B + 'all?format=csv', 'rta.csv')
rr = list(csv.reader(io.StringIO(open('rta.csv', encoding='utf-8-sig', errors='replace').read()), delimiter='|'))
cab = rr[0]; largas = [r for r in rr[1:] if len(r) == 92]
p('largas', len(largas))
# qué columnas parecen coordenadas UTM (6-7 cifras con decimales)
for i in range(92):
    vals = [r[i] for r in largas[:3000] if r[i].strip()]
    num = sum(1 for v in vals if re.fullmatch(r'\d{6,7}(\.\d+)?', v))
    ej = Counter(v[:30] for v in vals).most_common(3)
    p(i, 'llenos', len(vals), 'utm', num, ej)
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
