import re

with open('scripts/build_full_report.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
for line in lines:
    # If line is inside a python string literal and has unescaped quotes like <b>"AI- or Temple)"</b>
    if '<b>"AI-' in line:
        line = line.replace('<b>"AI-', '<b>&quot;AI-')
    if 'Temple)"</b>' in line:
        line = line.replace('Temple)"</b>', 'Temple)&quot;</b>')
    if '"Jnana Sangama"' in line:
        line = line.replace('"Jnana Sangama"', '&quot;Jnana Sangama&quot;')
    fixed_lines.append(line)

with open('scripts/build_full_report.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('Fixed quotes in build_full_report.py')
