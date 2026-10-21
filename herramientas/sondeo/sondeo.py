"""Sondeo: probar agendas abiertas nuevas (solo cabeceras, recuentos y primeras filas)."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)', 'Accept': '*/*'}
URLS = {
 'malaga_csv': 'https://datosabiertos.malaga.eu/recursos/cultura/agenda/2026.csv',
 'zgz_list': 'https://www.zaragoza.es/sede/servicio/cultura/evento/list.json?rows=3',
 'zgz_upcoming': 'https://www.zaragoza.es/sede/servicio/cultura/evento/upcoming.json?rows=3',
 'zgz_evento': 'https://www.zaragoza.es/sede/servicio/cultura/evento.json?rows=3',
 'vlc_ods': 'https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets?where=search(%22agenda%22)&limit=20',
 'datosgob_agenda': 'https://datos.gob.es/apidata/catalog/dataset/title/agenda.json?_pageSize=100',
 'datosgob_eventos': 'https://datos.gob.es/apidata/catalog/dataset/title/eventos.json?_pageSize=100',
 'datosgob_actividades': 'https://datos.gob.es/apidata/catalog/dataset/title/actividades.json?_pageSize=100',
}
res = {}
for k, u in URLS.items():
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            b = r.read(); res[k] = {'status': r.status, 'tipo': r.headers.get('content-type'), 'bytes': len(b)}
            txt = b.decode('utf-8', 'replace')
            if k.startswith('datosgob'):
                j = json.loads(txt); items = j.get('result', {}).get('items', [])
                res[k]['titulos'] = [((i.get('title') or [{}])[0].get('_value') if isinstance(i.get('title'), list) else i.get('title'), i.get('_about')) for i in items][:100]
            else:
                res[k]['inicio'] = txt[:2500]
    except Exception as e:
        res[k] = {'error': str(e)[:300]}
json.dump(res, open('salida/agendas.json', 'w'), ensure_ascii=False, indent=1)
