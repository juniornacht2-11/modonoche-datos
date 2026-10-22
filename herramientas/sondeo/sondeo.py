"""Sondeo: registros completos de las agendas de Andalucía y Vigo (solo lectura)."""
import os, json, urllib.request, collections
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
def j(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read())
out = {}
try:
    a = j('https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json')
    fut = [r for r in a if any((d.get('end_date_registration') or '') >= '2026-10-22' for d in (r.get('date_registration') or []))]
    out['andalucia_n'] = len(a); out['andalucia_futuros'] = len(fut)
    out['andalucia_ej'] = fut[:4]
    out['andalucia_prov'] = collections.Counter(str(r.get('province')) for r in fut).most_common(12)
    out['andalucia_temas'] = collections.Counter(str(r.get('themes')) for r in fut).most_common(15)
    out['andalucia_loc'] = collections.Counter(str(r.get('location')) for r in fut).most_common(15)
except Exception as e: out['andalucia_err'] = str(e)[:300]
try:
    v = j('https://datos.vigo.org/data/axenda/agenda-hoy.json')
    out['vigo_n'] = len(v); out['vigo_ej'] = [r for r in v if r.get('fecha_inicio')][:5]
except Exception as e: out['vigo_err'] = str(e)[:300]
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
