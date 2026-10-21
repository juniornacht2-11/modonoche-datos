"""MODO NOCHE · imágenes listas para Instagram, TikTok y WhatsApp (cada día, en publico/redes/).

Por cada ciudad con datos:
  - «Este finde en <ciudad>»: conciertos y fiestas de las agendas oficiales del viernes al domingo (solo eventos reales).
  - «Discotecas top de <ciudad>»: las destacadas por rankings, guías o prensa (cada una con su fuente en el texto).
Formatos: publicación 1080×1350 y historia 1080×1920. Junto a cada imagen, el texto para copiar (con hashtags).
publico/redes/index.html es una galería para descargarlas desde el móvil.
"""
import datetime as dt, html, json, os, re, sys, unicodedata, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(RAIZ, 'publico')
OUT = os.path.join(PUB, 'redes')
FUENTES = os.path.join(RAIZ, '.trabajo', 'fuentes')
WEB = os.environ.get('WEB', 'https://modonoche.juniornacht2.workers.dev')
CIUDADES = os.environ.get('CIUDADES_REDES', '28079,08019,46250,41091,29067,07026,07040,48020,50297,18087,03014,30030,15030,38038,35016,31201,20069,07011,29069,17095,43905,03031,47186,37274,33044,14021,11020,39075,36057,01059,07046,07054,38006,35019,33024,29901,07048').split(',')
UA = {'User-Agent': 'MODO-NOCHE-datos/1.0 (+https://github.com/juniornacht2-11/modonoche-datos)'}
BG, FG, FG2, VIO, CYA, ACI = (7, 7, 11), (245, 243, 255), (165, 162, 181), (168, 85, 247), (34, 211, 238), (199, 255, 74)
E = html.escape
HOY = dt.date.today()


def fuente(nombre, peso, tam):
    """Unbounded y Manrope (Google Fonts, licencia OFL) descargadas una vez en .trabajo/fuentes."""
    os.makedirs(FUENTES, exist_ok=True)
    url = {'Unbounded': 'https://github.com/google/fonts/raw/main/ofl/unbounded/Unbounded%5Bwght%5D.ttf',
           'Manrope': 'https://github.com/google/fonts/raw/main/ofl/manrope/Manrope%5Bwght%5D.ttf'}[nombre]
    p = os.path.join(FUENTES, nombre + '.ttf')
    if not os.path.exists(p):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            open(p, 'wb').write(r.read())
    f = ImageFont.truetype(p, tam)
    try:
        f.set_variation_by_axes([peso])
    except Exception:
        pass
    return f


def fondo(w, h):
    im = Image.new('RGB', (w, h), BG)
    capa = Image.new('RGB', (w, h), BG); d = ImageDraw.Draw(capa)
    d.ellipse((int(w * .45), -int(h * .2), int(w * 1.3), int(h * .45)), fill=(70, 30, 120))
    d.ellipse((-int(w * .4), int(h * .7), int(w * .5), int(h * 1.25)), fill=(10, 70, 85))
    capa = capa.filter(ImageFilter.GaussianBlur(160))
    return Image.blend(im, capa, .9)


def pin(im, x, y, alto):
    """El pin con la luna y la estrella del logo, dibujado con formas simples."""
    s = alto / 92.0; d = ImageDraw.Draw(im)
    def P(px, py): return (x + (px - 16) * s, y + (py - 3) * s)
    cx, cy, r = P(50, 37)[0], P(50, 37)[1], 34 * s
    grad = Image.new('RGB', (int(70 * s), int(95 * s)))
    gd = ImageDraw.Draw(grad)
    for i in range(grad.size[1]):
        t = i / max(1, grad.size[1] - 1); c = tuple(int(VIO[k] * (1 - t) + CYA[k] * t) for k in range(3)); gd.line((0, i, grad.size[0], i), fill=c)
    mask = Image.new('L', grad.size, 0); md = ImageDraw.Draw(mask)
    ox, oy = x, y
    md.ellipse((cx - r - ox, cy - r - oy, cx + r - ox, cy + r - oy), fill=255)
    md.polygon([(cx - r * .93 - ox, cy + r * .37 - oy), (cx + r * .93 - ox, cy + r * .37 - oy), (P(50, 95)[0] - ox, P(50, 95)[1] - oy)], fill=255)
    im.paste(grad, (int(ox), int(oy)), mask)
    d.ellipse((cx - 22 * s, cy - 22 * s, cx + 22 * s, cy + 22 * s), fill=BG)
    lx, ly, lr = P(47, 38)[0], P(47, 38)[1], 15 * s
    d.ellipse((lx - lr, ly - lr, lx + lr, ly + lr), fill=FG)
    mx, my, mr = P(57, 31)[0], P(57, 31)[1], 13 * s
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=BG)
    sx, sy, sr = P(64, 27)[0], P(64, 27)[1], 6 * s
    d.polygon([(sx, sy - sr), (sx + sr * .32, sy - sr * .32), (sx + sr, sy), (sx + sr * .32, sy + sr * .32), (sx, sy + sr), (sx - sr * .32, sy + sr * .32), (sx - sr, sy), (sx - sr * .32, sy - sr * .32)], fill=ACI)


