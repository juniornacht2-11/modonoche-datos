"""Sondeo: buscar agendas en portales de datos abiertos (Tenerife, Canarias, Gran Canaria, València, Baleares, Sevilla). Solo lectura."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
    except Exception as e: return {'error': str(e)[:150]}
out = {}
CKAN = {'tenerife': 'https://datos.tenerife.es/ckan', 'canarias': 'https://datos.canarias.es/catalogos/general', 'grancanaria': 'https://datos.grancanaria.com',
        'sevilla': 'https://www.sevilla.org/ayuntamiento/transparencia/datos-abiertos', 'sevilla2': 'https://sevilla-idesevilla.opendata.arcgis.com',
        'lpgc': 'https://www.laspalmasgc.es/opendata', 'palma': 'https://opendata.palma.cat', 'santacruz': 'https://www.santacruzdetenerife.es/opendata'}
for k, b in CKAN.items():
    for q in ['agenda', 'eventos']:
        j = get(b + '/api/3/action/package_search?rows=10&q=' + q)
        if 'error' in j and k + '_' + q not in out: out[k + '_' + q] = j; continue
        res = (j.get('result') or {}).get('results') or []
        out[k + '_' + q] = [{'t': r.get('title'), 'mod': r.get('metadata_modified'), 'res': [[x.get('format'), x.get('url'), x.get('last_modified')] for x in (r.get('resources') or [])][:5]} for r in res]
# València (Opendatasoft)
out['valencia'] = get('https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets?limit=20&where=' + urllib.parse.quote('search("agenda") OR search("eventos") OR search("activitats")'))
out['valencia2'] = get('https://opendata.vlci.valencia.es/api/3/action/package_search?rows=15&q=agenda')
# Baleares (Socrata)
out['caib'] = get('https://catalegdades.caib.cat/api/catalog/v1?q=agenda&limit=10')
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
