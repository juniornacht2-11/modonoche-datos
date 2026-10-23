"""Sondeo: tipos de establecimiento del registro de turismo de Cataluña (solo lectura)."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read())
    except Exception as e: return {'error': str(e)[:200]}
B = 'https://analisi.transparenciacatalunya.cat/resource/t2h3-cgys.json?'
out = {'tipos': get(B + urllib.parse.urlencode({'$select': 'tipus_establiment, grup, count(*)', '$group': 'tipus_establiment, grup', '$limit': 100})),
       'ej_llar': get(B + urllib.parse.urlencode({'$where': "lower(tipus_establiment) like '%llar%'", '$limit': 2}))}
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
