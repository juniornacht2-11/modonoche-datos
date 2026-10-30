#!/usr/bin/env python3
"""Busca el email de empresa en la PROPIA web oficial de cada local (la que figura en OpenStreetMap).
Visita la portada y, si hace falta, su página de contacto / aviso legal (Kontakt, Impressum, contatti, mentions légales…).
- Respeta robots.txt, se identifica y no repite dominios (cadenas con muchas sucursales: una visita).
- Solo emails del dominio de la propia web o de correo gratuito (gmail, hotmail…) y nunca de soporte, incidencias, entradas, empleo, etc.
Entrada: contactos/PAIS-webs.csv   Salida: añade filas a contactos/PAIS.csv (columna «fuente»)."""
import csv, os, re, sys, time, threading, urllib.parse, urllib.request, urllib.robotparser, ssl, html
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contactos import NO, EMAIL
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
UA = 'MODO-NOCHE-contacto/1.0 (guía de ocio nocturno; busca el email de contacto publicado por el propio local; https://modonoche.juniornacht2.workers.dev)'
GRATIS = {'gmail.com', 'hotmail.com', 'hotmail.es', 'hotmail.it', 'hotmail.fr', 'outlook.com', 'outlook.es', 'yahoo.com', 'yahoo.es', 'yahoo.fr', 'yahoo.it',
          'yahoo.de', 'yahoo.co.uk', 'live.com', 'icloud.com', 'gmx.de', 'gmx.net', 'web.de', 't-online.de', 'libero.it', 'virgilio.it', 'orange.fr', 'free.fr',
          'wanadoo.fr', 'sapo.pt', 'btinternet.com', 'telefonica.net', 'aol.com', 'protonmail.com', 'me.com', 'msn.com', 'googlemail.com', 'eircom.net', 'gmx.at', 'bluewin.ch'}
CONTACTO = re.compile(r'(contact|contacto|kontakt|contatti|contatto|contactos|impressum|imprint|mentions|aviso-legal|legal-notice|about|nosotros|chi-siamo|ueber-uns|uber-uns|reserv|booking|prenot|info)', re.I)
MAILRE = re.compile(r'[A-Za-z0-9._%+\-]+\s*(?:@|\[at\]|\(at\)|\s+at\s+|&#64;|%40)\s*[A-Za-z0-9\-]+(?:\s*(?:\.|\[dot\]|\(dot\))\s*[A-Za-z0-9\-]+)+', re.I)
BASURA = re.compile(r'\.(png|jpe?g|gif|webp|svg|css|js)$|sentry|wixpress|example\.|domain\.|email\.com$|yourdomain|tudominio|@2x', re.I)
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE   # muchas webs de bares tienen el certificado caducado
robots, lock = {}, threading.Lock()

def base(dom): return re.sub(r'^www\d?\.', '', dom.lower())

def permitido(url):
    p = urllib.parse.urlsplit(url); k = p.scheme + '://' + p.netloc
    with lock:
        rp = robots.get(k)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(k + '/robots.txt', headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=8, context=CTX) as r: rp.parse(r.read(200000).decode('utf-8', 'ignore').splitlines())
        except Exception:
            rp.parse([])   # sin robots.txt: se permite
        with lock: robots[k] = rp
    return rp.can_fetch(UA, url)

