import asyncio, os
from playwright.async_api import async_playwright
os.makedirs('copia/diseno', exist_ok=True)
H = 'file://' + os.path.abspath('herramientas/diseno/mapa.html')
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        for n, w, h, extra in [('mapa-movil', 390, 300, '?z=14.6'), ('mapa-escritorio', 760, 420, '?z=15.1'), ('mapa-ficha', 390, 200, '?z=15.6&lat=41.39763&lng=2.191241')]:
            pg = await b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=2)
            await pg.goto(H + extra); await pg.wait_for_function("document.title === 'listo'", timeout=60000); await pg.wait_for_timeout(1500)
            await pg.screenshot(path=f'copia/diseno/{n}.png'); print(n, 'ok')
        await b.close()
asyncio.run(main())
