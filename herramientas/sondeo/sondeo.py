"""Sondeo: referencias catastrales de Cataluña y coordenadas raras de Canarias (solo recuentos y formatos)."""
import csv, io, os, re, urllib.request
from collections import Counter
csv.field_size_limit(10**9)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=600).read()
def forma(v): return re.sub(r'[A-Za-z]', 'A', re.sub(r'\d', '9', v))
try:
    t = get('https://analisi.transparenciacatalunya.cat/resource/t2h3-cgys.csv?$limit=1000000').decode('utf-8-sig')
    rr = list(csv.reader(io.StringIO(t))); h = rr[0]; i = h.index('referencia_cadastral'); te = h.index('tipus_establiment')
    p('Cataluña filas', len(rr) - 1)
    p('longitudes ref', Counter(len(re.sub(r'\s', '', r[i])) for r in rr[1:]).most_common(10))
    p('formas ref', Counter(forma(r[i])[:24] for r in rr[1:]).most_common(10))
    p('por tipo con ref>=14', Counter(r[te] for r in rr[1:] if len(re.sub(r'\s', '', r[i])) >= 14).most_common(8))
except Exception as e: p('ERROR cat', repr(e)[:200])
try:
    t = get('https://datos.canarias.es/catalogos/general/dataset/9f4355a2-d086-4384-ba72-d8c99aa2d544/resource/8ff8cc43-c00b-4513-8f42-a5b961c579e1/download/establecimientos-extrahoteleros-de-tipologia-vivienda-vacacional-inscritos-en-el-registro-genera.csv').decode('utf-8-sig')
    d = max([';', ','], key=t[:3000].count); rr = list(csv.reader(io.StringIO(t), delimiter=d)); h = rr[0]
    la, lo = h.index('latitud'), h.index('longitud')
    p('Canarias formas lat', Counter(forma(r[la]) for r in rr[1:]).most_common(8))
    p('Canarias formas lon', Counter(forma(r[lo]) for r in rr[1:]).most_common(8))
    p('ejemplos', [(r[la], r[lo]) for r in rr[1:] if not re.fullmatch(r'-?\d+\.\d+', r[la].strip())][:8])
except Exception as e: p('ERROR can', repr(e)[:200])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
