"""Prueba (solo lectura) de los registros oficiales de viviendas y alojamientos turísticos.
Escribe publico/vut_prueba.json con lo que se ha podido descargar: filas, columnas y si traen coordenadas.
No publica ningún dato de los registros, solo el recuento y los nombres de las columnas."""
import csv, io, json, os, re, sys, time, urllib.parse, urllib.request
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
OUT = {'gen': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'catalogo': [], 'fuentes': []}
def get(url, t=90, maxb=400_000_000):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t)
    return r.status, r.headers.get('content-type', ''), r.read(maxb)
# A) catálogo nacional datos.gob.es
for kw in ['viviendas uso turistico', 'vivienda turistica', 'viviendas turisticas', 'alojamientos turisticos', 'establecimientos turisticos', 'registro turismo', 'apartamentos turisticos', 'habitatges', 'vivienda vacacional', 'alojamiento turistico']:
    try:
        u = 'https://datos.gob.es/apidata/catalog/dataset/title/' + urllib.parse.quote(kw) + '?_pageSize=50'
        st, ct, b = get(u, 60)
        for it in json.loads(b).get('result', {}).get('items', []):
            tit = it.get('title'); tit = tit if isinstance(tit, str) else ' | '.join(x.get('_value', '') for x in (tit or []) if isinstance(x, dict) and x.get('_lang') == 'es') or str(tit)[:120]
            dist = it.get('distribution') or []; dist = dist if isinstance(dist, list) else [dist]
            urls = [(d.get('accessURL'), (d.get('format') or {}).get('value') if isinstance(d.get('format'), dict) else d.get('format')) for d in dist if isinstance(d, dict)]
            OUT['catalogo'].append({'kw': kw, 'titulo': tit[:160], 'publica': str(it.get('publisher'))[-60:], 'id': it.get('_about'), 'urls': urls[:6]})
    except Exception as e:
        OUT['catalogo'].append({'kw': kw, 'error': repr(e)[:200]})
# B) fuentes concretas
COORD = re.compile(r'(lat|lon|lng|coord|utm|x_|y_|^x$|^y$|geo|gps)', re.I)
def analizar(nombre, url, tipo='csv'):
    f = {'nombre': nombre, 'url': url}
    try:
        st, ct, b = get(url); f['http'] = st; f['bytes'] = len(b); f['ct'] = ct
        if tipo == 'json' or 'json' in ct:
            j = json.loads(b); f['json_claves'] = list(j)[:20] if isinstance(j, dict) else None
            if isinstance(j, dict) and 'count' in j: f['count'] = j['count']
            if isinstance(j, dict) and 'layers' in j: f['capas'] = [(l.get('id'), l.get('name')) for l in j['layers']][:30]
            if isinstance(j, dict) and isinstance(j.get('result'), dict) and 'results' in j['result']:
                f['ckan'] = [{'t': p.get('title'), 'res': [(r.get('name'), r.get('format'), r.get('url'), r.get('last_modified')) for r in p.get('resources', [])][:8]} for p in j['result']['results']][:15]
            if isinstance(j, list): f['filas'] = len(j); f['columnas'] = list(j[0])[:60] if j and isinstance(j[0], dict) else None
            return f
        txt = None
        for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
            try: txt = b.decode(enc); f['enc'] = enc; break
            except Exception: pass
        head = txt[:5000]; delim = max([';', ',', '\t', '|'], key=head.count)
        rows = list(csv.reader(io.StringIO(txt), delimiter=delim))
        cols = rows[0] if rows else []; f['columnas'] = cols[:60]; f['filas'] = max(0, len(rows) - 1)
        cc = [i for i, c in enumerate(cols) if COORD.search(c.strip())]
        f['cols_coord'] = [cols[i] for i in cc]
        if cc: f['filas_con_coord'] = sum(1 for r in rows[1:] if all(i < len(r) and r[i].strip() for i in cc))
        wi = [i for i, c in enumerate(cols) if re.search(r'web|url|email|tel', c, re.I)]; f['cols_contacto'] = [cols[i] for i in wi]
        ti = [i for i, c in enumerate(cols) if re.search(r'tipo|modalidad|grupo|clase|categor', c, re.I)]
        if ti:
            from collections import Counter
            f['tipos'] = {cols[i]: Counter(r[i] for r in rows[1:] if i < len(r)).most_common(15) for i in ti[:3]}
    except Exception as e:
        f['error'] = repr(e)[:300]
    return f
FUENTES = [
    ('Cataluña · establecimientos (Socrata)', 'https://analisi.transparenciacatalunya.cat/resource/t2h3-cgys.csv?$limit=500000'),
    ('Cataluña · catálogo HUT', 'https://analisi.transparenciacatalunya.cat/api/catalog/v1?q=habitatges%20us%20turistic&limit=20', 'json'),
    ('C. Valenciana · catálogo', 'https://dadesobertes.gva.es/api/3/action/package_search?q=viviendas%20turisticas&rows=10', 'json'),
    ('C. Valenciana · viviendas ene-2025', 'https://dadesobertes.gva.es/dataset/8a1c4fa3-4696-4b3b-8a1a-6bff038abf0c/resource/2c1e8aa4-5238-47c4-9404-f574ee1269a4/download/listaviviendas_20250126.csv'),
    ('Castilla y León · viviendas uso turístico', 'https://datosabiertos.jcyl.es/web/jcyl/risp/es/turismo/viviendas-uso-turistico/1284748762495.csv'),
    ('Mallorca · IDEIB capas', 'https://ideib.caib.es/geoserveis/rest/services/public/GOIB_EstablimentsTuristicsMallorca/MapServer?f=json', 'json'),
    ('Mallorca · IDEIB capa 0 recuento', 'https://ideib.caib.es/geoserveis/rest/services/public/GOIB_EstablimentsTuristicsMallorca/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json', 'json'),
    ('C. Madrid · catálogo', 'https://datos.comunidad.madrid/catalogo/api/3/action/package_search?q=viviendas%20uso%20turistico&rows=10', 'json'),
    ('Canarias · catálogo', 'https://datos.canarias.es/catalogos/general/api/3/action/package_search?q=vivienda%20vacacional&rows=10', 'json'),
    ('Euskadi · catálogo datos.gob', 'https://datos.gob.es/apidata/catalog/dataset/title/alojamientos?_pageSize=50', 'json'),
    ('Andalucía · catálogo', 'https://www.juntadeandalucia.es/datosabiertos/portal/api/3/action/package_search?q=viviendas%20fines%20turisticos&rows=10', 'json'),
    ('Galicia · catálogo', 'https://abertos.xunta.gal/api/3/action/package_search?q=vivendas%20uso%20turistico&rows=10', 'json'),
    ('Aragón · catálogo', 'https://opendata.aragon.es/ckan/api/3/action/package_search?q=viviendas%20uso%20turistico&rows=10', 'json'),
    ('Asturias · catálogo', 'https://datos.gob.es/apidata/catalog/dataset/title/turismo?_pageSize=50', 'json'),
]
for x in FUENTES: OUT['fuentes'].append(analizar(*x)); print(OUT['fuentes'][-1].get('nombre'), OUT['fuentes'][-1].get('filas'), OUT['fuentes'][-1].get('error', ''), flush=True)
os.makedirs('publico', exist_ok=True)
json.dump(OUT, open('publico/vut_prueba.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
