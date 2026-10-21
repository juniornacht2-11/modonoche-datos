"""Sondeo: ejecutar la agenda completa y guardar el índice y muestras (para comprobar las fuentes nuevas)."""
import os, subprocess, shutil, json, urllib.request
os.makedirs('salida', exist_ok=True)
r = subprocess.run(['python3', 'herramientas/eventos.py'], capture_output=True, text=True, timeout=1500, env={**os.environ})
open('salida/sondeo.txt', 'w').write(r.stdout[-6000:] + '\n---\n' + r.stderr[-4000:])
ix = json.load(open('publico/eventos/indice.json'))
json.dump({'fuentes': ix['fuentes'], 'n_municipios': len(ix['municipios']), 'algunos': {k: ix['municipios'].get(k) for k in ['29067', '50297', '28079', '08019', '48020']}}, open('salida/indice.json', 'w'), ensure_ascii=False, indent=1)
for c in ['29067', '50297']:
    if os.path.exists(f'publico/eventos/{c}.json'):
        e = json.load(open(f'publico/eventos/{c}.json'))['eventos']
        json.dump({'total': len(e), 'musica': sum(1 for x in e if x.get('mus')), 'con_coordenadas': sum(1 for x in e if 'lat' in x), 'ej': [x for x in e if x.get('mus')][:6] + e[:3]}, open(f'salida/ej_{c}.json', 'w'), ensure_ascii=False, indent=1)
# agendas regionales candidatas: ficha en datos.gob.es (para ver los enlaces de descarga)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0', 'Accept': 'application/json'}
out = {}
for k, u in {'ivc': 'https://datos.gob.es/apidata/catalog/dataset/a10002983-agenda-cultural-del-institut-valencia-de-cultura-ivc.json',
             'clm': 'https://datos.gob.es/apidata/catalog/dataset/a08002880-agenda-cultural-de-castilla-la-mancha.json',
             'clm_tur': 'https://datos.gob.es/apidata/catalog/dataset/a08002880-agenda-de-turismo-de-castilla-la-mancha.json'}.items():
    try:
        j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
        it = (j.get('result', {}).get('items') or [{}])[0]
        dist = it.get('distribution') or []
        if isinstance(dist, dict): dist = [dist]
        out[k] = [{'url': d.get('accessURL'), 'fmt': (d.get('format') or {}).get('value') if isinstance(d.get('format'), dict) else d.get('format')} for d in dist]
        for d in out[k][:3]:
            try:
                b = urllib.request.urlopen(urllib.request.Request(d['url'], headers={'User-Agent': 'MODO-NOCHE-datos/1.0'}), timeout=60).read()
                d['inicio'] = b[:1500].decode('utf-8', 'replace'); d['bytes'] = len(b)
            except Exception as e:
                d['error'] = str(e)[:200]
    except Exception as e:
        out[k] = {'error': str(e)[:300]}
json.dump(out, open('salida/regionales.json', 'w'), ensure_ascii=False, indent=1)
