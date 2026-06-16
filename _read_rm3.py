import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manual_engine/run_manual.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Read full cell_props return
start = src.find('def cell_props')
print('--- cell_props full ---')
print(src[start:start+2000])

# Read well / RSO section
print('\n--- RSO / run_timestep well handling ---')
start2 = src.find('def run_timestep')
print(src[start2:start2+1500])
