import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('workflow.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cid in ['bc61b555', '85710352']:
    cell = next((c for c in nb['cells'] if c.get('id') == cid), None)
    if cell:
        src = ''.join(cell.get('source', []))
        print(f'=== CELL {cid} ===')
        print(src[:3000])
        print()
