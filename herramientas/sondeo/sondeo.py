"""Sondeo: descargar miniaturas candidatas (Wikimedia Commons) para revisarlas."""
import os, json, urllib.request
os.makedirs('salida', exist_ok=True)
UA = {'User-Agent': 'MODO-NOCHE-sondeo (modonochesoporte@gmail.com)'}
U = ["https://thumb.wikimedia.org/wikipedia/commons/thumb/8/88/Cleveland_Hostel_room.jpg/960px-Cleveland_Hostel_room.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/90/DSC_8570_A_cozy_elegantly_decorated_bedroom_with_a_tufted_headboard_soft_blue_linens_ornate_gold-framed_artwork_and_a_draped_ceiling_chandelier_creating_a_romantic_boutique-hotel_atmosphere.jpg/960px-thumbnail.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3e/DZ6_0461_Cozy_neatly_made_hotel_room_with_a_king_bed_soft_pillows_bedside_lamps_and_calming_neutral_decor.jpg/960px-DZ6_0461_Cozy_neatly_made_hotel_room_with_a_king_bed_soft_pillows_bedside_lamps_and_calming_neutral_decor.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail"]
for i, u in enumerate(U):
    open(f'salida/foto{i}.jpg', 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
json.dump({'ok': len(U)}, open('salida/publicado.json', 'w'))
