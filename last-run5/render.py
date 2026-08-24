import sys
import re
from pathlib import Path

src = Path('morning_早上八点.md').read_text(encoding='utf-8')

html = ['<!doctype html><html><head><meta charset="utf-8"><title>AI 早报</title>',
        '<style>',
        'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:780px;margin:32px auto;padding:0 24px;color:#1a1a1a;line-height:1.7}',
        'h1{font-size:24px;border-bottom:2px solid #2563eb;padding-bottom:12px;margin-bottom:8px}',
        'h2{font-size:18px;color:#2563eb;margin-top:28px;margin-bottom:12px}',
        'p{margin:6px 0}',
        'strong{color:#111}',
        'blockquote{border-left:3px solid #93c5fd;margin:8px 0;padding:0 14px;color:#475569;font-size:14px}',
        'a{color:#2563eb;text-decoration:none}',
        '.meta{color:#94a3b8;font-size:13px;margin-bottom:24px}',
        '</style></head><body>']

lines = src.split('\n')
in_list = False
for line in lines:
    if not line.strip():
        html.append('')
        continue
    if line.startswith('# '):
        html.append(f'<h1>{line[2:]}</h1>')
        html.append('<p class="meta">2026-08-18 · 15 条 importance ≥ 6 · 由 DeepSeek + PushPlus 自动生成</p>')
    elif line.startswith('## '):
        html.append(f'<h2>{line[3:]}</h2>')
    elif line.startswith('**['):
        m = re.match(r'\*\*\[(\d+)\]\s+(.+?)\*\*', line)
        if m:
            score, title = m.group(1), m.group(2)
            html.append(f'<p><strong>[{score}] {title}</strong></p>')
    elif line.startswith('> '):
        html.append(f'<blockquote>{line[2:]}</blockquote>')
    elif line.startswith('来源：'):
        html.append(f'<p style="font-size:13px;color:#64748b">{line}</p>')
    elif line.startswith('[阅读原文]'):
        html.append(f'<p style="font-size:13px">{line}</p>')

html.append('</body></html>')
Path('morning_早上八点.html').write_text('\n'.join(html), encoding='utf-8')
print('OK: morning_早上八点.html')
