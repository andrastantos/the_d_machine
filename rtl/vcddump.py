#!/usr/bin/python3
# Prints selected VCD signals as a table, one row per change.
#
# Usage: vcddump.py <file.vcd> <start time> <end time> <signal>...
#
# Signals are matched as suffixes of their full dotted scope path, for
# example: vcddump.py tb_fetch_av.vcd 700 800 mmu.av sequencer.intdis dut.bus_rd

import sys

path, t0, t1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
want = sys.argv[4:]
ids, scope = {}, []
f = open(path)
for line in f:
    tok = line.split()
    if not tok: continue
    if tok[0] == '$scope': scope.append(tok[2])
    elif tok[0] == '$upscope': scope.pop()
    elif tok[0] == '$var':
        full = '.'.join(scope + [tok[4]])
        for w in want:
            if full.endswith(w): ids.setdefault(tok[3], []).append(w)
    elif tok[0] == '$enddefinitions': break
vals, t = {w: 'x' for w in want}, 0
def show():
    print(f"{t:5}: " + "  ".join(f"{w.split('.')[-1]}={vals[w]}" for w in want))
last = None
for line in f:
    line = line.strip()
    if not line: continue
    if line[0] == '#':
        if t0 <= t <= t1:
            cur = tuple(vals.values())
            if cur != last: show(); last = cur
        t = int(line[1:])
        if t > t1: break
        continue
    if line[0] in 'bB':
        v, i = line[1:].split()
    else:
        v, i = line[0], line[1:]
    for w in ids.get(i, []):
        vals[w] = hex(int(v, 2)) if line[0] in 'bB' and set(v) <= {'0','1'} else v
