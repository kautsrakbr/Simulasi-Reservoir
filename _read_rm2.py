import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manual_engine/run_manual.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Read cell_props and well-related constants
start = src.find('def cell_props')
print('--- cell_props ---')
print(src[start:start+1200])

print('\n--- WELL config ---')
for line in src.split('\n'):
    if any(k in line.upper() for k in ['WELL', 'PRODUCER', 'INJECTOR', 'PWF', 'WI', 'Q_WELL', 'WELL_CELL', 'WELL_IDX', 'RSO', 'REFERENCE_DEPTH']):
        print(line)
