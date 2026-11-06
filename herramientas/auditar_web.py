"""Auditoría visual y funcional de la web publicada (solo lectura).

Abre cada pantalla en móvil y escritorio, hace capturas, cuenta errores de consola,
peticiones fallidas y problemas de accesibilidad (axe-core). Nunca envía formularios.
Salida: carpeta «auditoria» (se guarda en la rama «auditoria-web»).
"""
import json, os, time, datetime, traceback
from playwright.sync_api import sync_playwright

WEB = os.environ.get('WEB', 'https://mikenights.com').rstrip('/')
OUT = 'auditoria'
os.makedirs(OUT, exist_ok=True)
HOY = datetime.date.today().isoformat()
AXE = os.environ.get('AXE', '')  # ruta a axe.min.js

def esperar(page, ms=2500):
    try: page.wait_for_load_state('networkidle', timeout=15000)
    except Exception: pass
    page.wait_for_timeout(ms)

def clic(page, sel, ms=1800):
    loc = page.locator(sel).first
    loc.scroll_into_view_if_needed(timeout=8000)
    loc.click(timeout=8000)
    page.wait_for_timeout(ms)

# (id, ruta, acciones) — acciones: lista de ('clic', selector) | ('escribir', selector, texto) | ('ls', clave, valor) | ('scroll', y)
PANTALLAS = [
    ('01-portada', '/', []),
    ('02-buscar', '/', [('escribir', '#city', 'Barc')]),
    ('03-plan-bcn', '/#/plan/08019', []),
    ('04-idea-noche', '/#/plan/08019', [('clic', '.plan--exp')]),
    ('05-resultados-fiesta', f'/#/resultados/08019/{HOY}/2/fiesta', []),
    ('06-resultados-cenas', f'/#/resultados/08019/{HOY}/2/cenas', []),
    ('07-resultados-mapa', f'/#/resultados/08019/{HOY}/2/fiesta', [('clic', '[data-action="view"][data-v="map"]')]),
    ('08-ficha', f'/#/resultados/08019/{HOY}/2/fiesta', [('clic', '[data-action="ficha"]')]),
    ('09-favoritos-vacio', '/', [('clic', '.tabbar [data-action="favs"]')]),
    ('10-favoritos-con-uno', f'/#/resultados/08019/{HOY}/2/fiesta', [('clic', '[data-action="fav"]'), ('clic', '.tabbar [data-action="favs"]')]),
    ('11-mis-reservas', '/', [('clic', '[data-action="mis-reservas"]')]),
    ('12-panel-acceso', '/#panel', []),
    ('13-alta-local', '/#alta', []),
    ('14-habitacion', '/#habitacion', []),
    ('15-legal', '/', [('clic', '[data-action="legal"]')]),
    ('16-para-locales', '/para-locales.html', []),
    ('17-ciudades', '/ocio-nocturno/', []),
    ('18-seo-ciudad', '/ocio-nocturno/barcelona-08019', []),
    ('19-seo-tema', '/ocio-nocturno/discotecas-en-barcelona-08019', []),
    ('20-seo-local', '/ocio-nocturno/local-sala-apolo-08019', []),
    ('21-ingles', '/', [('ls', 'mn.lang', 'en')]),
    ('22-no-existe', '/esta-pagina-no-existe', []),
    ('23-enlace-local', '/#/local/08019/node%2F0', []),
]
DISPOSITIVOS = {
    'movil': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                  user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'),
    'pc': dict(viewport={'width': 1440, 'height': 900}, device_scale_factor=1),
}

