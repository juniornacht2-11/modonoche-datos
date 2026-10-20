"""Sondeo: ejecutar la agenda completa y guardar el índice y las muestras (para comprobar las fuentes nuevas)."""
import os, subprocess, shutil, json
os.makedirs('salida', exist_ok=True)
r = subprocess.run(['python3', 'herramientas/eventos.py'], capture_output=True, text=True, timeout=1500, env={**os.environ})
open('salida/sondeo.txt', 'w').write(r.stdout[-6000:] + '\n---\n' + r.stderr[-4000:])
ix = json.load(open('publico/eventos/indice.json'))
json.dump({'fuentes': ix['fuentes'], 'n_municipios': len(ix['municipios']), 'algunos': {k: ix['municipios'].get(k) for k in ['08019', '17079', '43148', '25120', '47186', '37274', '33024', '28079', '48020']}}, open('salida/eventos_indice.json', 'w'), ensure_ascii=False, indent=1)
shutil.copy('publico/eventos/_muestras.json', 'salida/muestras.json')
for c in ['08019', '47186']:
    if os.path.exists(f'publico/eventos/{c}.json'):
        e = json.load(open(f'publico/eventos/{c}.json'))['eventos']
        json.dump([x for x in e if 'Catalunya' in x['f'] or 'Castilla' in x['f']][:8], open(f'salida/ej_{c}.json', 'w'), ensure_ascii=False, indent=1)