def leer(url):
    if not permitido(url): return '', url
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,*/*;q=0.5', 'Accept-Language': 'es,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=10, context=CTX) as r:
        if 'html' not in (r.headers.get('content-type') or 'text/html'): return '', r.geturl()
        return r.read(800000).decode(r.headers.get_content_charset() or 'utf-8', 'ignore'), r.geturl()

def emails(texto, dom):
    t = html.unescape(texto).replace('%40', '@')
    out = []
    for m in MAILRE.findall(t):
        e = re.sub(r'\s*(\[at\]|\(at\)|\s+at\s+|&#64;)\s*', '@', m, flags=re.I); e = re.sub(r'\s*(\[dot\]|\(dot\))\s*', '.', e, flags=re.I)
        e = re.sub(r'\s+', '', e).strip('.').lower()
        if not EMAIL.match(e) or BASURA.search(e) or NO.search(e.split('@')[0]): continue
        d = e.split('@')[1]
        if not (base(d) == base(dom) or base(d).endswith('.' + base(dom)) or base(dom).endswith('.' + base(d)) or d in GRATIS): continue
        if e not in out: out.append(e)
    # primero los de reservas / info / contacto
    pref = re.compile(r'^(reserv|booking|prenot|info|contact|kontakt|contatti|hola|hello|ciao|bonjour|eventos|events|direccion|gerencia|management|office|comercial|marketing)')
    return sorted(out, key=lambda e: (0 if pref.match(e) else 1, len(e)))

def buscar(web):
    try:
        if not re.match(r'^https?://', web): web = 'http://' + web
        dom = urllib.parse.urlsplit(web).netloc.split(':')[0]
        if not dom or re.search(r'(facebook|instagram|tripadvisor|google|booking|airbnb|thefork|eltenedor|yelp|wix\.com$|linktr)', dom): return []
        portada, final = leer(web)
        es = emails(portada, dom)
        if es: return es
        links = []
        for h in re.findall(r'href=["\']([^"\'#]+)', portada)[:400]:
            u = urllib.parse.urljoin(final, h)
            if urllib.parse.urlsplit(u).netloc == urllib.parse.urlsplit(final).netloc and CONTACTO.search(urllib.parse.urlsplit(u).path) and u not in links: links.append(u)
        for u in links[:3]:
            try:
                t, _ = leer(u); es = emails(t, dom)
                if es: return es
            except Exception:
                continue
    except Exception:
        return []
    return []

def main():
    pais = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('PAIS', '')).upper()
    ent = os.path.join(RAIZ, 'contactos', f'{pais}-webs.csv')
    if not os.path.exists(ent): print('sin lista de webs'); return 0
    filas = list(csv.reader(open(ent, encoding='utf-8')))[1:]
    limite = time.time() + float(os.environ.get('MINUTOS', '300')) * 60
    por_dom = {}
    for f in filas:
        d = base(urllib.parse.urlsplit(f[4] if re.match(r'^https?://', f[4]) else 'http://' + f[4]).netloc.split(':')[0])
        por_dom.setdefault(d, []).append(f)
    doms = list(por_dom)
    print(pais, 'webs a visitar:', len(doms), 'dominios de', len(filas), 'locales', flush=True)
    res = {}
    def tarea(d):
        if time.time() > limite: return d, None
        return d, buscar(por_dom[d][0][4])
    hechos = 0
    with ThreadPoolExecutor(max_workers=48) as ex:
        for d, es in ex.map(tarea, doms):
            hechos += 1
            if es: res[d] = es
            if hechos % 2000 == 0: print(' ', hechos, 'visitadas,', len(res), 'con email', flush=True)
    sal = os.path.join(RAIZ, 'contactos', f'{pais}.csv')
    ya = {r[4] for r in list(csv.reader(open(sal, encoding='utf-8')))[1:]} if os.path.exists(sal) else set()
    nuevas = []
    for d, es in res.items():
        e = es[0]
        if e in ya: continue
        ya.add(e)
        for f in por_dom[d][:1]:   # una fila por web (las cadenas con muchas sucursales comparten email)
            nuevas.append([f[0], f[1], f[2], f[3], e, f[4], f[5], f[6]])
    with open(sal, 'a', newline='', encoding='utf-8') as fh:
        csv.writer(fh).writerows(nuevas)
    print(pais, 'emails encontrados en las webs oficiales:', len(nuevas), '| sin terminar por tiempo:', sum(1 for d in doms if d not in res) if time.time() > limite else 0)
    return 0

if __name__ == '__main__':
    sys.exit(main())
