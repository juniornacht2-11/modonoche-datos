"""MODO NOCHE · discotecas destacadas (datos/destacados.json) dentro de los datos de locales.

Para cada local de la lista (todos con su fuente):
  1. Lo busca por nombre entre los locales de OpenStreetMap de su municipio (publico/locales/CODIGO.json).
     Si lo encuentra, le añade las marcas «mn:*» (motivo, fuente, estilos, top, nueva).
  2. Si no está en OpenStreetMap, lo busca en Nominatim (OpenStreetMap) por nombre y municipio, y si no,
     por su dirección en CartoCiudad (IGN). Solo lo añade si la ubicación cae dentro de su municipio
     (o a menos de 3 km del centro) y la dirección tiene calle y número o el punto es el propio local.
  3. Si no se puede ubicar con seguridad, NO se añade (queda en el informe publico/destacados.json).
Se ejecuta cada día después de generar.py; es idempotente (borra lo que añadió el día anterior y lo vuelve a hacer).
"""
import json, os, re, sys, time, math, unicodedata, urllib.request, urllib.parse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(RAIZ, 'publico')
CACHE = os.path.join(RAIZ, 'cache', 'destacados_geo2.json')
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
FIESTA = {'nightclub', 'bar', 'pub', 'music_venue', 'events_venue', 'concert_hall', 'theatre', 'restaurant', 'biergarten'}
GENERICAS = {'discoteca', 'disco', 'club', 'sala', 'the', 'el', 'la', 'los', 'las', 'de', 'del', 'beach', 'nightclub', 'dance',
             'ibiza', 'barcelona', 'madrid', 'marbella', 'mallorca', 'bilbao', 'salou', 'sevilla', 'malaga', 'valencia', 'tenerife', 'lloret',
             'pamplona', 'zaragoza', 'granada', 'murcia', 'benidorm', 'matar', 'mataro', 'banus', 'san', 'sebastian', 'bar', 'pub', 'theclub', 'lounge'}


