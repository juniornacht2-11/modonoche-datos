#!/usr/bin/env python3
"""
MODO NOCHE · locales de otros países (OpenStreetMap vía Geofabrik), igual que España
=====================================================================================
Para UN país (variable PAIS o argumento): descarga su extracto de OpenStreetMap (Geofabrik), se queda con
discotecas, bares, pubs, salas, restaurantes y alojamientos con nombre, y asigna cada uno a la ciudad
más cercana de datos/ciudades.json (GeoNames) dentro de un radio que depende de su población.

  salida_int/PAIS/locales/CODIGO.json   {"m": código, "gen": fecha, "datos": fecha de OSM, "elements": [...]}
  salida_int/PAIS/indice.json           {"pais": "DE", "datos": fecha, "municipios": {código: n}}
  salida_int/PAIS/lugares.json          barrios y zonas (Kreuzberg, Soho…) para el buscador: [nombre, código, lat, lng, tipo]

Los «elements» siguen el formato de Overpass, igual que los de España, para que la web los lea igual.
Uso: PAIS=PT python3 herramientas/generar_int.py      (pruebas: --geojsonseq ARCHIVO)
"""
from __future__ import annotations
import argparse, datetime as dt, json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar import interesa, centro, tipo_id, norm, km, ETIQUETAS, ALOJ, UA, log  # mismas reglas que España

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GEOFABRIK = {'PT': 'europe/portugal', 'IT': 'europe/italy', 'FR': 'europe/france', 'DE': 'europe/germany', 'NL': 'europe/netherlands',
             'BE': 'europe/belgium', 'GB': 'europe/united-kingdom', 'IE': 'europe/ireland-and-northern-ireland', 'GR': 'europe/greece',
             'HR': 'europe/croatia', 'AT': 'europe/austria', 'CH': 'europe/switzerland'}
FILTRO = ['nwr/amenity=nightclub,music_venue,concert_hall,bar,pub,events_venue,restaurant,theatre',
          'nwr/tourism=hotel,hostel,guest_house,apartment,motel', 'n/place=suburb,quarter,neighbourhood']
LUGARES = {'suburb': 's', 'quarter': 'q', 'neighbourhood': 'n'}
AHORA = dt.datetime.now(dt.timezone.utc)


def radio_km(pop: int) -> float:
    """Hasta dónde llega una ciudad: las grandes abarcan sus barrios y los pueblos solo su centro."""
    return 12.0 if pop >= 1_000_000 else 8.0 if pop >= 300_000 else 5.0 if pop >= 100_000 else 3.5 if pop >= 30_000 else 2.5


class Ciudades:
    """Rejilla de 0,1° para encontrar rápido la ciudad que corresponde a cada punto."""
    def __init__(self, lista):
        self.c, self.g = lista, {}
        for i, c in enumerate(lista):
            r = radio_km(c[4]); dla = r / 111 + 0.1; dlo = r / (111 * max(0.2, math.cos(math.radians(c[2])))) + 0.1
            for a in range(int((c[2] - dla) * 10), int((c[2] + dla) * 10) + 1):
                for b in range(int((c[3] - dlo) * 10), int((c[3] + dlo) * 10) + 1):
                    self.g.setdefault((a, b), []).append(i)

    def buscar(self, lat, lng):
        best, bs = None, 1.0
        for i in self.g.get((int(lat * 10), int(lng * 10)), []):
            c = self.c[i]; d = km(lat, lng, c[2], c[3]); s = d / radio_km(c[4])
            if s <= bs: best, bs = c, s
        return best