informe = {'web': WEB, 'fecha': datetime.datetime.utcnow().isoformat() + 'Z', 'pantallas': []}
with sync_playwright() as p:
    nav = p.chromium.launch()
    for disp, opts in DISPOSITIVOS.items():
        for pid, ruta, acciones in PANTALLAS:
            ctx = nav.new_context(locale='es-ES', timezone_id='Europe/Madrid', **opts)
            ls = [a for a in acciones if a[0] == 'ls']
            if ls:
                ctx.add_init_script(';'.join(f"try{{localStorage.setItem({json.dumps(a[1])},{json.dumps(a[2])})}}catch(e){{}}" for a in ls))
            page = ctx.new_page()
            errores, fallidas, peticiones = [], [], []
            page.on('console', lambda m: m.type == 'error' and len(errores) < 30 and errores.append(m.text[:300]))
            page.on('pageerror', lambda e: len(errores) < 30 and errores.append('excepción: ' + str(e)[:300]))
            page.on('requestfailed', lambda r: len(fallidas) < 30 and fallidas.append(f"{r.url[:160]} · {r.failure}"))
            page.on('response', lambda r: peticiones.append((r.url, r.status)))
            r = {'id': pid, 'disp': disp, 'ruta': ruta}
            t0 = time.time()
            try:
                resp = page.goto(WEB + ruta, wait_until='domcontentloaded', timeout=45000)
                r['estado'] = resp.status if resp else None
                r['url_final'] = page.url
                esperar(page)
                for a in acciones:
                    if a[0] == 'clic': clic(page, a[1])
                    elif a[0] == 'escribir':
                        page.locator(a[1]).first.click(timeout=8000); page.keyboard.type(a[2], delay=120); page.wait_for_timeout(1500)
                esperar(page, 1500)
                r['segundos'] = round(time.time() - t0, 1)
                r['titulo'] = page.title()
                r['texto'] = page.evaluate("() => { const m = document.querySelector('#modal:not([hidden])') || document.querySelector('#screen') || document.body; return m.innerText.slice(0, 2500); }")
                r['h1'] = page.evaluate("() => [...document.querySelectorAll('h1')].map(h => h.innerText.trim()).slice(0, 3)")
                r['nodos'] = page.evaluate("() => document.getElementsByTagName('*').length")
                r['alto'] = page.evaluate("() => document.documentElement.scrollHeight")
                r['ancho_desborda'] = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")
                r['fuentes'] = page.evaluate("() => [...new Set([...document.querySelectorAll('h1,h2,p,button,a')].slice(0,200).map(e => getComputedStyle(e).fontFamily.split(',')[0]))]")
                r['botones_pequenos'] = page.evaluate("""() => [...document.querySelectorAll('button,a,[role=button],input,select')].filter(e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && (b.height < 24 || b.width < 24) && getComputedStyle(e).visibility !== 'hidden'; }).length""")
                r['imagenes_rotas'] = page.evaluate("() => [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.src).map(i => i.src.slice(0, 120)).slice(0, 10)")
                page.screenshot(path=f'{OUT}/{disp}-{pid}.png', full_page=False)
                if r['alto'] <= 9000:
                    page.screenshot(path=f'{OUT}/{disp}-{pid}-entera.png', full_page=True)
                if AXE and disp == 'movil':
                    try:
                        page.add_script_tag(path=AXE)
                        v = page.evaluate("async () => (await axe.run(document, {resultTypes: ['violations']})).violations.map(x => ({id: x.id, impacto: x.impact, n: x.nodes.length, ayuda: x.help}))")
                        r['axe'] = v
                    except Exception as e:
                        r['axe_error'] = str(e)[:200]
            except Exception:
                r['fallo'] = traceback.format_exc()[-600:]
                try: page.screenshot(path=f'{OUT}/{disp}-{pid}.png')
                except Exception: pass
            r['errores_consola'] = errores
            r['peticiones_fallidas'] = fallidas
            r['peticiones_error'] = [f"{u[:160]} · {s}" for u, s in peticiones if s >= 400][:20]
            r['hosts'] = sorted({u.split('/')[2] for u, s in peticiones if '://' in u})
            informe['pantallas'].append(r)
            print(disp, pid, r.get('estado'), r.get('segundos'), 'errores:', len(errores), 'fallo' if 'fallo' in r else '')
            ctx.close()
    nav.close()
json.dump(informe, open(f'{OUT}/informe.json', 'w'), ensure_ascii=False, indent=1)
