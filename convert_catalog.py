import csv, json, os
src = 'data/catalog.csv'
dst = 'backend/parts-search/data/catalog.json'
rows = list(csv.DictReader(open(src, encoding='utf-8')))
out = []
seen = set()
for r in rows:
    sku = r['sku']
    if sku in seen:
        raise SystemExit(f'Duplicate SKU {sku}')
    seen.add(sku)
    size = f"{r['diameter_mm']}x{r['length_mm']}" if r.get('diameter_mm') and r.get('length_mm') else ''
    rec = dict(r)
    rec['size'] = size
    out.append(rec)
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)
print('Converted', len(out), 'parts, unique SKUs:', len(seen))
