"""Sondeo: ¿están libres estos dominios? (RDAP y DNS públicos; solo lectura)."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)', 'Accept': 'application/rdap+json, application/json'}
def st(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40); return r.status, r.read(400).decode('utf-8', 'replace')
    except urllib.error.HTTPError as e: return e.code, ''
    except Exception as e: return None, str(e)[:120]
out = {}
nombres = ['modonoche', 'modo-noche', 'modonocheapp', 'modonoches']
tlds = ['es', 'com', 'app', 'club', 'net', 'eu']
RDAP = {'com': 'https://rdap.verisign.com/com/v1/domain/', 'net': 'https://rdap.verisign.com/net/v1/domain/', 'app': 'https://pubapi.registry.google/rdap/domain/',
        'club': 'https://rdap.nic.club/domain/', 'eu': 'https://rdap.eurid.eu/domain/'}
for n in nombres:
    for t in tlds:
        d = f'{n}.{t}'; res = {}
        if t in RDAP:
            c, _ = st(RDAP[t] + d); res['rdap'] = c   # 404 = no registrado
        c, body = st('https://dns.google/resolve?type=NS&name=' + d)
        try: j = json.loads(body) if c == 200 else {}
        except Exception: j = {}
        res['dns_status'] = j.get('Status'); res['ns'] = [a.get('data') for a in j.get('Answer') or []][:2]   # Status 3 = NXDOMAIN (no existe)
        out[d] = res
json.dump(out, open('salida/publicado.json', 'w'), ensure_ascii=False, indent=1)
