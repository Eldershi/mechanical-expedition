#!/usr/bin/env python3
"""Enrich six reviewed existing goals and repair one dangling overlay-only link."""
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('bumble_finish',ROOT/'tools/quest-workbench/import_bumblezone.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
loads=g.parser()
ROOTS=[ROOT/'clients/cmi-expedition/instance',ROOT/'clients/cmi-expedition/overlay',ROOT/'servers/cmi-expedition/instance']
COPY={
 'technology/A-tech-core-logic':['将1块线刻硅板、1枚磨制玫瑰石英和1块逻辑电路板放入压印器，得到1个逻辑处理器。需要自动生产时，将产物送回存储网络。'],
 'technology/B-engblocks':['按配方准备工业机壳与轻工构件，每轮制作4个轻型工程块。重型工程块、红石工程块分别使用各自配方，按手册为要搭建的机器备料。'],
 'technology/B-squeezer':['建造挤压机前先在配方查询中选择目标产物，再按手册备料。压榨植物油也可使用机械动力对种子进行压块。'],
 'technology/B-autowork':['按手册搭好自动化工程师装配台，使用工程师锤成型。装入电子管蓝图并选中配方，从蓝点输入材料、上侧供电、末端传送带收集产物。持续补料，连续生产至少两批电子管。'],
 'technology/B-diode':['将琥珀金线、殷钢板、纯净石英棱镜投入部件装配机，每轮制得4个激光二极管。'],
 'technology/B-electronic':['在部件装配机投入激光二极管、防腐木台阶、石英和琥珀金线，每轮制得2个电子元件。按照配方选择同槽材料，成品可接入后续构件生产。'],
}
TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|[{}\[\]]')

def sha(blob):return hashlib.sha256(blob).hexdigest()
def atomic(path,blob):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name('.'+path.name+'.finish.tmp')
 try:tmp.write_bytes(blob);tmp.replace(path)
 finally:tmp.unlink(missing_ok=True)

def quest_span(text,qid):
 match=re.search(r'\bid\s*:\s*"'+re.escape(qid)+'"',text);assert match,qid
 stack=[]
 for token in TOKEN.finditer(text):
  if token.start()>=match.start():break
  if token.group()=='{':stack.append(token.start())
  elif token.group()=='}':stack.pop()
 start=stack[-1];depth=0
 for token in TOKEN.finditer(text,start):
  if token.group()=='{':depth+=1
  elif token.group()=='}':
   depth-=1
   if depth==0:return start,token.end()
 raise AssertionError('Unclosed quest')

def replace_description(text,qid,values):
 a,b=quest_span(text,qid);block=text[a:b]
 match=re.search(r'\bdescription\s*:\s*\[',block)
 literal=g.snbt(values,3)
 if match:
  start=match.end()-1;depth=0
  for token in TOKEN.finditer(block,start):
   if token.group()=='[':depth+=1
   elif token.group()==']':
    depth-=1
    if depth==0:
     block=block[:start]+literal+block[token.end():];break
  else:raise AssertionError('Unclosed description')
 else:block=block[:-1]+'\n\t\t\tdescription: '+literal+'\n\t\t}'
 return text[:a]+block+text[b:]

def main():
 rows=json.loads((HERE/'staging/existing-copy-enrichments.json').read_text())
 before={};writes={};operations=[]
 for base in ROOTS:
  for path in (base/'config/ftbquests/quests/chapters').glob('*.snbt'):
   raw=path.read_bytes();doc=loads(raw.decode());text=raw.decode()
   byid={q['id']:q for q in doc.get('quests',[])}
   for row in rows:
    if row['questId'] not in byid:continue
    paragraphs=[p for p in row['description'] if p.startswith('{image:') and 'width:32 ' not in p]+COPY[row['nodeKey']]
    old=byid[row['questId']].get('description',[])
    updated=[v for v in old if v]+[v for v in paragraphs if v not in old]
    text=replace_description(text,row['questId'],updated)
    operations.append({'path':str(path.relative_to(ROOT)),'questId':row['questId'],'sourceNodeKey':row['nodeKey']})
   after=loads(text)
   for original,changed in zip(doc.get('quests',[]),after.get('quests',[])):
    left,right=deepcopy(original),deepcopy(changed);left.pop('description',None);right.pop('description',None)
    assert left==right,'Non-copy change: '+str(path)
   if text.encode()!=raw:before[path]=raw;writes[path]=text.encode()
 # The old overlay overview is intentionally a different draft from the live
 # client/server. Repair only its missing prerequisite, preserving that variant.
 path=ROOTS[1]/'config/ftbquests/quests/chapters/expedition_technology.snbt'
 raw=path.read_bytes();doc=loads(raw.decode());coil=next(q for q in doc['quests'] if q['id']=='61A447533BE35575')
 assert coil.get('dependencies')==['7CA16714E43959A6']
 coil.pop('dependencies')
 qid='304F1C5501224675'
 for base in ROOTS:
  assert any(q['id']==qid for p in (base/'config/ftbquests/quests/chapters').glob('research_*.snbt') for q in loads(p.read_text())['quests'])
 lid=f'{int(hashlib.sha256(b"cmi/coil/assembly/runtime-link/20261018").hexdigest()[:16],16)&0x7fffffffffffffff:016X}'
 assert not doc.get('quest_links') and not doc.get('quest_enhance_decorative_lines')
 doc['quest_links']=[{'id':lid,'linked_quest':qid,'x':0.0,'y':-3.0,'shape':'rsquare','size':0.75}]
 doc['quest_enhance_decorative_lines']=[{'nodes':['l:'+format(int(lid,16),'x'),'q:'+format(int(coil['id'],16),'x')]}]
 before[path]=raw;writes[path]=(g.snbt(doc)+'\n').encode()
 manifest_path=ROOT/'clients/cmi-expedition/evidence/overlay-files.json';raw=manifest_path.read_bytes();manifest=json.loads(raw)
 for p,b in writes.items():
  if ROOTS[1] in p.parents:manifest[p.relative_to(ROOTS[1]).as_posix()]=sha(b)
 before[manifest_path]=raw;writes[manifest_path]=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
 backup=HERE/'backups'/('existing-copy-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
 for p,b in before.items():atomic(backup/p.relative_to(ROOT),b)
 done=[]
 try:
  for p,b in writes.items():
   assert p.read_bytes()==before[p],'Concurrent edit: '+str(p)
   atomic(p,b);done.append(p);assert p.read_bytes()==b
 except BaseException:
  for p in reversed(done):atomic(p,before[p])
  raise
 result={'applied':True,'copyEnrichments':operations,'overlayDanglingDependencyRepaired':True,'newLinkID':lid,
         'questAndTaskIDsPreserved':True,'backup':str(backup),
         'files':[{'path':str(p.relative_to(ROOT)),'beforeSHA256':sha(before[p]),'afterSHA256':sha(b)} for p,b in writes.items()]}
 atomic(HERE/'root-review/existing-copy-finish-result.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps({k:v for k,v in result.items() if k not in ('files','copyEnrichments')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
