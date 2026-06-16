import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manual_engine/run_manual.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find cell_props and related functions
import re
# Find function definitions
funcs = [(m.start(), m.group()) for m in re.finditer(r'^def \w+', src, re.MULTILINE)]
for pos, name in funcs:
    print(f'  {name} at char {pos}')

print('\n--- CONSTANTS / WELL CONFIG ---')
for line in src.split('\n'):
    if any(k in line for k in ['WELL', 'PRODUCER', 'INJECTOR', 'NX', 'NY', 'NZ', 'P_REF', 'DT_', 'POROSITY', 'PERM']):
        if not line.strip().startswith('#'):
            print(line)
