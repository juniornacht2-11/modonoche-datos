#!/usr/bin/env python3
"""Descarga las fotos candidatas de Pexels (licencia Pexels: uso gratuito, también comercial) a fotos/candidatas/."""
import os, re, sys, urllib.request
D = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(D, 'candidatas'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r: return r.read(), r.headers.get('content-type', '')
ok = fail = 0; informe = []
for linea in open(os.path.join(D, 'candidatas.txt'), encoding='utf-8'):
    if not linea.strip() or linea.startswith('#'): continue
    hueco, pid, *desc = linea.split(); dst = os.path.join(OUT, f'{hueco}__{pid}.jpg')
    if os.path.exists(dst): ok += 1; continue
    urls = [f'https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w=1400']
    err = ''
    for u in urls:
        try:
            b, ct = get(u)
            if 'image' in ct and len(b) > 5000: open(dst, 'wb').write(b); ok += 1; err = ''; break
            err = f'no es imagen ({ct})'
        except Exception as ex: err = str(ex)
    else:
        # nombres de archivo nuevos: se busca la imagen en la página de la foto
        try:
            html, _ = get(f'https://www.pexels.com/photo/{pid}/')
            m = re.search(rb'https://images\.pexels\.com/photos/%s/[^"?\s]+\.(?:jpe?g|png)' % pid.encode(), html)
            if m:
                b, ct = get(m.group(0).decode() + '?auto=compress&cs=tinysrgb&w=1400')
                if 'image' in ct: open(dst, 'wb').write(b); ok += 1; err = ''
        except Exception as ex: err += ' | página: ' + str(ex)
    if err: fail += 1; informe.append(f'{hueco} {pid}: {err}')
print('descargadas', ok, 'fallidas', fail); print('\n'.join(informe))
open(os.path.join(OUT, 'informe.txt'), 'w').write(f'descargadas {ok} fallidas {fail}\n' + '\n'.join(informe))
