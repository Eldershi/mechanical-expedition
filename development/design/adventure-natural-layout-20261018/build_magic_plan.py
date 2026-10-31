from pathlib import Path
import sys,json,hashlib,math,collections
ROOT=(Path.home() / 'Desktop/机械动力：远征');sys.path.insert(0,str(ROOT/'clients/cmi-expedition/tools'));import ftb_snbt
OUT=ROOT/'design/adventure-natural-layout-20261018';BASE=ROOT/'clients/cmi-expedition/instance/config/ftbquests/quests/chapters'
A=ROOT/'design/video-quest-pipeline-20261018/B-magic/analysis'
T=json.loads((A/'task-structure.json').read_text());E=json.loads((A/'dependency-evidence.json').read_text());GUIDE=(A/'guide.md').read_text()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nk(kind,id):return kind+':'+(f'{int(id,16):x}' if kind in ['q','l'] else id.lower())
# Hand-authored semantic positions, indexed in unchanged native quest order. Not a graph-layer algorithm.
POS={
'ars_nouveau':[(-15,0),(-12,0),(-9,0),(-9,-6),(-3,-6),(-6,3),(-3,3),(-6,0),(-3,0),(0,0),(3,-3),(0,-6),(3,-6),(6,-6),(9,-6),(3,6),(6,3),(9,3),(6,6),(12,6)],
'botania':[(-15,0),(-12,0),(-9,0),(-6,-3),(-6,3),(-3,-6),(-3,-3),(0,-3),(0,0),(3,0),(0,3),(3,3),(6,3),(6,0),(9,0),(12,0),(15,0),(12,-6),(15,-6),(18,-6),(-15,3),(3,8),(9,8)],
'eidolon':[(-13,0),(-10,0),(-7,0),(-7,-3),(-4,-3),(-1,-3),(-4,0),(2,0),(5,0),(8,-3),(8,3),(11,0),(11,-6),(14,-6),(14,3)],
'forbidden_arcanus':[(-13,-2),(-13,2),(-10,0),(-7,0),(-7,-3),(-3,-6),(0,-3),(0,3),(0,7),(3,0),(6,0),(9,0),(12,0),(6,6),(9,6),(12,6)],
'irons_spellbooks':[(-13,0),(-10,0),(-7,0),(-4,-3),(-1,-3),(-4,3),(-1,0),(3,0),(3,-5),(6,3),(9,3),(12,-5),(15,-5),(6,-8),(9,0)],
'malum':[(-14,-3),(-14,3),(-11,3),(-8,3),(-5,0),(-2,-3),(-2,0),(-2,3),(1,-6),(1,3),(4,6),(4,3),(7,3),(7,-3),(10,-3),(10,0),(4,0)]}
# Every group is a hand-read gameplay role, not a requirement or new dependency.
GROUPS={
'ars_nouveau':[
 ('被动灌注入口',[0,1,2,7],'至高木→灌注室→宝石及精华作为短入口，不让初次灌注被魔源罐反锁。'),
 ('个人施法与野外晋阶',[3,4,11,12,13,14],'上方施法书与抄写台接仪式火盆；奇美拉、供物、大法师书只在该升级路线收束。'),
 ('魔源与附魔工位',[5,6,8,9],'下侧产魔回接中心附魔装置和种植花，明确个人法力与罐装魔源不同。'),
 ('按需选用的法袍与工具',[10,19],'法袍靠近施法，工具位于外缘，不成为使魔或奇美拉门槛。'),
 ('生物工坊',[15,16,17,18],'星宝石兽、德格米、薇克精、风转草围绕装置及作物支线展开，四者可以独立选择。')],
'botania':[
 ('花园入口',[0,1,2],'花瓣、花药台、白雏菊是左侧短入口，不要求花色全收集。'),
 ('活材料与首个魔力循环',[3,4,5,6,7,8,9],'活木向上供法杖/发射器，活石向下供池与祭坛；花、发射器、池围绕第一次加工汇合。'),
 ('符文与泰拉工艺',[10,11,12,13,14],'下侧符文支路与池上火花在泰拉钢合流，不把符文全集作为先行收集任务。'),
 ('精灵交易及盖亚挑战',[15,16,17,18,19],'交易沿右侧继续；可选盖亚挑战上移成独立远征支路。'),
 ('三处可选自动化',[20,21,22],'补水留在花药台下方，批次控制靠近祭坛，凝聚板回收靠近泰拉钢；不放在Boss之后做毕业锁。')],
'eidolon':[
 ('教典与金属工艺',[0,1,2,3],'教典入门后以白镴/魔力工作台组成基础工坊，仪式刀邻接工位。'),
 ('献祭与三段炼金',[4,5,6,7],'上侧基础火盆取得第一份碎片，下侧坩埚在灵魂宝石处合流；镰刀不反锁首份碎片。'),
 ('双信仰分支',[8,9,10,11],'祭坛向上下分为黑暗/光明，再在可选镰刀汇合；两种象征符保持OR。'),
 ('独立研究与装备',[12,13,14],'研究/渡鸦斗篷在上外缘，召唤魔杖在下外缘，保留可选实用目标。')],
'forbidden_arcanus':[
 ('资源与锻炉搭建',[0,1,2,3,4],'矿石/埃德木双入口汇合洁净粉末与锻炉，锤位于炉侧。'),
 ('四种独立精华补给',[5,6,7,8],'灵魂、血液、辉光、经验各在炉右侧不同方位；只是并行补给，不改成相互加工链。'),
 ('三阶与永恒成果',[9,10,11,12],'二阶→三阶→永恒陨星顺右推进，实用永恒用途作为该工艺成果。'),
 ('外围延伸',[13,14,15],'龙鳞、捕捉器与按需四五阶放下侧，避免成为永恒陨星三阶入口的假门槛。')],
'irons_spellbooks':[
 ('探索到持续施法',[0,1,2],'卷轴→书→抄写台短入口；不把Boss当早期法术书入口。'),
 ('撰写与等级提升工坊',[3,4,5,6,7],'墨水/炼金锅在上，学派核心在下，合于卷轴撰写与奥术铁砧；不要求九学派集齐。'),
 ('按需强化',[9,10,14],'布匹、法球、扩槽在下侧，与施法工坊平行；库存材料不冒充输出NBT验证。'),
 ('探索及实用选修',[8,11,12,13],'邪术知识与两个独立挑战在上外缘；法杖也是可选施放方式，不假定由Boss掉落。')],
'malum':[
 ('木石双入口与首次收魂',[0,1,2,3,4],'符文木从上、魂石/镰刀/精魄从下抵达精魂祭坛；猎取对应精魄而非全收集。'),
 ('首轮灌注三用途',[5,6,7,8],'祭坛右侧金/钢/布匹分三层，方尖碑外移到上侧作为可选加速。'),
 ('灵性石材与坩埚',[9,10,11,12],'下侧石材分向修复基座与坩埚，调谐就在坩埚旁，保留工具耐久语义。'),
 ('图腾、释缚和个人装备',[13,14,15,16],'图腾在右上继续释缚，符文和魂染装备在右中/工坊侧；选择成果不锁定全套。')]
}
def seg_box(a,b,p,hx=.53,hy=.58):
 # Liang-Barsky on the padded 64x72-preview card (72 logical px/grid).
 lo,hi=0.0,1.0;dx=b[0]-a[0];dy=b[1]-a[1]
 for denom,num in [(-dx,a[0]-(p[0]-hx)),(dx,(p[0]+hx)-a[0]),(-dy,a[1]-(p[1]-hy)),(dy,(p[1]+hy)-a[1])]:
  if abs(denom)<1e-10:
   if num<0:return False
  elif denom<0:lo=max(lo,num/denom)
  else:hi=min(hi,num/denom)
 return lo<=hi and hi>=0 and lo<=1