def marca(im, x, y, tam):
    d = ImageDraw.Draw(im); f = fuente('Unbounded', 800, tam)
    d.text((x, y), 'MODO', font=f, fill=FG, anchor='ls')
    w = d.textlength('MODO ', font=f)
    noche = Image.new('RGB', (int(d.textlength('NOCHE', font=f)) + 4, int(tam * 1.2)))
    nd = ImageDraw.Draw(noche)
    for i in range(noche.size[0]):
        t = i / max(1, noche.size[0] - 1); c = tuple(int(VIO[k] * (1 - t) + CYA[k] * t) for k in range(3)); nd.line((i, 0, i, noche.size[1]), fill=c)
    m = Image.new('L', noche.size, 0); ImageDraw.Draw(m).text((0, int(tam * .95)), 'NOCHE', font=f, fill=255, anchor='ls')
    im.paste(noche, (int(x + w), int(y - tam * .95)), m)
    pin(im, x + w + noche.size[0] + tam * .2, y - tam * 1.22, tam * 1.22)


def envolver(d, txt, f, ancho, lineas=2):
    pal, out, cur = txt.split(), [], ''
    for p in pal:
        t = (cur + ' ' + p).strip()
        if d.textlength(t, font=f) <= ancho:
            cur = t
        else:
            if cur: out.append(cur)
            cur = p
        if len(out) >= lineas: break
    if cur and len(out) < lineas: out.append(cur)
    if len(out) == lineas and ' '.join(out) != txt.strip():
        while out[-1] and d.textlength(out[-1] + '…', font=f) > ancho: out[-1] = out[-1][:-1]
        out[-1] = out[-1].rstrip() + '…'
    return out


DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def tarjetas(w, h, kicker, titulo, filas, pie):
    """filas: [(etiqueta, título, detalle)]"""
    im = fondo(w, h); d = ImageDraw.Draw(im); M = 84
    marca(im, M, 150, 46)
    fk, ft, fe, fn, fd, fp = fuente('Manrope', 700, 30), fuente('Unbounded', 800, 74 if len(titulo) < 22 else 60), fuente('Manrope', 800, 24), fuente('Manrope', 800, 38), fuente('Manrope', 500, 28), fuente('Manrope', 600, 30)
    y = 270
    d.text((M, y), kicker.upper(), font=fk, fill=ACI); y += 60
    for l in envolver(d, titulo, ft, w - 2 * M, 3):
        d.text((M, y), l, font=ft, fill=FG); y += int(ft.size * 1.12)
    y += 30
    alto = 212 if h > 1500 else 196
    for et, ti, de in filas:
        if y + alto > h - 190: break
        d.rounded_rectangle((M, y, w - M, y + alto - 18), radius=26, fill=(18, 17, 30), outline=(48, 46, 66), width=2)
        tx = M + 30; ty = y + 24
        if et:
            ew = d.textlength(et, font=fe) + 28
            col = ACI if et.startswith('TOP') else (34, 211, 238) if et.startswith(('HOY', 'VIE', 'SÁB', 'DOM', 'NUEVA')) else (216, 180, 254)
            d.rounded_rectangle((tx, ty, tx + ew, ty + 38), radius=19, fill=col if et.startswith('TOP') else (30, 26, 50), outline=col, width=2)
            d.text((tx + 14, ty + 19), et, font=fe, fill=(11, 11, 16) if et.startswith('TOP') else col, anchor='lm'); ty += 50
        for l in envolver(d, ti, fn, w - 2 * M - 60, 1):
            d.text((tx, ty), l, font=fn, fill=FG); ty += 46
        for l in envolver(d, de, fd, w - 2 * M - 60, 1):
            d.text((tx, ty), l, font=fd, fill=FG2)
        y += alto
    d.text((M, h - 120), pie, font=fp, fill=FG2)
    d.text((M, h - 78), WEB.replace('https://', ''), font=fuente('Manrope', 800, 32), fill=CYA)
    return im