def procesar(ruta: str, ciudades: list) -> dict:
    idx = Ciudades(ciudades)
    st = {'lineas': 0, 'locales_leidos': 0, 'sin_ciudad': 0, 'duplicados': 0}
    por_c, vistos, lugares = {}, {}, []
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip().lstrip('\x1e')
            if not linea:
                continue
            try:
                feat = json.loads(linea)
            except ValueError:
                continue
            st['lineas'] += 1
            p, g = feat.get('properties') or {}, feat.get('geometry') or {}
            if p.get('place') in LUGARES and p.get('name') and g.get('type') == 'Point':
                lo, la = g['coordinates'][:2]; c = idx.buscar(la, lo)
                if c:
                    for nm in {str(p['name'])[:80], str(p.get('name:es') or p['name'])[:80]}:
                        if norm(nm) != norm(c[1]): lugares.append([nm, c[0], round(la, 5), round(lo, 5), LUGARES[p['place']]])
                continue
            k = interesa(p)
            if not k:
                continue
            ce = centro(g)
            if not ce:
                continue
            st['locales_leidos'] += 1
            c = idx.buscar(ce[1], ce[0])
            if not c:
                st['sin_ciudad'] += 1; continue
            t, i = tipo_id(str(feat.get('id') or ''))
            tags = {e: str(p[e])[:250] for e in ETIQUETAS if p.get(e) not in (None, '')}
            el = {'type': t, 'id': i, 'lat': round(ce[1], 6), 'lon': round(ce[0], 6), 'tags': tags}
            clave = (k, norm(tags.get('name', '')), c[0]); dup = None
            for o in vistos.get(clave, []):
                if abs(o['lat'] - el['lat']) < 0.00045 and abs(o['lon'] - el['lon']) < 0.0006: dup = o; break
            if dup:
                for kk, vv in tags.items(): dup['tags'].setdefault(kk, vv)
                st['duplicados'] += 1; continue
            vistos.setdefault(clave, []).append(el)
            por_c.setdefault(c[0], []).append(el)
    for lst in por_c.values():
        lst.sort(key=lambda e: (e['tags'].get('amenity') or e['tags'].get('tourism') or '', norm(e['tags'].get('name', ''))))
    unicos, vist = [], set()
    for x in sorted(lugares, key=lambda x: (norm(x[0]), x[1])):
        if (norm(x[0]), x[1]) in vist: continue
        vist.add((norm(x[0]), x[1])); unicos.append(x)
    st['lugares'] = len(unicos)
    return {'por_c': por_c, 'st': st, 'lugares': unicos}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('pais', nargs='?', default=os.environ.get('PAIS', ''))
    ap.add_argument('--geojsonseq')
    a = ap.parse_args(argv)
    pais = a.pais.upper()
    if pais not in GEOFABRIK:
        log('País no válido:', pais); return 1
    todas = json.load(open(os.path.join(RAIZ, 'datos', 'ciudades.json'), encoding='utf-8'))['ciudades']
    ciudades = [c for c in todas if c[5] == pais]
    trabajo = os.path.join(RAIZ, '.trabajo_int', pais); os.makedirs(trabajo, exist_ok=True)
    fecha = None
    if a.geojsonseq:
        salida = a.geojsonseq
    else:
        url = f'https://download.geofabrik.de/{GEOFABRIK[pais]}-latest.osm.pbf'; pbf = os.path.join(trabajo, 'pais.osm.pbf')
        log('Descargando', url)
        subprocess.run(['curl', '-fsSL', '--retry', '4', '--retry-delay', '20', '-A', UA, '-o', pbf, url], check=True)
        try:
            fecha = subprocess.run(['osmium', 'fileinfo', '-g', 'header.option.osmosis_replication_timestamp', pbf], capture_output=True, text=True).stdout.strip() or None
        except Exception:
            pass
        filtrado = os.path.join(trabajo, 'filtrado.osm.pbf'); log('Filtrando')
        subprocess.run(['osmium', 'tags-filter', '--overwrite', '-o', filtrado, pbf, *FILTRO], check=True)
        os.remove(pbf)   # el extracto pesa varios GB: se borra en cuanto se ha filtrado
        salida = os.path.join(trabajo, 'filtrado.geojsonseq')
        subprocess.run(['osmium', 'export', '--overwrite', '-f', 'geojsonseq', '--add-unique-id=type_id', '-o', salida, filtrado], check=True)
    res = procesar(salida, ciudades)
    total = sum(len(v) for v in res['por_c'].values())
    log(pais, 'estadísticas:', json.dumps(res['st'], ensure_ascii=False), '| locales:', total, '| ciudades con datos:', len(res['por_c']), 'de', len(ciudades))
    if total < 500:
        log('ERROR: muy pocos locales, no se publica nada.'); return 1
    out = os.path.join(RAIZ, 'salida_int', pais); os.makedirs(os.path.join(out, 'locales'), exist_ok=True)
    gen = AHORA.isoformat(timespec='seconds'); indice = {}
    for cod, lst in sorted(res['por_c'].items()):
        with open(os.path.join(out, 'locales', f'{cod}.json'), 'w', encoding='utf-8') as f:
            json.dump({'m': cod, 'gen': gen, 'datos': fecha, 'elements': lst}, f, ensure_ascii=False, separators=(',', ':'))
        indice[cod] = len(lst)
    json.dump({'pais': pais, 'gen': gen, 'datos': fecha, 'total': total, 'estadisticas': res['st'], 'municipios': indice},
              open(os.path.join(out, 'indice.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(res['lugares'], open(os.path.join(out, 'lugares.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    resumen = os.environ.get('GITHUB_STEP_SUMMARY')
    if resumen:
        with open(resumen, 'a', encoding='utf-8') as f:
            f.write(f"## {pais}\n\n- Datos de OSM: {fecha}\n- Locales: {total} en {len(indice)} ciudades\n- Barrios: {len(res['lugares'])}\n- `{json.dumps(res['st'], ensure_ascii=False)}`\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