def collisions(points,keys,path):
 return [k for k,p in points.items() if k not in keys and any(seg_box(a,b,p) for a,b in zip(path,path[1:]))]

chapters=[]
for mod,pos in POS.items():
 path=BASE/f'research_adventure_b_{mod}.snbt';raw=path.read_text();c=ftb_snbt.loads(raw);qs=c['quests'];assert len(qs)==len(pos)
 pts={nk('q',q['id']):xy for q,xy in zip(qs,pos)}
 for l in c.get('quest_links',[]):pts[nk('l',l['id'])]=(-13,5)
 images=c.get('images',[]);anchors={nk('a',i['click'].split(':')[-1]):j for j,i in enumerate(images) if 'decorative_anchor:' in i.get('click','')}
 lines=c.get('quest_enhance_decorative_lines',[]);succ=collections.defaultdict(list);pred=collections.defaultdict(list)
 for i,l in enumerate(lines):
  ns=l['nodes'];assert len(ns)==2
  a,b=ns;succ[a].append(b);pred[b].append(a)
 for a in anchors:assert len(succ[a])==1 and len(pred[a])==1,(mod,a,succ[a],pred[a])
 chains=[]
 for start in pts:
  for nxt in succ[start]:
   chain=[start,nxt]
   while chain[-1] in anchors:chain.append(succ[chain[-1]][0]);assert len(chain)<10
   assert chain[-1] in pts
   chains.append(chain)
 anchored=[];direct=[];assigned={}
 for chain in chains:
  start,end=chain[0],chain[-1];s,t=pts[start],pts[end]
  if len(chain)==2:
   hit=collisions(pts,{start,end},[s,t]);direct.append({'nodes':chain,'thirdNodeIntersections':hit});continue
  assert len(chain)==4,(mod,chain)
  candidates=[[s,((2*s[0]+t[0])/3,(2*s[1]+t[1])/3),((s[0]+2*t[0])/3,(s[1]+2*t[1])/3),t]];xs=sorted(set([x*.5 for x in range(-38,43)]+[(s[0]+t[0])/2]));ys=[x*.5 for x in range(-23,25)]
  for x in xs:candidates.append([s,(x,s[1]),(x,t[1]),t])
  for y in ys:candidates.append([s,(s[0],y),(t[0],y),t])
  # Existing two-anchor edges can leave a crowded central worksite diagonally
  # into a free corridor. This moves existing anchors only; no endpoint changes.
  for radius in [1.25,2,3,4]:
   for dx,dy in [(1,1),(1,-1),(-1,1),(-1,-1),(1,0),(-1,0),(0,1),(0,-1)]:
    a=(s[0]+dx*radius,s[1]+dy*radius)
    for ex,ey in [(1,1),(1,-1),(-1,1),(-1,-1),(1,0),(-1,0),(0,1),(0,-1)]:
     b=(t[0]+ex*radius,t[1]+ey*radius)
     candidates.append([s,a,b,t])
  best=None
  for pp in candidates:
   hit=collisions(pts,{start,end},pp)
   if hit:continue
   length=sum(math.dist(a,b) for a,b in zip(pp,pp[1:]));backtrack=max(0,pp[1][0]-max(s[0],t[0]),min(s[0],t[0])-pp[1][0])
   # Prefer short nonzero two-bend corridors; shared semantic edges may share a lane.
   score=length+backtrack*.1+sum(.05 for a,b in zip(pp,pp[1:]) if math.dist(a,b)<.2)
   if best is None or score<best[0]:best=(score,pp)
  if best is None:raise RuntimeError(('no safe routing',mod,chain))
  pp=best[1]
  for key,xy in zip(chain[1:-1],pp[1:-1]):
   assert key not in assigned;assigned[key]=xy
  anchored.append({'nodes':chain,'points':[list(x)for x in pp],'thirdNodeIntersections':[]})
 assert set(assigned)==set(anchors),(mod,set(anchors)-set(assigned))
 # Exact rectangle-intersection test, not a claim that the native game was launched.
 overlaps=[]
 for i,(k,p) in enumerate(pts.items()):
  for k2,p2 in list(pts.items())[i+1:]:
   if abs(p[0]-p2[0])<64/72 and abs(p[1]-p2[1])<1:overlaps.append([k,k2])
 canon=[n for n in T['nodes'] if n['chapterId']=='B.'+mod]
 groupplan=[{'name':name,'questIds':[qs[i]['id'] for i in ids],'rationale':r,'canonicalNodeIds':[canon[i]['id'] for i in ids]} for name,ids,r in GROUPS[mod]]
 relevant_edges=[e for e in T['edges'] if e['source'].startswith('B.'+mod+'.') or e['target'].startswith('B.'+mod+'.')]
 chapters.append({'filename':path.name,'path':str(path),'chapterId':c['id'],'title':c['title'],'sourceSha256':sha(path),'quests':[{'id':q['id'],'title':q['title'],'old':{'x':q['x'],'y':q['y']},'new':{'x':xy[0],'y':xy[1]}}for q,xy in zip(qs,pos)],'questLinks':[{'id':l['id'],'linkedQuest':l['linked_quest'],'old':{'x':l['x'],'y':l['y']},'new':{'x':pts[nk('l',l['id'])][0],'y':pts[nk('l',l['id'])][1]}}for l in c.get('quest_links',[])],'images':[{'index':j,'anchorId':img['click'].split(':')[-1],'old':{'x':img['x'],'y':img['y']},'new':{'x':assigned[nk('a',img['click'].split(':')[-1])][0],'y':assigned[nk('a',img['click'].split(':')[-1])][1]}}for j,img in enumerate(images)],'clusters':groupplan,'sourceRelationsRead':[{'id':e['id'],'source':e['source'],'target':e['target'],'relation':e['relation'],'hard':e['hard'],'scope':e.get('scope'),'evidenceIds':e['evidenceIds']}for e in relevant_edges],'routes':anchored,'directSegments':direct,'geometryValidation':{'nodeCount':len(pts),'widthLogicalUnits':max(x for x,y in pts.values())-min(x for x,y in pts.values()),'heightLogicalUnits':max(y for x,y in pts.values())-min(y for x,y in pts.values()),'nodeBoxOverlaps':overlaps,'directThirdNodeIntersections':[x for x in direct if x['thirdNodeIntersections']],'routedThirdNodeIntersections':[],'routedAnchorCount':len(assigned)}})
report={'schemaVersion':1,'scope':'six magic chapters coordinate-only proposal; not installed','authorship':'Hand-authored chapter-specific gameplay clusters; geometry routing only uses safe corridor search. No graph-leveling layout algorithm.','preserved':['all chapter/quest/task/link/anchor IDs','chapter names','quest text, all playful subtitles','task detection and quantities','dependencies and OR semantics','rewards','decorative line endpoint relationships','image dimensions and all non-coordinate fields'],'inputs':[{'path':str(A/f),'sha256':sha(A/f)}for f in ['task-structure.json','dependency-evidence.json','guide.md']],'chapters':chapters}
(OUT/'magic-plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for c in chapters:print(c['filename'],json.dumps(c['geometryValidation'],ensure_ascii=False))
