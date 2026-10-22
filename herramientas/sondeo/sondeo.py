"""Sondeo: buscar agendas de eventos en datos.gob.es y probar sus descargas (solo lectura)."""
import os, json, urllib.request, urllib.parse
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)', 'Accept': 'application/json'}
def raw(u, n=400000):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read(n)
    except Exception as e: return ('ERROR ' + str(e)[:150]).encode()
out = {'catalogo': [], 'pruebas': {}}
vistos = set()
for t in ['agenda', 'eventos', 'actividades culturales', 'agenda cultural', 'conciertos', 'fiestas']:
    for pag in range(3):
        u = 'https://datos.gob.es/apidata/catalog/dataset/title/' + urllib.parse.quote(t) + f'.json?_pageSize=50&_page={pag}'
        try: j = json.loads(raw(u, 5_000_000))
        except Exception as e: out['catalogo'].append({'err': str(e)[:100], 'u': u}); break
        items = j.get('result', {}).get('items', [])
        for it in items:
            about = it.get('_about')
            if about in vistos: continue
            vistos.add(about)
            tit = it.get('title'); tit = tit if isinstance(tit, str) else ' / '.join(x.get('_value', '') for x in (tit if isinstance(tit, list) else [tit]) if isinstance(x, dict))
            dist = it.get('distribution') or []; dist = dist if isinstance(dist, list) else [dist]
            urls = []
            for d in dist:
                if isinstance(d, dict):
                    f = d.get('format'); f = f.get('value') if isinstance(f, dict) else f
                    urls.append([d.get('accessURL'), f])
            pub = it.get('publisher'); pub = pub.get('_about') if isinstance(pub, dict) else pub
            mod = it.get('modified')
            out['catalogo'].append({'t': tit[:120], 'pub': str(pub)[-12:], 'mod': str(mod)[:25], 'urls': urls[:6]})
        if len(items) < 50: break
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