def nz(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()


def nucleo(s):
    toks = [t for t in re.split(r'[^a-z0-9]+', nz(s)) if t]
    core = [t for t in toks if t not in GENERICAS]
    return ''.join(core or toks)


def km(a, b, c, d):
    return math.hypot((a - c) * 111.2, (b - d) * 111.2 * math.cos(math.radians(a)))


def get(url, tries=2):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            print('  aviso:', url[:90], e, flush=True); time.sleep(2)
    return None


def calle(s):
    """Palabras significativas de la calle de una dirección («Calle del Doctor Cortezo, 1» → {doctor, cortezo})."""
    s = nz(str(s or '').split(',')[0])
    return {w for w in re.split(r'[^a-z0-9]+', s) if len(w) > 2 and w not in {'calle', 'carrer', 'avenida', 'avinguda', 'plaza', 'placa', 'paseo', 'passeig', 'del', 'de', 'la', 'las', 'los', 'els', 'dels', 'les'}}


def coincide(nombre, el, dirx=''):
    """Mismo nombre una vez quitadas las palabras genéricas (discoteca, club, sala, la, nombre de la ciudad…).
    No vale que un nombre contenga al otro: «Hyde Club» no es «Hyde Park» ni «Indiana» es «Bar Diana»."""
    t = el.get('tags') or {}
    a = nucleo(nombre)
    for c in filter(None, [t.get('name'), t.get('name:es'), t.get('alt_name'), t.get('brand')]):
        if a and nucleo(c) == a:
            # si los dos tienen calle y no se parecen en nada, no es el mismo sitio
            cs, ce = calle(dirx), calle(t.get('addr:street') or t.get('addr:place') or '')
            if cs and ce and not (cs & ce) and re.search(r'\d', dirx or ''):
                return 0
            return 3
    return 0


def main():
    lista = json.load(open(os.path.join(RAIZ, 'datos', 'destacados.json'), encoding='utf-8'))['locales']
    munis = {m[0]: m for m in json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))['municipios']}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    geo = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    ix_path = os.path.join(PUB, 'indice.json')
    ix = json.load(open(ix_path, encoding='utf-8'))
    archivos = {}

    def locales(c):
        if c not in archivos:
            p = os.path.join(PUB, 'locales', f'{c}.json')
            j = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'m': c, 'gen': ix.get('gen'), 'datos': ix.get('datos'), 'elements': []}
            # limpiar lo añadido ayer
            j['elements'] = [e for e in j['elements'] if e.get('type') != 'mn']
            for e in j['elements']:
                t = e.get('tags') or {}
                for k in [k for k in t if k.startswith('mn:')]:
                    del t[k]
            archivos[c] = j
        return archivos[c]['elements']

    informe = {'encontrados': [], 'anadidos': [], 'sin_ubicar': []}
    for i, d in enumerate(lista):
        c = d['muni']; els = locales(c)
        marcas = {'mn:motivo': d['motivo'], 'mn:fuente': d['fuente']}
        if d.get('estilos'): marcas['mn:estilos'] = ';'.join(d['estilos'])
        if d.get('top'): marcas['mn:top'] = 'yes'
        if d.get('nueva'): marcas['mn:nueva'] = d['nueva']
        best = max(((max(coincide(nn, e, d.get('dir', '')) for nn in [d['n']] + d.get('alias', [])) + (1 if (e.get('tags') or {}).get('amenity') == 'nightclub' else 0), e) for e in els
                    if (e.get('tags') or {}).get('amenity') in FIESTA), default=(0, None), key=lambda x: x[0])
        if best[0] >= 3:
            best[1].setdefault('tags', {}).update(marcas)
            informe['encontrados'].append([d['n'], c, f"{best[1]['type']}/{best[1]['id']}", best[1]['tags'].get('name')])
            continue
        m = munis.get(c); mlat, mlng = (m[2], m[3]) if m else (None, None)
        clave = f"{d['n']}|{c}|{d.get('dir', '')}"
        if clave not in geo:
            pos = None
            q = f"{d['n']}, {m[1].split('/')[0] if m else ''}, España"
            r = get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'countrycodes': 'es', 'limit': 5, 'addressdetails': 1}))
            time.sleep(1.1)
            fallo = r is None
            for x in r or []:
                if x.get('category') in ('amenity', 'leisure', 'tourism') and nucleo(d['n']) and nucleo(x.get('name') or '') == nucleo(d['n']):
                    la, lo = float(x['lat']), float(x['lon'])
                    if mlat is None or km(la, lo, mlat, mlng) < 25:
                        pos = {'lat': la, 'lng': lo, 'via': 'nominatim', 'osm': f"{x.get('osm_type')}/{x.get('osm_id')}"}; break
            if not pos and re.search(r'\d', d.get('dir') or ''):
                r = get('https://www.cartociudad.es/geocoder/api/geocoder/find?q=' + urllib.parse.quote(f"{d['dir']}, {m[1].split('/')[0] if m else ''}"))
                g = re.search(r'POINT\(([-\d.]+) ([-\d.]+)\)', (r or {}).get('geom') or '')
                if g and (r or {}).get('type') == 'portal' and str(r.get('muniCode') or c) == c:
                    la, lo = float(g.group(2)), float(g.group(1))
                    if mlat is None or km(la, lo, mlat, mlng) < 25:
                        pos = {'lat': la, 'lng': lo, 'via': 'cartociudad'}
            if pos or not fallo:
                geo[clave] = pos     # si Nominatim no respondió, se reintenta otro día
        pos = geo.get(clave)
        if pos:
            tags = {'amenity': 'nightclub', 'name': d['n'], **marcas}
            if d.get('dir'): tags['addr:full'] = d['dir']
            els.append({'type': 'mn', 'id': f'd{i}', 'lat': round(pos['lat'], 6), 'lon': round(pos['lng'], 6), 'tags': tags})
            informe['anadidos'].append([d['n'], c, pos['via']])
        else:
            informe['sin_ubicar'].append([d['n'], c, d.get('dir', '')])
    for c, j in archivos.items():
        with open(os.path.join(PUB, 'locales', f'{c}.json'), 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, separators=(',', ':'))
        ix['municipios'][c] = len(j['elements'])
    ix['destacados'] = {'total': len(lista), 'encontrados': len(informe['encontrados']), 'anadidos': len(informe['anadidos']), 'sin_ubicar': len(informe['sin_ubicar'])}
    json.dump(ix, open(ix_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(geo, open(CACHE, 'w'), ensure_ascii=False)
    json.dump(informe, open(os.path.join(PUB, 'destacados.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('destacados:', ix['destacados'], flush=True)
    for x in informe['sin_ubicar']:
        print('  sin ubicar:', x, flush=True)


if __name__ == '__main__':
    main()
