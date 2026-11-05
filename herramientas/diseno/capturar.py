import asyncio, os, traceback
from playwright.async_api import async_playwright
os.makedirs('copia/diseno', exist_ok=True)
LOG = open('copia/diseno/log.txt', 'w')
H = 'file://' + os.path.abspath('herramientas/diseno/mapa.html')
TRABAJOS = [('mapa-movil', 390, 300, '?z=14.6'), ('mapa-escritorio', 760, 420, '?z=15.1'),
            ('mapa-ficha', 390, 200, '?z=15.6&lat=41.39763&lng=2.191241&ruta=0&pts=2.191241,41.39763'),
            ('mapa-ficha-esc', 420, 260, '?z=15.6&lat=41.39763&lng=2.191241&ruta=0&pts=2.191241,41.39763'),
            ('mapa-lista', 520, 760, '?z=12.6&lat=41.3875&lng=2.158&ruta=0&pts=2.16956,41.37439;2.19124,41.39763;2.15460,41.38457;2.17394,41.38957;2.16261,41.38944;2.11433,41.38126;2.14904,41.39460;2.14487,41.37834;2.15038,41.39530;2.16398,41.38844')]
TRABAJOS += [('ps-movil', 390, 280, '?z=17.3&lat=41.37395&lng=2.16962&pts=2.170174,41.373601;2.169049,41.37388;2.169518,41.374356'),
             ('ps-escritorio', 720, 520, '?z=17.5&lat=41.37398&lng=2.16962&pts=2.170174,41.373601;2.169049,41.37388;2.169518,41.374356'),
             ('ps-plan-movil', 390, 420, '?z=17.4&lat=41.37392&lng=2.16962&pts=2.170174,41.373601;2.169049,41.37388;2.169518,41.374356'),
             ('apolo-ficha', 390, 220, '?z=16.6&lat=41.374391&lng=2.169561&ruta=0&pts=2.169561,41.374391'),
             ('apolo-ficha-esc', 440, 300, '?z=16.4&lat=41.374391&lng=2.169561&ruta=0&pts=2.169561,41.374391;2.167898,41.375481;2.169049,41.37388;2.170174,41.373601')]
TRABAJOS = TRABAJOS[5:]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        for n, w, h, extra in TRABAJOS:
            try:
                pg = await b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=2)
                pg.on('console', lambda m: LOG.write(f'{n} console {m.type}: {m.text[:300]}\n'))
                pg.on('pageerror', lambda e: LOG.write(f'{n} pageerror: {e}\n'))
                await pg.goto(H + extra); await pg.wait_for_function("document.title === 'listo'", timeout=90000); await pg.wait_for_timeout(2000)
                await pg.screenshot(path=f'copia/diseno/{n}.png'); LOG.write(f'{n} ok\n')
            except Exception:
                LOG.write(f'{n} FALLO {traceback.format_exc()[-800:]}\n')
                try: await pg.screenshot(path=f'copia/diseno/{n}-fallo.png')
                except Exception: pass
        await b.close()
asyncio.run(main()); LOG.close()
