import openpyxl, json, io, re
from PIL import Image
SRC = '/Users/piano/Downloads/womens_clothing_catalog_standardized.xlsx'
wb = openpyxl.load_workbook(SRC)
ws = wb['Catalog']
rows = list(ws.iter_rows(min_row=2, values_only=True))
img_by_row = {img.anchor._from.row: img for img in ws._images}
items = []
for i, r in enumerate(rows):
    retailer, brand, name, cat, color, occ, price, cdetail, catdetail, url, _ = r
    iid = i + 1
    img = img_by_row.get(i + 1)
    thumb = None
    if img:
        im = Image.open(io.BytesIO(img._data())).convert('RGB')
        thumb = f'images/thumbs/{iid:03d}.jpg'
        im.save(thumb, 'JPEG', quality=88)
    items.append(dict(
        id=iid, retailer=retailer, brand=brand, name=name.strip(), category=cat, color=color,
        occasions=[o.strip() for o in occ.split(',')], price=price,
        colorDetail=cdetail, categoryDetail=catdetail, url=url, thumb=thumb, image=None))
json.dump(items, open('build/items_raw.json', 'w'), indent=1, ensure_ascii=False)
print(len(items), 'items;', sum(1 for x in items if x['thumb']), 'thumbs')
