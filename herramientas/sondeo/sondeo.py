"""Sondeo: comprobar que la web publicada es la versión 15 (sin datos personales)."""
import os, json, urllib.request, time
os.makedirs('salida', exist_ok=True)
W = 'https://modonoche.juniornacht2.workers.dev'; S = 'https://frosty-bird-92d2.juniornacht2.workers.dev'
def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u + ('&' if '?' in u else '?') + 'x=' + str(time.time()), headers={'User-Agent': 'MODO-NOCHE-sondeo', 'Cache-Control': 'no-cache'}), timeout=60)
        return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e: return e.code, ''
    except Exception as e: return 0, str(e)[:200]
out = {}
c, sw = get(W + '/sw.js'); out['sw'] = [c, [l for l in sw.splitlines() if 'CACHE =' in l]]
c, app = get(W + '/app.js'); out['app'] = [c, len(app), {k: k in app for k in ['duenosHtml', 'ver-cerrados', 'Reservar aquí', 'acc-tab', 'no es para salir de noche', 'openPanel', 'r.tel.replace']}]
c, css = get(W + '/estilos.css'); out['css'] = [c, 'Reorganización (v15)' in css]
c, ix = get(W + '/'); out['index'] = [c, {k: k in ix for k in ['foot-cols', 'Recibir reservas', 'JetBrains']}]
c, en = get(W + '/i18n/en.json'); 
try: d = json.loads(en); out['en'] = [c, len(d), d.get('Ver planes'), d.get('Reservar aquí')]
except Exception as e: out['en'] = [c, str(e)[:100]]
c, pl = get(W + '/para-locales'); out['para_locales'] = [c, 'res_t' in pl]
c, es = get(S + '/api/comunidad/estado'); out['estado'] = [c, es[:200]]
c, rv = get(S + '/api/reservables?m=41091'); out['reservables_sevilla'] = [c, rv[:200]]
c, rb = get(S + '/api/reservables?m=08019'); out['reservables_bcn'] = [c, rb[:200]]
c, ca = get(S + '/api/cuenta'); out['cuenta_sin_sesion'] = [c, ca[:150]]
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
