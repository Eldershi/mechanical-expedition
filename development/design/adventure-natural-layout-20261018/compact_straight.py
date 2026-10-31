#!/usr/bin/env python3
"""Compact the accepted semantic regions and make existing routes straight."""
from copy import deepcopy
from datetime import datetime
import argparse, hashlib, importlib.util, json, math, os, re, random
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'compact-straight'
spec=importlib.util.spec_from_file_location('surgery',ROOT/'design/researched-quest-integration-20261018/finish_existing_copy.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
g=s.g;loads=s.loads
GROUP='54D4CAA40ADB5408'
ROOTS=[ROOT/p for p in ('clients/cmi-expedition/instance','clients/cmi-expedition/overlay','servers/cmi-expedition/instance')]
REL=Path('config/ftbquests/quests/chapters')
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def atomic(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name('.'+p.name+'.compact.tmp')
 try:t.write_bytes(b);t.replace(p)
 finally:t.unlink(missing_ok=True)
def qref(kind,qid):return kind+':'+format(int(qid,16),'x')

def hit(a,b,c,half=.54):
 x,y=c;lo=0.;hi=1.;dx=b[0]-a[0];dy=b[1]-a[1]
 for p,q in [(-dx,a[0]-x+half),(dx,x+half-a[0]),(-dy,a[1]-y+half),(dy,y+half-a[1])]:
  if abs(p)<1e-12:
   if q<0:return False
  else:
   r=q/p
   if p<0:lo=max(lo,r)
   else:hi=min(hi,r)
   if lo>hi:return False
 return True

def chains(doc):
 lines=doc.get('quest_enhance_decorative_lines',[]);adj={};direct=[]
 for i,line in enumerate(lines):
  nodes=line.get('nodes',[])
  for a,b in zip(nodes,nodes[1:]):adj.setdefault(a,[]).append((b,i))
 result=[]
 def walk(v,path,indices):
  if v.startswith(('q:','l:')) and len(path)>1:
   result.append({'path':path,'lineIndices':indices});return
  for w,i in adj.get(v,[]):
   assert w not in path,'Decorative cycle'
   walk(w,path+[w],indices+[i])
 for v in adj:
  if v.startswith(('q:','l:')):walk(v,[v],[])
 anchors={a for r in result for a in r['path'] if a.startswith('a:')}
 original={'a:'+im['click'].split(':')[-1] for im in doc.get('images',[]) if str(im.get('click','')).startswith('quest_enhance:decorative_anchor:')}
 assert anchors==original,'All original route anchors must be accounted for'
 return result

def metrics(coords,edges,basis):
 keys=list(coords);overlaps=[];blocks=[];closeness=0.
 for i,a in enumerate(keys):
  x,y=coords[a]
  for b in keys[i+1:]:
   u,v=coords[b];dx=abs(x-u);dy=abs(y-v)
   if dx<1.13 and dy<1.13:overlaps.append((a,b))
   distance=math.hypot(dx,dy)
   if distance<1.75:closeness+=(1.75-distance)**2
 for a,b in edges:
  for c in keys:
   if c not in (a,b) and hit(coords[a],coords[b],coords[c]):blocks.append((a,b,c))
 drift=sum((coords[k][0]-basis[k][0])**2+(coords[k][1]-basis[k][1])**2 for k in keys)
 score=len(overlaps)*3000+len(blocks)*100+closeness*12+drift*.45
 return score,overlaps,blocks

def local_score(coords,edges,basis,key):
 # Contributions that can change when exactly one card moves. All terms use
 # the same weights as metrics; unrelated card pairs and edges are constant.
 x,y=coords[key];score=0.
 for other,(u,v) in coords.items():
  if other==key:continue
  dx=abs(x-u);dy=abs(y-v)
  if dx<1.13 and dy<1.13:score+=3000
  distance=math.hypot(dx,dy)
  if distance<1.75:score+=(1.75-distance)**2*12
 for a,b in edges:
  if key in (a,b):
   for c,p in coords.items():
    if c not in (a,b) and hit(coords[a],coords[b],p):score+=100
  elif hit(coords[a],coords[b],coords[key]):score+=100
 score+=((x-basis[key][0])**2+(y-basis[key][1])**2)*.45
 return score

def compact(doc,factor=None):
 ns=doc.get('quests',[])+doc.get('quest_links',[])
 nodes={qref('q',q['id']):q for q in doc.get('quests',[])}
 nodes.update({qref('l',q['id']):q for q in doc.get('quest_links',[])})
 routes=chains(doc);edgekeys={(r['path'][0],r['path'][-1]) for r in routes}
 for q in doc.get('quests',[]):
  for dep in q.get('dependencies',[]):
   if qref('q',dep) in nodes:edgekeys.add((qref('q',dep),qref('q',q['id'])))
 edges=sorted(edgekeys)
 xs=[q['x'] for q in ns];ys=[q['y'] for q in ns]
 ox=(max(xs)+min(xs))/2;oy=(max(ys)+min(ys))/2
 # Uniformly compact the existing hand-designed semantic composition. Local
 # relaxation below moves only obstructing cards, never ranks by graph depth.
 factor=(.70 if len(ns)>30 else .72) if factor is None else factor
 basis={k:((q['x']-ox)*factor,(q['y']-oy)*factor) for k,q in nodes.items()}
 pos=deepcopy(basis);last=None;iterations=0
 bounds=(min(p[0] for p in basis.values())-.7,max(p[0] for p in basis.values())+.7,min(p[1] for p in basis.values())-.7,max(p[1] for p in basis.values())+.7)
 def allowed(p,key):return math.dist(p,basis[key])<=3.1 and bounds[0]<=p[0]<=bounds[1] and bounds[2]<=p[1]<=bounds[3]
 for iteration in range(360):
  score,over,blocks=metrics(pos,edges,basis)
  if not over and not blocks:break
  candidates={k for pair in over for k in pair}|{c for a,b,c in blocks}
  # Moving an endpoint slightly can clear a long straight line without sending
  # the obstructing card outside its original biome/ritual/material region.
  if iteration%3==2:candidates|={k for a,b,c in blocks for k in (a,b)}
  best=(score,None,None)
  for key in sorted(candidates):
   old=pos[key];x,y=old;oldlocal=local_score(pos,edges,basis,key)
   steps=(.45,.85,1.3,1.8) if iteration<160 else (.55,1.1,1.9,2.5)
   for step in steps:
    for dx,dy in [(step,0),(-step,0),(0,step),(0,-step),(step,step),(step,-step),(-step,step),(-step,-step)]:
     p=(round(x+dx,3),round(y+dy,3))
     if not allowed(p,key):continue
     pos[key]=p;value=score+local_score(pos,edges,basis,key)-oldlocal
     if value<best[0]-1e-7:best=(value,key,p)
   pos[key]=old
  if best[1] is None:break
  pos[best[1]]=best[2];iterations=iteration+1
 score,over,blocks=metrics(pos,edges,basis)
 if over or blocks:
  # A short deterministic local anneal can clear mutually obstructing cards
  # that require a temporary equal-cost move; no graph ranking is introduced.
  rng=random.Random(doc['id']);bestpos=deepcopy(pos);bestscore=score
  for trial in range(50000):
   if trial%120==0:
    score,over,blocks=metrics(pos,edges,basis)
    if not over and not blocks:break
    affected={k for pair in over for k in pair}|{k for row in blocks for k in row}
   key=rng.choice(sorted(affected));old=pos[key]
   step=rng.choice((.35,.55,.8,1.15,1.6,2.1));angle=rng.random()*2*math.pi
   candidate=(round(old[0]+step*math.cos(angle),3),round(old[1]+step*math.sin(angle),3))
   if not allowed(candidate,key):continue
   before=local_score(pos,edges,basis,key);pos[key]=candidate
   delta=local_score(pos,edges,basis,key)-before
   temp=max(.3,65*(1-(trial%10000)/10000)**2)
   if delta<=0 or rng.random()<math.exp(-min(700,delta/temp)):
    score+=delta
    if score<bestscore:bestscore=score;bestpos=deepcopy(pos)
   else:pos[key]=old
  else:pos=bestpos
  score,over,blocks=metrics(pos,edges,basis)
 # Center the final composition; translating all cards does not affect their
 # straight edges, semantic adjacency or relationship identities.
 cx=(min(p[0] for p in pos.values())+max(p[0] for p in pos.values()))/2
 cy=(min(p[1] for p in pos.values())+max(p[1] for p in pos.values()))/2
 pos={k:(round(p[0]-cx,3),round(p[1]-cy,3)) for k,p in pos.items()}
 images=deepcopy(doc.get('images',[]));indices={'a:'+im['click'].split(':')[-1]:i for i,im in enumerate(images) if str(im.get('click','')).startswith('quest_enhance:decorative_anchor:')}
 for r in routes:
  a,b=pos[r['path'][0]],pos[r['path'][-1]];internal=r['path'][1:-1]
  for n,key in enumerate(internal,1):
   assert key in indices
   t=n/(len(internal)+1);images[indices[key]]['x']=round(a[0]+(b[0]-a[0])*t,6);images[indices[key]]['y']=round(a[1]+(b[1]-a[1])*t,6)
 # Decorative art retains its actual content and dimensions. It is placed in
 # compact vacant margins near its original semantic region, avoiding cards.
 imagecollisions=[]
 for i,im in enumerate(images):
  if i in indices.values():continue
  rawx=(im.get('x',0)-ox)*factor-cx;rawy=(im.get('y',0)-oy)*factor-cy
  w=float(im.get('width',0));h=float(im.get('height',0));choices=[]
  for dx in [0,-1,1,-2,2,-3,3,-4,4,-5,5,-7,7]:
   for dy in [0,-1,1,-2,2,-3,3,-4,4,-5,5,-7,7]:
    x=rawx+dx;y=rawy+dy
    # Chapter images use center positions, matching the workbench renderer.
    if any(abs(x-p[0])<w/2+.67 and abs(y-p[1])<h/2+.67 for p in pos.values()):continue
    if any(abs(x-other['x'])<(w+other.get('width',0))/2+.2 and abs(y-other['y'])<(h+other.get('height',0))/2+.2 for j,other in enumerate(images[:i]) if j not in indices.values()):continue
    choices.append((dx*dx+dy*dy,x,y))
  if not choices:imagecollisions.append(i);continue
  _,x,y=min(choices);im['x']=round(x,3);im['y']=round(y,3)
 return {'positions':pos,'images':images,'routes':routes,'iterations':iterations,'nodeOverlapPairs':over,'straightEdgesPassingThirdNodes':blocks,'unplacedArt':imagecollisions,'beforeExtent':{'width':max(xs)-min(xs),'height':max(ys)-min(ys)},'afterExtent':{'width':max(p[0] for p in pos.values())-min(p[0] for p in pos.values()),'height':max(p[1] for p in pos.values())-min(p[1] for p in pos.values())},'initialScale':factor}

def replace_xy(text,id,xy):
 a,b=s.quest_span(text,id);block=text[a:b]
 for k,val in zip(('x','y'),xy):
  block,n=re.subn(r'(?m)^(\s*'+k+r':\s*)-?[0-9.]+[dDfF]?',lambda m:m[1]+g.snbt(float(val)),block,count=1);assert n==1
 return text[:a]+block+text[b:]

def replace_images(text,images):
 match=re.search(r'(?m)^\timages:\s*\[',text)
 if not match:
  assert not images;return text
 start=match.end()-1;depth=0
 for token in s.TOKEN.finditer(text,start):
  if token.group()=='[':depth+=1
  elif token.group()==']':
   depth-=1
   if depth==0:return text[:start]+g.snbt(images,1)+text[token.end():]
 raise AssertionError('unclosed images')

def normal(doc):
 d=deepcopy(doc)
 for n in d.get('quests',[])+d.get('quest_links',[])+d.get('images',[]):n.pop('x',None);n.pop('y',None)
 return d

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');ap.add_argument('--use-plan',action='store_true');args=ap.parse_args()
 if args.apply and (OUT/'install-result.json').exists() and json.loads((OUT/'install-result.json').read_text()).get('applied'):raise RuntimeError('Already applied; inspect receipt')
 OUT.mkdir(exist_ok=True)
 source=[p for p in sorted((ROOTS[0]/REL).glob('*.snbt')) if loads(p.read_text()).get('group')==GROUP];assert len(source)==16
 plans=[]
 if args.use_plan:
  plans=json.loads((OUT/'geometry-plan.json').read_text())['chapters']
  assert {p.name for p in source}=={p['filename'] for p in plans}
  for plan in plans:assert sha((ROOTS[0]/REL/plan['filename']).read_bytes())==plan['sourceSha256'],'Stale candidate geometry'
 else:
  for p in source:
   raw=p.read_bytes();d=loads(raw.decode());c=compact(d);plans.append({'filename':p.name,'title':d['title'],'sourceSha256':sha(raw),**c})
   print(p.name,'iterations',c['iterations'],'overlaps',len(c['nodeOverlapPairs']),'edge_blocks',len(c['straightEdgesPassingThirdNodes']),'art',c['unplacedArt'],'extent',c['beforeExtent'],'->',c['afterExtent'],flush=True)
 atomic(OUT/'geometry-plan.json',enc({'applied':False,'chapters':plans,'semanticRegionsFromExistingAcceptedLayout':True,'routeIdentityPreserved':True}))
 assert all(not p['nodeOverlapPairs'] and not p['straightEdgesPassingThirdNodes'] and not p['unplacedArt'] for p in plans),'Unresolved geometry: preserve source and review candidate'
 before={};writes={};rows=[]
 for base in ROOTS:
  for plan in plans:
   p=base/REL/plan['filename'];raw=p.read_bytes();old=loads(raw.decode());text=raw.decode()
   client=loads((ROOTS[0]/REL/p.name).read_text())
   assert {q['id'] for q in old.get('quests',[])}=={q['id'] for q in client.get('quests',[])}
   assert old.get('quest_enhance_decorative_lines',[])==client.get('quest_enhance_decorative_lines',[])
   assert [im.get('click') for im in old.get('images',[])]==[im.get('click') for im in client.get('images',[])]
   for kind,key in [('q','quests'),('l','quest_links')]:
    for q in old.get(key,[]):text=replace_xy(text,q['id'],plan['positions'][qref(kind,q['id'])])
   # Preserve each root's exact art fields, updating coordinates only.
   ims=deepcopy(old.get('images',[]))
   for im,new in zip(ims,plan['images']):im['x']=new['x'];im['y']=new['y']
   text=replace_images(text,ims);new=loads(text);assert normal(new)==normal(old),'Non-coordinate mutation'
   before[p]=raw;writes[p]=text.encode();rows.append({'path':str(p.relative_to(ROOT)),'beforeSha256':sha(raw),'afterSha256':sha(writes[p]),'questCount':len(new.get('quests',[])),'nonCoordinateParsedFieldsUnchanged':True,'allRelationshipObjectsUnchanged':True})
  assert len(rows)%16==0
 manifest=ROOT/'clients/cmi-expedition/evidence/overlay-files.json';before[manifest]=manifest.read_bytes();m=json.loads(before[manifest])
 for p,b in writes.items():
  if ROOTS[1] in p.parents:m[p.relative_to(ROOTS[1]).as_posix()]=sha(b)
 writes[manifest]=enc(m)
 report={'applied':False,'files':rows,'chapterCount':16,'allOriginalIdsAndTaskBodiesAndArtAndRelationsPreserved':True,'allRoutingAnchorsCollinear':True,'allStraightEdgesClearThirdNodes':True,'techAndStarterUntouched':True,'staticOnlyNoMinecraftRun':True}
 for p,b in before.items():assert p.read_bytes()==b,'Concurrent edit'
 if args.apply:
  bp=OUT/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
  for p,b in before.items():atomic(bp/p.relative_to(ROOT),b)
  done=[]
  try:
   for p,b in writes.items():
    assert p.read_bytes()==before[p],'Concurrent edit';atomic(p,b);done.append(p);assert p.read_bytes()==b
  except BaseException:
   for p in reversed(done):atomic(p,before[p])
   raise
  report.update(applied=True,backupRoot=str(bp),appliedAt=datetime.now().astimezone().isoformat())
 atomic(OUT/('install-result.json' if args.apply else 'dry-run.json'),enc(report))
 print(json.dumps({'applied':report['applied'],'chapters':16,'physicalChapterWrites':len(rows),'backupRoot':report.get('backupRoot')},ensure_ascii=False))

if __name__=='__main__':main()
