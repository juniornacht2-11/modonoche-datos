"""Prueba (solo lectura): fuentes oficiales de alojamientos y restauración y servicios para situarlos.
Escribe publico/vut_prueba.txt (solo recuentos, columnas y enlaces; ningún dato de los registros)."""
import csv, io, json, re, time, urllib.parse, urllib.request, zipfile, os
from collections import Counter
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
def get(url, t=120):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t); return r.status, r.headers.get('content-type', ''), r.read()
def tabla(nombre, url):
    p('\n##', nombre, url)
    try:
        st, ct, b = get(url)
        txt = None
        for e in ('utf-8-sig', 'cp1252', 'latin-1'):
            try: txt = b.decode(e); break
            except UnicodeDecodeError: pass
        if txt.lstrip()[:1] in '[{':
            j = json.loads(txt); rows = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [])
            p('JSON filas', len(rows)); 
            if rows and isinstance(rows[0], dict): p('columnas', list(rows[0])); cols = list(rows[0]); data = [[str(r.get(c, '')) for c in cols] for r in rows]
            else: return
        else:
            d = max([';', ',', '\t', '|'], key=txt[:5000].count); rr = list(csv.reader(io.StringIO(txt), delimiter=d)); cols = rr[0]; data = rr[1:]
            p('CSV filas', len(data)); p('columnas', cols)
        for i, c in enumerate(cols):
            if re.search(r'tipo|modalidad|grupo|clase|categor|actividad|subtipo|tipolog', c, re.I): p('  ', c, Counter(r[i] for r in data if i < len(r)).most_common(25))
            if re.search(r'lat|lon|coord|utm|^x$|^y$|gps|catastr', c, re.I): p('  con', c, sum(1 for r in data if i < len(r) and r[i].strip()))
    except Exception as e: p('ERROR', repr(e)[:200])
tabla('Andalucía OpenRTA', 'https://datos.juntadeandalucia.es/api/v0/openrta/all?format=csv')
p('\n## Catálogo datos.gob.es')
vistos = set()
for kw in ['restaurantes', 'bares', 'cafeterias', 'establecimientos de restauracion', 'alojamientos', 'establecimientos turisticos', 'casas rurales', 'campings', 'apartamentos turisticos', 'hoteles', 'viviendas uso turistico', 'registro turismo', 'albergues', 'hostales', 'ocio nocturno', 'discotecas']:
    try:
        st, ct, b = get('https://datos.gob.es/apidata/catalog/dataset/title/' + urllib.parse.quote(kw) + '?_pageSize=50', 60)
        for it in json.loads(b).get('result', {}).get('items', []):
            idd = it.get('_about')
            if idd in vistos: continue
            vistos.add(idd)
            tit = it.get('title'); tit = tit if isinstance(tit, str) else next((x.get('_value') for x in (tit or []) if isinstance(x, dict) and x.get('_lang') == 'es'), str(tit)[:100])
            dist = it.get('distribution') or []; dist = dist if isinstance(dist, list) else [dist]
            urls = [d.get('accessURL') for d in dist if isinstance(d, dict) and re.search(r'csv|json', str(d.get('format')), re.I)][:2]
            p('*', kw, '|', (tit or '')[:110], '|', str(it.get('publisher', ''))[-12:], '|', ' '.join(str(u) for u in urls))
    except Exception as e: p('ERROR catálogo', kw, repr(e)[:150])
p('\n## Catastro INSPIRE parcelas')
try:
    st, ct, b = get('https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml')
    feeds = re.findall(r'<link[^>]+href="([^"]+\.atom\.xml)"', b.decode('utf-8', 'replace')); p('feeds provincia', len(feeds), feeds[:3])
    f08 = next((f for f in feeds if '.08.' in f or '/08/' in f), feeds[0])
    st, ct, b = get(f08); zips = re.findall(r'href="([^"]+\.zip)"', b.decode('utf-8', 'replace')); p('zips en', f08, len(zips), zips[:2])
    z = next((u for u in zips if '08019' in u), zips[0]); t0 = time.time(); st, ct, b = get(z, 300); p('descarga', z, len(b), 'bytes', round(time.time() - t0, 1), 's')
    zf = zipfile.ZipFile(io.BytesIO(b)); p('archivos', zf.namelist())
    g = zf.read(next(n for n in zf.namelist() if n.endswith('cadastralparcel.gml'))).decode('utf-8', 'replace')
    refs = re.findall(r'<cp:nationalCadastralReference>([^<]+)<', g); pts = re.findall(r'<cp:referencePoint>\s*<gml:Point[^>]*srsName="([^"]+)"[^>]*>\s*<gml:pos>([^<]+)<', g)
    p('parcelas', len(refs), 'puntos', len(pts), pts[:2], refs[:2])
except Exception as e: p('ERROR catastro', repr(e)[:300])
p('\n## CartoCiudad geocodificador')
for q in ['Calle Mayor 10, Madrid', 'CALLE FUENCARRAL 45 MADRID 28004']:
    try:
        st, ct, b = get('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(q), 30); p(q, '→', b[:300])
    except Exception as e: p('ERROR cartociudad', repr(e)[:200])
os.makedirs('publico', exist_ok=True); open('publico/vut_prueba.txt', 'w', encoding='utf-8').write('\n'.join(L))
