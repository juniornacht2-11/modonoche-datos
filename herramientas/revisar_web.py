#!/usr/bin/env python3
"""Revisa la web PUBLICADA de MODO NOCHE con un navegador real (Chromium) y guarda capturas y datos en revision/.
Solo lee páginas públicas: no reserva, no envía formularios ni crea cuentas."""
import asyncio, datetime as dt, json, os, urllib.request
from playwright.async_api import async_playwright

WEB = os.environ.get('WEB', 'https://mikenights.com').rstrip('/')
API = 'https://frosty-bird-92d2.juniornacht2.workers.dev'
OUT = 'revision'; os.makedirs(OUT, exist_ok=True)
hoy = dt.date.today(); SAB = (hoy + dt.timedelta(days=(5 - hoy.weekday()) % 7)).isoformat()
INFO = {'web': WEB, 'sabado': SAB, 'paginas': {}}


def leer(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'MODO-NOCHE-revision'}), timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 0, str(e)


async def main():
    s, t = leer(WEB + '/sw.js'); INFO['sw'] = next((l.strip() for l in t.splitlines() if 'CACHE =' in l), t[:120])
    s, t = leer(API + '/api/comunidad/estado?t=rev'); INFO['servicio'] = t[:300]
    s, t = leer(WEB + '/ajustes.json'); INFO['ajustes_aviso_legal'] = (json.loads(t).get('aviso_legal') if s == 200 else t[:200])
    s, t = leer(WEB + '/datos/nombres-ciudades.json'); INFO['nombres_ciudades'] = s
    s, t = leer(WEB + '/img/cat/v/fiesta-1.jpg'); INFO['fotos_variantes'] = s
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for nombre, ancho, alto, movil in [('mov', 393, 852, True), ('pc', 1440, 900, False)]:
            ctx = await b.new_context(viewport={'width': ancho, 'height': alto}, is_mobile=movil, has_touch=movil, locale='es-ES', timezone_id='Europe/Madrid')
            pg = await ctx.new_page(); errores = []
            pg.on('pageerror', lambda e: errores.append('PAGEERROR ' + str(e)[:200]))
            pg.on('console', lambda m: errores.append(m.type + ' ' + m.text[:200]) if m.type == 'error' else None)

            async def captura(clave, url, espera=6000, accion=None, lang='es'):
                errores.clear()
                try:
                    await pg.goto(WEB + '/#x'); await pg.evaluate(f"localStorage.setItem('mn.lang','{lang}')")
                    await pg.goto(url); await pg.reload(); await pg.wait_for_timeout(espera)
                    if accion: await accion()
                    h = await pg.evaluate('document.body.scrollHeight')
                    for y in range(0, min(h, 9000), 600): await pg.evaluate(f'scrollTo(0,{y})'); await pg.wait_for_timeout(120)
                    await pg.evaluate('scrollTo(0,0)'); await pg.wait_for_timeout(800)
                    await pg.screenshot(path=f'{OUT}/{nombre}-{clave}.png', full_page=True)
                    txt = await pg.evaluate("document.querySelector('#modal:not([hidden])') ? document.querySelector('#modal').innerText : document.body.innerText")
                    INFO['paginas'][f'{nombre}-{clave}'] = {'url': url, 'h1': await pg.evaluate("(document.querySelector('#modal:not([hidden]) h2, #modal:not([hidden]) .fh-t, h1')||{}).innerText||''"),
                                                         'tarjetas': await pg.locator('.card').count(), 'texto': txt[:2500], 'errores': list(errores)}
                except Exception as e:
                    INFO['paginas'][f'{nombre}-{clave}'] = {'url': url, 'fallo': str(e)[:300], 'errores': list(errores)}

            async def ficha():
                c = pg.locator('.card').first
                if await c.count(): await c.click(position={'x': 30, 'y': 30}); await pg.wait_for_timeout(3500)

            async def legal():
                await pg.locator('footer').get_by_text('Aviso legal y fuentes', exact=True).click(); await pg.wait_for_timeout(1500)

            if movil:
                # métricas de la lista en móvil: altura de tarjetas, cuántas caben en pantalla, peso y peticiones
                pesos = []
                pg.on('response', lambda r: pesos.append(r.url))
                await pg.goto(WEB + '/#x'); await pg.goto(f'{WEB}/#/resultados/08019/{SAB}/2/fiesta'); await pg.reload(); await pg.wait_for_timeout(9000)
                INFO['metricas_lista_bcn'] = await pg.evaluate("""(() => { const c=[...document.querySelectorAll('.card')].slice(0,20).map(e=>e.getBoundingClientRect().height); const first=document.querySelector('.card'); return {tarjetas:document.querySelectorAll('.card').length, alto_medio:Math.round(c.reduce((a,b)=>a+b,0)/Math.max(1,c.length)), primera_tarjeta_y: first?Math.round(first.getBoundingClientRect().top+scrollY):null, con_reserva_aqui: document.querySelectorAll('[data-action=reservar]').length, con_foto_propia: [...document.querySelectorAll('.card-img img')].filter(i=>!i.classList.contains('cat-foto')).length, orientativas: document.querySelectorAll('.cat-nota').length, texto_count: (document.querySelector('.count-line')||{}).innerText||''}; })()""")
                await pg.goto(WEB + '/#x'); await pg.goto(WEB + '/'); await pg.reload(); await pg.wait_for_timeout(6000)
                INFO['metricas_portada'] = await pg.evaluate("""(() => { const vh=innerHeight; const vis=[...document.querySelectorAll('h1,h2,button,a,.chip,input')].filter(e=>{const r=e.getBoundingClientRect(); return r.top>=0 && r.bottom<=vh && r.width>0}).map(e=>(e.innerText||e.placeholder||'').trim().slice(0,40)).filter(Boolean); const res=performance.getEntriesByType('resource'); return {en_primera_pantalla: vis, peticiones: res.length, kb_transferidos: Math.round(res.reduce((a,r)=>a+(r.transferSize||0),0)/1024), dominios: [...new Set(res.map(r=>new URL(r.name).host))], alto_total: document.body.scrollHeight, imgs_hero: [...document.querySelectorAll('img')].filter(i=>i.getBoundingClientRect().top<vh).length}; })()""")
            await captura('1-portada', WEB + '/')
            await captura('2-plan-madrid', f'{WEB}/#/plan/28079/{SAB}/2')
            await captura('3-fiesta-madrid', f'{WEB}/#/resultados/28079/{SAB}/2/fiesta', 9000)
            await captura('4-ficha-madrid', f'{WEB}/#/resultados/28079/{SAB}/2/fiesta', 9000, ficha)
            if movil:
                await captura('5-cenas-madrid', f'{WEB}/#/resultados/28079/{SAB}/2/cenas', 9000)
                await captura('6-hoteles-sevilla', f'{WEB}/#/resultados/41091/{SAB}/2/hoteles', 9000)
                await captura('7-plan-lisboa', f'{WEB}/#/plan/PT2267057/{SAB}/2', 9000)
                await captura('8-fiesta-londres-en', f'{WEB}/#/resultados/GB2643743/{SAB}/2/fiesta', 10000, lang='en')
                await captura('9-legal', WEB + '/', 5000, legal)
                await captura('10-panel', WEB + '/#panel', 5000)
                await captura('11-para-locales', WEB + '/para-locales.html', 4000)
            await ctx.close()
        await b.close()
    json.dump(INFO, open(f'{OUT}/informe.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in INFO.items() if k != 'paginas'}, ensure_ascii=False))
    for k, v in INFO['paginas'].items(): print(k, v.get('h1'), v.get('tarjetas'), v.get('fallo', ''), v.get('errores'))

asyncio.run(main())
