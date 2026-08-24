src = open('morning_20260818_162641.md', 'r', encoding='utf-8').read()
dst = src.replace('# AI 早报 · 08-18', '# AI 早报 · 早上八点', 1)
open('morning_早上八点.md', 'w', encoding='utf-8').write(dst)
print(open('morning_早上八点.md', 'r', encoding='utf-8').readline().strip())
