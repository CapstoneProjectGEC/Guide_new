with open('scripts/build_full_report.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('\u201c', '"')
text = text.replace('\u201d', '"')
text = text.replace('\u2018', "'")
text = text.replace('\u2019', "'")
text = text.replace('\u2013', '-')
text = text.replace('\u2014', '--')

with open('scripts/build_full_report.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Sanitized build_full_report.py successfully!')
