import json, os, urllib.request, datetime
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
L = []
def p(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)
hoy = datetime.date.today().isoformat()
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read())
r = get(f"https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json?$limit=3&$where=data_fi%20%3E=%20'{hoy}T00:00:00'%20AND%20permanent='No'")
for x in r: p('CAT', json.dumps({k: (v[:120] if isinstance(v, str) else v) for k, v in x.items() if k != 'descripcio'}, ensure_ascii=False))
c = get(f"https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json?$select=count(*)&$where=data_fi%20%3E=%20'{hoy}T00:00:00'%20AND%20permanent='No'"); p('CAT próximos', c)
y = get('https://datosabiertos.jcyl.es/web/jcyl/risp/es/cultura-ocio/agenda_cultural/1284806871500.json')
p('CYL claves', list(y[0].keys())); p('CYL ej', json.dumps({k: (v[:100] if isinstance(v, str) else v) for k, v in y[5].items() if k != 'descripcion'}, ensure_ascii=False))
p('CYL futuros', sum(1 for e in y if (e.get('fecha_fin') or e.get('fecha_inicio') or '') >= hoy))
a = get('https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json')
fut = [e for e in a if any((d.get('end_date_registration') or '') >= hoy for d in (e.get('date_registration') or []))]
p('AND futuros', len(fut), 'de', len(a))
os.makedirs('salida', exist_ok=True); open('salida/sondeo.txt', 'w', encoding='utf-8').write('\n'.join(L))
