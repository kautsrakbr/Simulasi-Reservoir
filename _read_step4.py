import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('workflow.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

cell = next(c for c in nb['cells'] if c.get('id') == 'aef0691a')
src = ''.join(cell['source'])
print(src)
