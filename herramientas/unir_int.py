#!/usr/bin/env python3
"""Une lo generado por país (salida_int/PAIS/) en una sola carpeta para publicar con los datos de España:
   publico_int/locales/CODIGO.json, publico_int/indice-int.json y publico_int/lugares-int.json"""
import glob, json, os, shutil, datetime as dt
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ENT, SAL = os.path.join(RAIZ, 'salida_int'), os.path.join(RAIZ, 'publico_int')
shutil.rmtree(SAL, ignore_errors=True); os.makedirs(os.path.join(SAL, 'locales'))
paises, munis, lugares = {}, {}, []
for ix in sorted(glob.glob(os.path.join(ENT, '*', 'indice.json'))):
    d = os.path.dirname(ix); j = json.load(open(ix, encoding='utf-8'))
    for f in glob.glob(os.path.join(d, 'locales', '*.json')): shutil.copy(f, os.path.join(SAL, 'locales'))
    munis.update(j['municipios']); paises[j['pais']] = {'datos': j.get('datos'), 'gen': j.get('gen'), 'total': j.get('total'), 'ciudades': len(j['municipios'])}
    try: lugares += json.load(open(os.path.join(d, 'lugares.json'), encoding='utf-8'))
    except Exception: pass
# Países que esta semana han fallado: se mantiene lo de la semana anterior (carpeta «previo», copia de la rama datos-int)
PREV = os.path.join(RAIZ, 'previo')
try:
    pj = json.load(open(os.path.join(PREV, 'indice-int.json'), encoding='utf-8'))
    pl = json.load(open(os.path.join(PREV, 'lugares-int.json'), encoding='utf-8')).get('l', [])
except Exception:
    pj, pl = {}, []
for cc, info in (pj.get('paises') or {}).items():
    if cc in paises: continue
    for cod, n in pj['municipios'].items():
        if cod.startswith(cc):
            f = os.path.join(PREV, 'locales', cod + '.json')
            if os.path.exists(f): shutil.copy(f, os.path.join(SAL, 'locales')); munis[cod] = n
    lugares += [x for x in pl if str(x[1]).startswith(cc)]
    paises[cc] = dict(info, semana_anterior=True); print('se mantiene la semana anterior de', cc)
gen = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
json.dump({'gen': gen, 'fuente': 'OpenStreetMap vía Geofabrik', 'licencia': 'ODbL 1.0 · © colaboradores de OpenStreetMap', 'paises': paises, 'municipios': munis},
          open(os.path.join(SAL, 'indice-int.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({'gen': gen, 'formato': ['nombre', 'codigo_ciudad', 'lat', 'lng', 'tipo s/q/n'], 'l': lugares},
          open(os.path.join(SAL, 'lugares-int.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('países', list(paises), '| ciudades con datos', len(munis), '| locales', sum(p['total'] or 0 for p in paises.values()), '| barrios', len(lugares))
