"""Sondeo: agendas de eventos abiertas (catálogos)."""
import json, os, urllib.parse, urllib.request
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
def get(u, t=60): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read()
for kw in ['agenda', 'agenda cultural', 'eventos', 'actividades culturales', 'conciertos']:
    for pag in range(0, 3):
        try:
            j = json.loads(get(f'https://datos.gob.es/apidata/catalog/dataset/title/{urllib.parse.quote(kw)}.json?_pageSize=50&_page={pag}'))
            items = j.get('result', {}).get('items', [])
            if not items: break
            for it in items:
                t = it.get('title'); t = t if isinstance(t, str) else next((x.get('_value') for x in (t or []) if isinstance(x, dict) and x.get('_lang') == 'es'), str(t)[:90])
                dist = it.get('distribution') or []; dist = dist if isinstance(dist, list) else [dist]
                us = [d.get('accessURL') for d in dist if isinstance(d, dict) and any(f in str(d.get('format', '')).lower() for f in ('csv', 'json'))][:2]
                mod = str(it.get('modified', ''))[:10]
                p('*', kw, '|', (t or '')[:100], '|', str(it.get('publisher', ''))[-10:], '|', mod, '|', ' '.join(map(str, us)))
        except Exception as e: p('ERR', kw, pag, repr(e)[:120])
for nombre, u in [('Cataluña socrata', 'https://analisi.transparenciacatalunya.cat/api/catalog/v1?q=agenda&limit=30'),
                  ('CyL socrata', 'https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets?where=search(%22agenda%22)&limit=20'),
                  ('Valencia ciudad', 'https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets?where=search(%22agenda%22)&limit=20'),
                  ('Málaga ckan', 'https://datosabiertos.malaga.eu/api/3/action/package_search?q=agenda&rows=10'),
                  ('Zaragoza', 'https://www.zaragoza.es/sede/servicio/cultura/evento/list.json?rows=5')]:
    try:
        b = get(u); j = json.loads(b)
        if 'results' in j and isinstance(j['results'], list):
            for r in j['results'][:30]:
                res = r.get('resource') or r
                p('#', nombre, '|', res.get('name') or res.get('dataset_id') or res.get('title'), '|', res.get('id') or res.get('dataset_id'), '|', str(res.get('updatedAt') or res.get('modified') or '')[:10])
        elif 'result' in j and isinstance(j['result'], dict):
            for r in j['result'].get('results', [])[:10]: p('#', nombre, '|', r.get('title'), '|', [x.get('url') for x in r.get('resources', [])][:3])
        else: p('#', nombre, 'claves', list(j)[:10], str(j)[:400])
    except Exception as e: p('ERR', nombre, repr(e)[:150])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
