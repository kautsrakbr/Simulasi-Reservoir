import json

NB = r"c:\My Workspaces\venv.Python\SIMULASI RESERVOIR\workflow.ipynb"
BEL = '\x07'

with open(NB, 'r', encoding='utf-8') as f:
    nb = json.load(f)

CELL_ID = '5f2c10c1'
patched = False

for cell in nb['cells']:
    if cell.get('id') != CELL_ID:
        continue

    src = ''.join(cell['source'])
    count_before = src.count(BEL)
    print(f"BEL chars before: {count_before}")

    # BEL + 'lpha' came from \alpha -> \a (BEL) + lpha in non-raw strings
    fixed = src.replace(BEL + 'lpha', r'\alpha')
    count_after = fixed.count(BEL)
    print(f"BEL chars after:  {count_after}")

    # Rebuild as list-of-lines (Jupyter format: each line ends with \n except last)
    lines = fixed.split('\n')
    src_list = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    cell['source'] = src_list

    # Show the fixed lines
    for i, l in enumerate(lines):
        if r'\alpha' in l and 'BEL' not in l:
            print(f"  OK L{i+1}: {l}")
    patched = True
    break

if not patched:
    print("Cell not found!")
else:
    with open(NB, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("Saved OK.")
