#!/usr/bin/env python3
"""Emails de contacto de empresa de restaurantes, bares, discotecas, salas y alojamientos (OpenStreetMap) de UN país.
Solo lo que el propio negocio publica en OpenStreetMap (email / contact:email). Se descartan los buzones de soporte,
incidencias, reclamaciones, facturación, empleo, privacidad, etc. NO se publica en la web: sale como archivo privado del proceso.
Uso: PAIS=ES python3 herramientas/contactos.py   ->  contactos/PAIS.csv"""
import csv, json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar import interesa, centro, km, UA, log
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GEOFABRIK = {'ES': ['europe/spain', 'africa/canary-islands'], 'PT': ['europe/portugal'], 'IT': ['europe/italy'], 'FR': ['europe/france'], 'DE': ['europe/germany'],
             'NL': ['europe/netherlands'], 'BE': ['europe/belgium'], 'GB': ['europe/united-kingdom'], 'IE': ['europe/ireland-and-northern-ireland'],
             'GR': ['europe/greece'], 'HR': ['europe/croatia'], 'AT': ['europe/austria'], 'CH': ['europe/switzerland']}
PAISES = {'ES': 'España', 'PT': 'Portugal', 'IT': 'Italia', 'FR': 'Francia', 'DE': 'Alemania', 'NL': 'Países Bajos', 'BE': 'Bélgica', 'GB': 'Reino Unido',
          'IE': 'Irlanda', 'GR': 'Grecia', 'HR': 'Croacia', 'AT': 'Austria', 'CH': 'Suiza'}
EMAIL = re.compile(r'^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')
# buzones que no son de contacto comercial (soporte, incidencias, reclamaciones, facturas, empleo, privacidad, sistemas…)
NO = re.compile(r'(support|soporte|suporte|supporto|assistenza|helpdesk|servicedesk|incidenc|incident|reclama|complaint|claims?\b|noreply|no-reply|donotreply|do-not-reply|'
                r'abuse|privacy|privacidad|privacidade|datenschutz|dpo|rgpd|gdpr|lopd|legal|factura|billing|invoice|rechnung|accounting|contabilidad|administracion|'
                r'jobs?\b|empleo|trabaj|rrhh|recursos|careers?|karriere|bewerbung|candidat|\bcv\b|ticketing|tickets?\b|entradas|refund|devoluc|reembolso|'
                r'webmaster|postmaster|hostmaster|mailer|bounce|newsletter|unsubscribe)', re.I)
TIPOS = {'nightclub': 'Discoteca', 'bar': 'Bar', 'pub': 'Pub', 'music_venue': 'Sala de conciertos', 'concert_hall': 'Sala de conciertos', 'events_venue': 'Sala de eventos',
         'theatre': 'Sala de conciertos', 'restaurant': 'Restaurante', 'hotel': 'Hotel', 'hostel': 'Albergue', 'guest_house': 'Hostal o pensión', 'apartment': 'Apartamento turístico', 'motel': 'Motel'}

def ciudades(pais):
    if pais == 'ES':
        return [(m[0], m[1], m[2], m[3]) for m in json.load(open(os.path.join(RAIZ, 'datos', 'municipios.json'), encoding='utf-8'))['municipios'] if m[2] is not None]
    return [(c[0], c[1], c[2], c[3]) for c in json.load(open(os.path.join(RAIZ, 'datos', 'ciudades.json'), encoding='utf-8'))['ciudades'] if c[5] == pais]

def main():
    pais = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('PAIS', '')).upper()
    if pais not in GEOFABRIK: log('País no válido'); return 1
    trab = os.path.join(RAIZ, '.trabajo_contactos', pais); os.makedirs(trab, exist_ok=True)
    filtrados = []
    for i, ruta in enumerate(GEOFABRIK[pais]):
        pbf = os.path.join(trab, f'{i}.osm.pbf'); url = f'https://download.geofabrik.de/{ruta}-latest.osm.pbf'
        log('Descargando', url); subprocess.run(['curl', '-fsSL', '--retry', '4', '--retry-delay', '20', '-A', UA, '-o', pbf, url], check=True)
        f = os.path.join(trab, f'{i}.f.osm.pbf')
        subprocess.run(['osmium', 'tags-filter', '--overwrite', '-o', f, pbf, 'nwr/email', 'nwr/contact:email'], check=True); os.remove(pbf); filtrados.append(f)
    unido = os.path.join(trab, 'unido.osm.pbf'); subprocess.run(['osmium', 'merge', '--overwrite', '-o', unido, *filtrados], check=True)
    geo = os.path.join(trab, 'c.geojsonseq'); subprocess.run(['osmium', 'export', '--overwrite', '-f', 'geojsonseq', '-o', geo, unido], check=True)
    cs = ciudades(pais); rej = {}
    for c in cs: rej.setdefault((int(c[2] * 10), int(c[3] * 10)), []).append(c)
    def ciudad(lat, lng):
        best, bd = None, 15.0
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for c in rej.get((int(lat * 10) + a, int(lng * 10) + b), []):
                    d = km(lat, lng, c[2], c[3])
                    if d < bd: best, bd = c, d
        if best: return best[1]
        for c in cs:   # sin ninguna a menos de 15 km: la más cercana
            d = km(lat, lng, c[2], c[3])
            if d < bd + 50: best, bd = c, d
        return best[1] if best else ''
    filas, vistos, desc = [], set(), 0
    for linea in open(geo, encoding='utf-8'):
        linea = linea.strip().lstrip('\x1e')
        if not linea: continue
        try: feat = json.loads(linea)
        except ValueError: continue
        p, g = feat.get('properties') or {}, feat.get('geometry') or {}
        k = interesa(p)
        if not k: continue
        ce = centro(g)
        if not ce: continue
        for em in re.split(r'[;,\s]+', ' '.join(str(p.get(x) or '') for x in ('email', 'contact:email'))):
            em = em.strip().strip('.').lower().replace('mailto:', '')
            if not EMAIL.match(em): continue
            if NO.search(em.split('@')[0]): desc += 1; continue
            if em in vistos: continue
            vistos.add(em)
            tipo = TIPOS.get(p.get('amenity') or p.get('tourism'), k)
            filas.append([PAISES[pais], ciudad(ce[1], ce[0]), tipo, p.get('name', ''), em, p.get('website') or p.get('contact:website') or '',
                          p.get('phone') or p.get('contact:phone') or '', p.get('instagram') or p.get('contact:instagram') or ''])
    os.makedirs(os.path.join(RAIZ, 'contactos'), exist_ok=True)
    filas.sort(key=lambda r: (r[1], r[2], r[3]))
    with open(os.path.join(RAIZ, 'contactos', f'{pais}.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['país', 'ciudad', 'tipo', 'nombre', 'email', 'web', 'teléfono', 'instagram']); w.writerows(filas)
    log(pais, 'emails de empresa:', len(filas), '| descartados (soporte, incidencias…):', desc)
    return 0

if __name__ == '__main__':
    sys.exit(main())
