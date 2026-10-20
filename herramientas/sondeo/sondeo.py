"""Sondeo: estructura de agendas candidatas (columnas y 2 filas)."""
import csv, io, json, os, urllib.request
csv.field_size_limit(10**8)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
F = [('cat', 'https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json?$limit=3&$order=data_inici%20DESC'),
     ('cat_count', 'https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json?$select=count(*)'),
     ('bcn', 'https://opendata-ajuntament.barcelona.cat/data/dataset/2767159c-1c98-46b8-a686-2b25b40cb053/resource/3abb2414-1ee0-446e-9c25-380e938adb73/download'),
     ('cyl', 'https://datosabiertos.jcyl.es/web/jcyl/risp/es/cultura-ocio/agenda_cultural/1284806871500.json'),
     ('can', 'https://datos.canarias.es/catalogos/general/dataset/11dc9d88-b456-4ae2-bcf9-07ad624fd025/resource/d179079c-a2ed-40dc-a748-7b64d093c342/download/agendaproxima.csv'),
     ('and', 'https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json'),
     ('vigo', 'https://datos.vigo.org/data/axenda/agenda-hoy.json'),
     ('gijon', 'https://opendata.gijon.es/descargar.php?id=728&tipo=JSON')]
for n, u in F:
    try:
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        p('\n##', n, len(b), 'bytes', repr(b[:80]))
        t = None
        for e in ('utf-8-sig', 'latin-1'):
            try: t = b.decode(e); break
            except: pass
        if t.lstrip()[:1] in '[{':
            j = json.loads(t); rows = j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), None)
            if rows is None and isinstance(j, dict):
                for v in j.values():
                    if isinstance(v, dict):
                        rows = next((w for w in v.values() if isinstance(w, list)), None)
                        if rows: break
            p('claves raíz', list(j)[:10] if isinstance(j, dict) else 'lista', 'filas', len(rows or []))
            for r in (rows or [])[:2]: p(json.dumps(r, ensure_ascii=False)[:1500])
        else:
            d = max([';', ',', '\t'], key=t[:4000].count); rr = list(csv.DictReader(io.StringIO(t), delimiter=d))
            p('csv filas', len(rr)); 
            for r in rr[:2]: p(json.dumps(r, ensure_ascii=False)[:1500])
    except Exception as e: p('\n##', n, 'ERROR', repr(e)[:200])
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
