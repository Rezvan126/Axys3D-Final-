import json,re,sys
F,out=sys.argv[1],sys.argv[2]
rows=[];names={};seen=set()
def flat(c):
  if isinstance(c,str): return c
  return '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
for l in open(F):
  try: d=json.loads(l)
  except: continue
  t=d.get('type'); ts=d.get('timestamp','')[:16].replace('T',' ')
  if d.get('isSidechain') or d.get('isCompactSummary') or d.get('isMeta'): continue
  if t=='attachment' and d['attachment'].get('type')=='queued_command':
    txt=flat(d['attachment'].get('prompt')).strip()
    txt=re.sub(r'<(system-reminder|task-notification)>.*?</(system-reminder|task-notification)>','',txt,flags=re.S).strip()
    if txt and 'Stop hook' not in txt[:200] and txt not in seen:
      seen.add(txt); rows.append((ts,'Owner',txt))
    continue
  if t not in('user','assistant'): continue
  c=d['message']['content']; texts=[]
  if isinstance(c,str): texts=[c]
  else:
    for b in c:
      if b.get('type')=='text': texts.append(b['text'])
      elif b.get('type')=='tool_use': names[b['id']]=b['name']
      elif b.get('type')=='tool_result' and names.get(b['tool_use_id'])=='ArtifactComments':
        s=flat(b.get('content'))
        cur=None;buf=[]
        def flush():
          if cur and buf:
            body='\n'.join(buf).strip(); key=body
            if body and key not in seen and 'Claude' not in cur.split(',')[0]:
              seen.add(key); rows.append((ts,'Owner (artifact comment)',body))
        for line in s.split('\n'):
          m=re.match(r'^\s*\[(.+?)\]\s*$',line)
          if m and ('—' in m.group(1)):
            flush(); cur=m.group(1); buf=[]; continue
          m=re.match(r'^\s*[0-9a-f]{8}\| ?(.*)$',line)
          if m and cur is not None: buf.append(m.group(1))
          elif cur is not None and buf and not line.strip(): pass
          elif cur is not None and buf: flush(); cur=None; buf=[]
        flush()
  txt='\n'.join(texts).strip()
  if not txt: continue
  if t=='user':
    txt=re.sub(r'<(system-reminder|task-notification)>.*?</(system-reminder|task-notification)>','',txt,flags=re.S).strip()
    if not txt or txt.startswith('<local-command') or txt.startswith('<command-') or 'Stop hook feedback' in txt[:200] or txt.startswith('[Request interrupted') or txt in seen: continue
    seen.add(txt)
  rows.append((ts,'Owner' if t=='user' else 'Claude',txt))
with open(out,'w') as o:
  o.write("# Chat history backup\n\nThe owner's messages and artifact comments, plus Claude's replies, from the website build session (3–4 Nov 2026). Tool calls and file dumps are left out. Times are UTC.\n\nRead `DESIGN.md` and `HANDOFF.md` first. Use this file to look up exactly what was asked and agreed.\n\n")
  for ts,w,txt in rows: o.write(f'---\n\n### {w} · {ts}\n\n{txt}\n\n')
import collections; print(collections.Counter(w for _,w,_ in rows))