def norm(s):
    return re.sub(r'[^a-z0-9]+', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())


def main():
    munis = {m[0]: m for m in json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))['municipios']}
    os.makedirs(OUT, exist_ok=True)
    # próximo fin de semana (si hoy es viernes a domingo, este)
    vie = HOY + dt.timedelta(days=(4 - HOY.weekday()) % 7) if HOY.weekday() < 4 else HOY - dt.timedelta(days=HOY.weekday() - 4)
    dias = [vie + dt.timedelta(days=i) for i in range(3)]
    piezas = []
    for c in CIUDADES:
        m = munis.get(c)
        if not m: continue
        nom = m[1].split('/')[0].strip()
        if re.match(r'^(.*), (El|La|Los|Las|O|A)$', nom): a, b = nom.rsplit(', ', 1); nom = f'{b} {a}'
        nom = {'03014': 'Alicante', '20069': 'San Sebastián'}.get(c, nom)
        tag = '#' + norm(nom)
        # --- agenda del finde
        pe = os.path.join(PUB, 'eventos', f'{c}.json')
        ev = json.load(open(pe, encoding='utf-8')).get('eventos', []) if os.path.exists(pe) else []
        fin = []
        for e in ev:
            try: ini, ff = dt.date.fromisoformat(e['ini']), dt.date.fromisoformat(e['fin'])
            except Exception: continue
            dia = next((x for x in dias if ini <= x <= ff), None)
            if dia and e.get('mus') and (ff - ini).days <= 3:
                fin.append((dia, e.get('h') or '99', e))
        fin.sort(key=lambda x: (x[0], x[1]))
        vistos, filas, texto = set(), [], []
        for dia, h, e in fin:
            k = norm(e['t'])[:40]
            if k in vistos: continue
            vistos.add(k)
            et = f"{DIAS[dia.weekday()][:3].upper().replace('SAB', 'SÁB')} {dia.day}" + (f" · {e['h']}" if e.get('h') else '')
            de = ' · '.join(x for x in [e.get('lugar'), 'Gratis' if e.get('gratis') else e.get('precio')] if x)
            filas.append((et, e['t'], de or 'Agenda oficial'))
            texto.append(f"• {DIAS[dia.weekday()].capitalize()} {dia.day}{(' a las ' + e['h']) if e.get('h') else ''}: {e['t']}{(' — ' + e['lugar']) if e.get('lugar') else ''}")
        if len(filas) >= 3:
            fuentes_ev = sorted({e['f'] for _, _, e in fin})
            for fmt, (w, h) in {'post': (1080, 1350), 'historia': (1080, 1920)}.items():
                im = tarjetas(w, h, f'Este finde · {dias[0].day}-{dias[-1].day} de {["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"][dias[-1].month - 1]}', f'Música y fiesta en {nom}', filas, 'Datos de la agenda oficial · más planes en')
                im.save(os.path.join(OUT, f'finde-{c}-{fmt}.jpg'), quality=88)
            piezas.append({'c': c, 'nom': nom, 'tipo': 'finde', 'titulo': f'Este finde en {nom}', 'imgs': [f'finde-{c}-post.jpg', f'finde-{c}-historia.jpg'],
                           'texto': f"🌙 Este finde en {nom}: música y fiesta\n\n" + '\n'.join(texto[:8]) + f"\n\nOrganiza tu noche (cena, copas, fiesta y dónde dormir) en {WEB}\nFuente: {', '.join(fuentes_ev)}\n\n#ModoNoche {tag} #planes{norm(nom)} #findesemana #ociónocturno #fiesta"})
        # --- discotecas destacadas
        pl = os.path.join(PUB, 'locales', f'{c}.json')
        els = json.load(open(pl, encoding='utf-8')).get('elements', []) if os.path.exists(pl) else []
        dest = [e for e in els if (e.get('tags') or {}).get('mn:motivo')]
        dest.sort(key=lambda e: (e['tags'].get('mn:top') != 'yes', e['tags'].get('name', '')))
        if len(dest) >= 3:
            filas, texto = [], []
            for e in dest:
                t = e['tags']; top = t.get('mn:top') == 'yes'
                et = 'TOP MUNDIAL' if top else 'NUEVA' if t.get('mn:nueva') else 'DESTACADA'
                filas.append((et, t['name'], t['mn:motivo']))
                texto.append(f"• {t['name']}: {t['mn:motivo']}")
            for fmt, (w, h) in {'post': (1080, 1350), 'historia': (1080, 1920)}.items():
                im = tarjetas(w, h, 'Ranking MODO NOCHE', f'Discotecas top de {nom}', filas, 'Según rankings, guías y prensa · ficha de cada una en')
                im.save(os.path.join(OUT, f'top-{c}-{fmt}.jpg'), quality=88)
            piezas.append({'c': c, 'nom': nom, 'tipo': 'top', 'titulo': f'Discotecas top de {nom}', 'imgs': [f'top-{c}-post.jpg', f'top-{c}-historia.jpg'],
                           'texto': f"🔥 Las discotecas top de {nom}\n\n" + '\n'.join(texto[:10]) + f"\n\nHorarios, cómo llegar y planes cerca en {WEB}\n\n#ModoNoche {tag} #discotecas{norm(nom)} #ociónocturno #clubbing"})
    json.dump({'gen': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'finde': [d.isoformat() for d in dias], 'piezas': piezas}, open(os.path.join(OUT, 'piezas.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    tarjetas_html = ''.join(f'''<article><h2>{E(p['titulo'])}</h2><div class="imgs">{''.join(f'<a href="{i}" download><img src="{i}" loading="lazy" alt="{E(p["titulo"])}"><span>Descargar {"historia" if "historia" in i else "publicación"}</span></a>' for i in p['imgs'])}</div>
<textarea readonly rows="7">{E(p['texto'])}</textarea><button onclick="navigator.clipboard.writeText(this.previousElementSibling.value).then(()=>{{this.textContent='Copiado ✓'}})">Copiar texto</button></article>''' for p in piezas)
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>MODO NOCHE · contenido para redes</title><style>body{{margin:0;background:#07070B;color:#F5F3FF;font:16px/1.5 system-ui,sans-serif;padding:16px}}h1{{font-size:22px}}article{{background:#101019;border:1px solid #29283A;border-radius:16px;padding:14px;margin:0 0 16px}}
h2{{font-size:18px;margin:0 0 10px;color:#C7FF4A}}.imgs{{display:flex;gap:10px;overflow-x:auto}}.imgs a{{flex:none;width:46%;max-width:260px;color:#22D3EE;font-size:13px;text-decoration:none}}.imgs img{{width:100%;border-radius:10px;display:block;margin-bottom:4px}}
textarea{{width:100%;box-sizing:border-box;margin-top:10px;background:#07070B;color:#F5F3FF;border:1px solid #29283A;border-radius:10px;padding:8px;font:13px/1.4 system-ui}}button{{margin-top:6px;padding:10px 14px;border-radius:10px;border:0;background:#A855F7;color:#fff;font-weight:700}}</style></head>
<body><h1>MODO NOCHE · contenido para redes</h1><p>Actualizado cada día. Finde del {dias[0].day}/{dias[0].month} al {dias[-1].day}/{dias[-1].month}. Mantén pulsada una imagen para guardarla o toca «Descargar». Solo eventos reales de agendas oficiales y discotecas con fuente.</p>{tarjetas_html or '<p>Hoy no hay piezas: faltan eventos o discotecas destacadas.</p>'}</body></html>''')
    print('redes:', len(piezas), 'piezas', flush=True)


if __name__ == '__main__':
    sys.exit(main())
