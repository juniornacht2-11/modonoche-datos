"""Sondeo: probar agendas candidatas (solo lectura): tamaño, columnas, ejemplo y fechas."""
import os, json, re, csv, io, urllib.request
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def raw(u, n=30_000_000):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120)
        return r.read(n), r.headers.get('Content-Type')
    except Exception as e: return ('ERROR ' + str(e)[:200]).encode(), None
U = {
 'andalucia_json': 'https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json',
 'andalucia_csv': 'https://datos.juntadeandalucia.es/api/v0/schedule/all?format=csv',
 'canarias_proxima': 'https://datos.canarias.es/catalogos/general/dataset/11dc9d88-b456-4ae2-bcf9-07ad624fd025/resource/d179079c-a2ed-40dc-a748-7b64d093c342/download/agendaproxima.csv',
 'vigo': 'https://datos.vigo.org/data/axenda/agenda-hoy.json',
 'santacruz': 'https://www.santacruzdetenerife.es/opendata/dataset/f38a3086-8d4c-4c6a-943e-629056b66f01/resource/95a65af3-5f11-4041-a418-45afcc5e7686/download/agendacultural.json',
 'diba_general': 'http://do.diba.cat/api/dataset/agendageneral_ca/format/json',
 'diba_escenari': 'http://do.diba.cat/api/dataset/escenari/pag-ini/1/pag-fi/100/format/json',
 'bizkaikoa_2025': 'https://www.opendatabizkaia.eus/es/datastore/dump/6b76cd72-63b9-4125-93fe-4037921a91c5/agenda-cultural-bizkaikoa-2025?format=json',
 'coruna_ics': 'https://datos.coruna.gal/en/dataset/agenda-de-eventos/resource/234cdaac-0d9b-46b1-9b1c-b853dd3b486e',
}
out = {}
for k, u in U.items():
    b, ct = raw(u)
    info = {'bytes': len(b), 'ct': ct, 'inicio': b[:700].decode('utf-8', 'replace')}
    fechas = re.findall(rb'20\d\d-\d\d-\d\d', b)
    if fechas: f = sorted(set(x.decode() for x in fechas)); info['fechas'] = [f[0], f[-1], len(f), sum(1 for x in f if x >= '2026-10-22')]
    else:
        f2 = re.findall(rb'\b\d\d/\d\d/20\d\d\b', b); info['fechas_dmy'] = sorted(set(x.decode()[-4:] + x.decode()[3:5] + x.decode()[:2] for x in f2))[-3:] if f2 else None
    try:
        j = json.loads(b)
        def forma(o, d=0):
            if d > 3: return '…'
            if isinstance(o, dict): return {kk: forma(v, d + 1) for kk, v in list(o.items())[:25]}
            if isinstance(o, list): return [len(o), forma(o[0], d + 1) if o else None]
            return str(o)[:80]
        info['forma'] = forma(j)
    except Exception: pass
    out[k] = info
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
