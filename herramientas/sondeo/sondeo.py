"""Sondeo: buscar una foto libre de una habitación (Wikimedia Commons) para el plan «Habitaciones». Solo lectura."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
out = []
for q in ['hostel private room bed', 'guest house bedroom Spain', 'pension room bed Spain', 'hotel room cozy bed lamp']:
    j = get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': 'filetype:bitmap ' + q, 'gsrnamespace': 6, 'gsrlimit': 12,
        'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size', 'iiurlwidth': 800}))
    for p in (j.get('query') or {}).get('pages', {}).values():
        ii = (p.get('imageinfo') or [{}])[0]; m = ii.get('extmetadata') or {}
        lic = (m.get('LicenseShortName') or {}).get('value', '')
        if not any(x in lic for x in ('CC0', 'Public domain', 'CC BY 4.0', 'CC BY-SA 4.0', 'CC BY 3.0', 'CC BY-SA 3.0')): continue
        out.append({'t': p.get('title'), 'lic': lic, 'autor': (m.get('Artist') or {}).get('value', '')[:120], 'thumb': ii.get('thumburl'), 'w': ii.get('width'), 'h': ii.get('height'), 'q': q})
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
