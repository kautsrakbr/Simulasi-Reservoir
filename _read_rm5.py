import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('manual_engine/run_manual.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Read compute_residual and accumulation for well terms
start = src.find('def compute_residual')
print('--- compute_residual ---')
print(src[start:start+800])

# Read compute_accumulation for well
start2 = src.find('def compute_accumulation')
print('\n--- compute_accumulation ---')
print(src[start2:start2+1200])

# Read init_state for well cell info
start3 = src.find('def init_state')
print('\n--- init_state ---')
print(src[start3:start3+800])

# Read build_grid for well assignment
start4 = src.find('def build_grid')
print('\n--- build_grid (partial) ---')
print(src[start4:start4+2000])
