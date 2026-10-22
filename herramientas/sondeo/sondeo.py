"""Sondeo: CartoCiudad para Exito Gay Club (solo lectura)."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
out = {}
for q in ['Avenida Rafael Puig Lluvina 5, Adeje', 'Avenida Rafael Puig Lluvina 5, Arona', 'Rafael Puig Lluvina 5', 'Avenida Rafael Puig Lluvina, Adeje']:
    try: r = json.loads(urllib.request.urlopen(urllib.request.Request('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(q), headers=UA), timeout=60).read())
    except Exception as e: r = {'error': str(e)[:150]}
    out[q] = {k: (str(r.get(k))[:160]) for k in ('type', 'address', 'portalNumber', 'muniCode', 'muni', 'geom', 'error')}
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
