"""Measure the widest line inside markdown code fences, in real characters.

Box-drawing glyphs (─ │ ┌ └ etc.) are 3 bytes each in UTF-8 but 1 display
column wide, so `awk length` over-reports widths by up to 3x. This script
counts code points instead, which is what matters for monospace print width.
"""

import sys

path = sys.argv[1] if len(sys.argv) > 1 else "REPORT.md"
lines = open(path, encoding="utf-8").read().splitlines()

in_code = False
code_lines = []
for number, line in enumerate(lines, 1):
    if line.startswith("```"):
        in_code = not in_code
        continue
    if in_code:
        code_lines.append((number, line))

code_lines.sort(key=lambda pair: -len(pair[1]))

print(f"{path}: {len(code_lines)} lines inside code fences")
print("widest 8 (in CHARACTERS):")
for number, line in code_lines[:8]:
    print(f"  line {number:5d}: {len(line):3d} cols")

widest = len(code_lines[0][1])
print(f"\nmax = {widest} columns")

# A4 text column = 210mm - 18mm - 18mm = 174mm.
# Consolas advance width = 0.5498 em; 1pt = 0.352778mm.
print("\nConsolas fit at various sizes (174mm text column):")
for pt in (7.0, 7.5, 7.8, 8.0, 8.5):
    fits = 174 / (pt * 0.5498 * 0.352778)
    verdict = "OK" if widest <= fits else "CLIPPED"
    print(f"  {pt:4.1f}pt -> {fits:5.0f} cols fit   {verdict}")
