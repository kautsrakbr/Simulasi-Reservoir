import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manual_engine/run_manual.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Find RSO and well handling in residual/flux
print('--- Lines with RSO/WELL/PRODUCER/INJECTOR ---')
for i, line in enumerate(src.split('\n'), 1):
    if any(k in line.upper() for k in ['RSO', 'WELL', 'PRODUCER', 'INJEC', 'Q_O', 'Q_W', 'Q_G', 'PWF', 'WI_', 'PVT_RSO']):
        print(f'L{i}: {line}')

print('\n--- Rso from PVT_BO (first 50 lines of constants) ---')
for i, line in enumerate(src.split('\n')[:100], 1):
    if 'PVT' in line or 'ROCK' in line:
        print(f'L{i}: {line}')
