#!/usr/bin/env python3
"""Comprobación real de servicios externos que usa la web (no publica datos de locales).
Escribe publico/diagnostico.json. Nunca hace fallar el proceso."""
import json, os, urllib.request, datetime as dt
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TOKEN = 'MLY|29090041194015397|038d4d876aec6328a86caab4503a3753'  # token público de cliente (solo lectura de fotos)
SITIOS = {'Puerta del Sol (Madrid)': (40.4169, -3.7035), 'Razzmatazz (Barcelona)': (41.3977, 2.1913), 'Alameda de Hércules (Sevilla)': (37.4007, -5.9946)}
res = {'comprobado': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'mapillary': {}, 'wikidata': None}
for nombre, (lat, lng) in SITIOS.items():
    bbox = f'{lng-0.0016},{lat-0.0012},{lng+0.0016},{lat+0.0012}'
    url = f'https://graph.mapillary.com/images?access_token={urllib.request.quote(TOKEN, safe="")}&fields=id,thumb_1024_url,thumb_256_url,captured_at,compass_angle,computed_geometry&bbox={bbox}&limit=20'
    try:
        req = urllib.request.Request(url, headers={'Origin': 'https://modonoche.juniornacht2.workers.dev', 'User-Agent': 'MODO-NOCHE-diagnostico/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read()); cors = r.headers.get('Access-Control-Allow-Origin')
        imgs = d.get('data') or []
        res['mapillary'][nombre] = {'ok': True, 'imagenes': len(imgs), 'cors': cors,
                                    'ejemplo': {k: imgs[0].get(k) for k in ('id', 'captured_at', 'compass_angle')} if imgs else None,
                                    'tiene_miniatura': bool(imgs and imgs[0].get('thumb_256_url'))}
    except Exception as ex:
        res['mapillary'][nombre] = {'ok': False, 'error': str(ex)[:300]}
try:
    req = urllib.request.Request('https://www.wikidata.org/wiki/Special:EntityData/Q2807.json', headers={'Origin': 'https://modonoche.juniornacht2.workers.dev', 'User-Agent': 'MODO-NOCHE-diagnostico/1.0 (https://github.com/juniornacht2-11/modonoche-datos)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read()); cors = r.headers.get('Access-Control-Allow-Origin')
    ent = next(iter(d['entities'].values()))
    p18 = ent.get('claims', {}).get('P18', [{}])[0].get('mainsnak', {}).get('datavalue', {}).get('value')
    res['wikidata'] = {'ok': True, 'cors': cors, 'P18': p18}
except Exception as ex:
    res['wikidata'] = {'ok': False, 'error': str(ex)[:300]}
os.makedirs(os.path.join(RAIZ, 'publico'), exist_ok=True)
json.dump(res, open(os.path.join(RAIZ, 'publico', 'diagnostico.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
