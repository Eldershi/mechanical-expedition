#!/usr/bin/env python3
"""Propose hand-designed dimension layouts; never write installed quest files."""
from pathlib import Path
import hashlib, importlib.util, json, math

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
AN=ROOT/'design/video-quest-pipeline-20261018/A-dimensions/analysis'
spec=importlib.util.spec_from_file_location('surgery',ROOT/'design/researched-quest-integration-20261018/finish_existing_copy.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def sha(b):return hashlib.sha256(b).hexdigest()

# Each coordinate below is an editorial choice after reading this chapter's
# complete task text and the current native/recipe evidence. This is not a
# graph rank/grid algorithm. Only invisible existing routing handles below
# use geometric obstacle avoidance.
MAP={
'alex':[
 (0,0),(3,-2),(6,-2),(3,2),
 (9,-13),(12,-15),(15,-15),(15,-11),(18,-17),(22,-12),(22,-9),(26,-10.5),(19,-14),
 (27,-6),(30,-4),(30,0),(34,-4),(30,-10),(34,-10),(42,-10),
 (9,1),(12,-1),(16,-1),(12,3),(16,3),(20,6),
 (27,8),(30,5),(38,10),(30,8),(34,7),(38,7),(40,0),(44,0),
 (9,13),(12,13),(15,13),(23,11),(26,13),(22,-17),(12,-18),(34,0),(20,-1),(41,13),(23,17),(12,9),
 (30,12),(34,12),(38,-10),(23,3),(38,-4),(19,13)],
'twilight':[(0,0),(0,-3),(3,-3),(6,0),(9,0),(12,-5),(15,-5),(21,-5),(15,0),(21,0),(12,5),(15,5),(18,5),(21,5),(25,8),(25,0),(29,0),(33,0)],
'starlight':[(0,0),(3,0),(7,-6),(7,-3),(7,3),(11,-10),(15,-10),(7,12),(11,12),(11,8),(7,16),(12,0),(16,-3),(19,-7),(20,-3),(24,-3),(16,4),(20,4),(24,4),(28,4),(24,8),(7,-10)],
'aether':[(0,0),(3,0),(7,-3),(11,-5),(11,-1),(7,3),(11,3),(7,7),(14,-5),(14,0),(18,0),(14,6),(18,6),(21,9)],
'undergarden':[(0,0),(3,0),(7,-6),(7,0),(7,-3),(7,3),(11,4),(15,4),(19,0),(7,6)],
'deeper':[(0,0),(4,-4),(8,-4),(12,-4),(4,1),(8,1),(12,1),(16,-1),(16,3),(12,7),(16,7),(20,7)],
}

CLUSTERS={
'alex':[
 ('出发与可选石板导航',[0,1,2,3],'入口保留直接探索方式；石板、地图和书只作为旁支导航，不放在五洞穴硬门槛上。'),
 ('磁场：双材料到机械应用',[4,5,6,7,8,9,10,11,12,39,40],'赤钕、青钕并行；本体和粉碎器在采掘操作汇合，电梯和全息独立收束，不串成全收集。'),
 ('原始：驯养与火山两翼',[13,14,15,16,17,18,19,41,48,50],'沙拉与驯龙在下翼，触媒、暝煌龙及碎片在上翼；翼龙/迅猛龙并行，蛋和碎片分别保留真实材料去向。'),
 ('渊海：交易与潜艇两路',[20,21,22,23,24,25,42,49],'珍珠交易横向上支，天然艇和碎船兽下支；人工造艇为后续重复生产，胚胎另向蛋合流。'),
 ('撼地斯拉材料合流',[32,33],'只在板块碎片、撼地龙蛋和永恒胚胎已有配方交汇处收束；不把毒化整线、核弹或任一洞穴强制放在孵化前。'),
 ('毒化：防护、工业、核能各选',[26,27,28,29,30,31,43,46,47],'食物与射线猫靠近入场，工业能力/聚合物板位于独立下翼，只接防化服和枪；核炉与核弹并列选修。'),
 ('异寂：仪式与黑暗装备',[34,35,36,37,38,44,45,51],'仪式到遗弃者再影丝是可读主支；兜帽、斗篷和弓分别展开，窥探/控心留作近入口独立工具。'),
],
'twilight':[
 ('入场、地图与娜迦巫妖',[0,1,2,3,4],'地图小支位于入口上方，娜迦巫妖主干保持清晰；导航不成为新增完成条件。'),
 ('沼泽与火焰沼泽',[5,6,7],'迷宫取得沙拉酱肉，实际吃肉，再九头蛇。'),
 ('雪地与冰川',[8,9],'雪怪首领到冰雪女王，与另外两分支同时展开。'),
 ('黑森林与高塔',[10,11,12,13],'奖杯基座、幻影骑士、高塔操作、暮初恶魂沿下支渐进。'),
 ('炽铁的任选来源',[14],'血或泪任选，独立在汇合点下方，不伪成双方Boss都必须的收集。'),
 ('三支汇合后高地',[15,16,17],'三个真实原生资格汇合；巨人镐/余烬灯与终焉高原向右收束。'),
],
'starlight':[
 ('守门与球体',[0,1],'挑战或屠龙后交谈为OR；球体还有配方来源，保持现有导航线而不加硬锁。'),
 ('生态、矿物与施法',[2,3,4,9,10,21],'资源位于入口周围的独立短翼；不要求按树脂、矿石、河流、陨石逐一走完。'),
 ('星火与流璃工艺',[5,6,13],'鸟巢到流璃位于上方，星火剑靠近花园模板，避免把月藤排成材料前置。'),
 ('采矿能力',[7,8],'饥渴之牙到晶生催化器独立短支。'),
 ('寻觅与花园',[11,12,14,15],'眼是导航备选；花园、月藤和战镰沿上支，不锁锻造厂。'),
 ('锻造厂到两种加工',[16,17,18,19,20],'锻造厂/傀儡下支分出氧化钢的普通烧炼和去氧化合金炉，不以合金炉反锁普通钢。'),
],
'aether':[
 ('入场与本地材料',[0,1],'本地工具居入口近处，探索准备并不锁三个地牢。'),
 ('神能加工',[2,3,4],'神能炉分到重力晶和治愈石；已有替代配方不改OR。'),
 ('孵化与冷冻',[5,6,7],'孵化器到孵化进度一短支，冷冻器为独立能力。'),
 ('青铜地牢',[8],'合适镐能造成伤害，不先要求重力装或其他地牢。'),
 ('白银地牢',[9,10],'10勋章到女王是真实资格，独立放中部。'),
 ('黄金地牢与可选收获',[11,12,13],'烈阳、日轮祭坛与凤凰变黑曜石在下部；没有青铜/白银硬序。'),
],
'undergarden':[
 ('点门与生存补给',[0,1,2],'催化石工具进入石砖门，食物在入口上翼。'),
 ('并行材料和工具',[3,4,5,9],'融并、御腐、交易与弹弓不串行；融并工具只在真正锻造升级处接合。'),
 ('墓穴材料与锻造合流',[6,7,8],'墓穴守卫、9粒合锭再与融并工具和模板合流，升级为章内清晰收束。'),
],
'deeper':[
 ('古城与监守者装备',[0,1,2,3],'甲壳可箱或实体；强化碎片与监守者装备上翼，和门户材料分开。'),
 ('深渊之心点门',[4,5],'心会消耗；向右进入幽冥，不要求先全套甲。'),
 ('幽冥装备分叉',[6,7,8,9],'骨头分别进入额外心法杖或鞘翅；Resonarium为独立铁装升级，不串在监守者套装前。'),
 ('神庙实用工具',[10,11],'神庙到同维度已加载区块传讯器，单独下翼收束。'),
]}

def rect_hit(a,b,c,half=.57):
    # Liang-Barsky segment vs expanded 64x72 px node, 72px logical unit.
    x,y=c;lo=0.;hi=1.;dx=b[0]-a[0];dy=b[1]-a[1]
    for p,q in [(-dx,a[0]-x+half),(dx,x+half-a[0]),(-dy,a[1]-y+half),(dy,y+half-a[1])]:
        if abs(p)<1e-10:
            if q<0:return False
        else:
            r=q/p
            if p<0:lo=max(lo,r)
            else:hi=min(hi,r)
            if lo>hi:return False
    return True

def collision_segments(points,coords,exclude):
    return [(i,k) for i,(a,b) in enumerate(zip(points,points[1:]))
            for k,c in coords.items() if k not in exclude and rect_hit(a,b,c)]

def length(points):return sum(math.dist(a,b) for a,b in zip(points,points[1:]))

def route(a,b,coords,exclude,all_routes):
    # Invisible existing two-corner chains only. Try hand-layout free corridors
    # rather than retaining the previous chapter-wide overhead bus.
    xs={a[0]+1.,b[0]-1.,(a[0]+b[0])/2}
    ys={a[1],b[1],(a[1]+b[1])/2}
    for x,y in coords.values():
        xs.update((x-1.,x+1.));ys.update((y-1.,y+1.))
    minx=min(v[0] for v in coords.values());maxx=max(v[0] for v in coords.values())
    miny=min(v[1] for v in coords.values());maxy=max(v[1] for v in coords.values())
    xs.update((minx-1.5,maxx+1.5));ys.update((miny-1.5,maxy+1.5))
    candidates=[]
    for x in xs:candidates.append([a,(x,a[1]),(x,b[1]),b])
    for y in ys:candidates.append([a,(a[0],y),(b[0],y),b])
    good=[p for p in candidates if not collision_segments(p,coords,exclude)]
    if not good:
        for x in xs:
            for y in ys:
                for p in ([a,(x,y),(b[0]-1.,y),b],[a,(a[0]+1.,y),(x,y),b]):
                    if not collision_segments(p,coords,exclude):good.append(p)
    assert good,('no 2-anchor corridor',a,b)
    # Prefer shorter paths, then discourage reusing the same long parallel bus.
    def cost(p):
        overlap=sum(1 for old in all_routes if p[1:3]==old[1:3])
        return length(p)+overlap*1.5
    return min(good,key=cost)

def main():
    task_blob=(AN/'task-structure.json').read_bytes();ev_blob=(AN/'dependency-evidence.json').read_bytes();guide_blob=(AN/'guide.md').read_bytes()
    task=json.loads(task_blob);ev=json.loads(ev_blob)
    result={'schemaVersion':1,'purpose':'coordinates_only_manual_natural_layout','coordinateSpace':'logical_grid','logicalUnitPx':72,
        'formalSourcesWritten':False,'chapters':[],
        'evidenceSources':[{'path':str((AN/n).relative_to(ROOT)),'sha256':sha(b),'bytesRead':len(b)} for n,b in [('task-structure.json',task_blob),('dependency-evidence.json',ev_blob),('guide.md',guide_blob)]],
        'preserve':['chapter and quest titles','quest IDs and task IDs','all task conditions and item ORs','all subtitles','all rewards','all hard dependencies','all decorative line relationships and endpoint IDs'],
        'scopeBoundary':'Only proposed coordinates; research guides remain supporting sources, current installed task prose is authoritative for task content. No new survival playtest.'}
    for name,positions in MAP.items():
        path=ROOT/f'clients/cmi-expedition/instance/config/ftbquests/quests/chapters/research_adventure_a_{name}.snbt'
        blob=path.read_bytes();doc=s.loads(blob.decode());qs=doc['quests'];assert len(qs)==len(positions)
        # Center each hand-designed chapter without changing its relative plan.
        center=(min(x for x,y in positions)+max(x for x,y in positions))/2
        # Alex's five biome regions alternate across three bands: magnetic /
        # primal above, sea / toxic through the middle, darkness below-left.
        # This is a different composition, not a compressed vertical list.
        xy={q['id']:(p[0]-center,p[1]) for q,p in zip(qs,positions)}
        nodes=[{'questId':q['id'],'title':q.get('title'),'old':{'x':q.get('x',0),'y':q.get('y',0)},'new':{'x':xy[q['id']][0],'y':xy[q['id']][1]}} for q in qs]
        # Decode exact existing decorative paths, preserving their full graph.
        ref={'q:'+q['id'].lower().lstrip('0'):q['id'] for q in qs}
        image_ref={'a:'+im['click'].split(':')[-1]:i for i,im in enumerate(doc.get('images',[])) if str(im.get('click','')).startswith('quest_enhance:decorative_anchor:')}
        lines=doc.get('quest_enhance_decorative_lines',[]);adj={}
        for line in lines:
            for a,b in zip(line['nodes'],line['nodes'][1:]):adj.setdefault(a,[]).append(b)
        chains=[]
        def walk(v,path):
            if v.startswith('q:') and len(path)>1:chains.append(path);return
            for w in adj.get(v,[]):
                assert w not in path
                walk(w,path+[w])
        for v in adj:
            if v.startswith('q:'):walk(v,[v])
        image_new={};routing=[];routes=[]
        for chain in chains:
            a,b=ref[chain[0]],ref[chain[-1]];anchors=chain[1:-1]
            if not anchors:
                pts=[xy[a],xy[b]]
            else:
                assert len(anchors)==2,chain
                pts=route(xy[a],xy[b],xy,{a,b},routes)
                for key,p in zip(anchors,pts[1:-1]):
                    idx=image_ref[key]
                    assert idx not in image_new
                    image_new[idx]=p
            routes.append(pts)
            hits=collision_segments(pts,xy,{a,b})
            routing.append({'sourceQuestId':a,'targetQuestId':b,'unchangedNodeReferences':chain,'points':[list(p) for p in pts], 'thirdNodeIntersections':[{'segment':i,'questId':k} for i,k in hits]})
        images=[]
        for i,im in enumerate(doc.get('images',[])):
            assert i in image_new,('Unrouted image requires manual treatment',name,i,im)
            p=image_new[i]
            images.append({'index':i,'identity':im.get('click'),'old':{'x':im.get('x',0),'y':im.get('y',0)},'new':{'x':p[0],'y':p[1]},'zeroWidthRoutingAnchor':True})
        overlaps=[]
        for i,q in enumerate(qs):
            for q2 in qs[i+1:]:
                a,b=xy[q['id']],xy[q2['id']]
                if abs(a[0]-b[0])<1.15 and abs(a[1]-b[1])<1.15:overlaps.append([q['id'],q2['id']])
        chapterId='A-'+name
        an_ch=next(c for c in task['chapters'] if c['id']==chapterId)
        assert len(an_ch['nodeIds'])==len(qs)
        analysis_by_q={q['id']:aid for q,aid in zip(qs,an_ch['nodeIds'])}
        clusters=[]
        for title,indices,why in CLUSTERS[name]:
            ids=[analysis_by_q[qs[i]['id']] for i in indices]
            relevant=[r for r in ev['edgeRecords'] if r['source'] in ids or r['target'] in ids]
            clusters.append({'title':title,'questIds':[qs[i]['id'] for i in indices],'analysisNodeIds':ids,'rationale':why,'evidenceEdgeIds':[r['id'] for r in relevant], 'hardEdgesRemainScoped':[{'source':r['source'],'target':r['target'],'relation':r['relation'],'necessity':r.get('necessity'),'evidenceIds':r.get('evidenceIds',[])} for r in relevant if r['hard']]})
        assert sorted(i for _,ix,_ in CLUSTERS[name] for i in ix)==list(range(len(qs)))
        issues=[r for r in routing if r['thirdNodeIntersections']]
        result['chapters'].append({'filename':path.name,'path':str(path.relative_to(ROOT)),'title':doc['title'],'chapterId':doc['id'],'sourceSha256':sha(blob),'quests':nodes,'questLinks':[],'images':images,'clusters':clusters,'decorativeRouting':routing,'validation':{'questCount':len(qs),'allQuestsCovered':True,'allImagesCovered':True,'questLinksCount':len(doc.get('quest_links',[])),'questOverlapPairs':overlaps,'linesCrossingThirdNodes':issues,'extent':{'minX':min(p[0] for p in xy.values()),'maxX':max(p[0] for p in xy.values()),'minY':min(p[1] for p in xy.values()),'maxY':max(p[1] for p in xy.values())},'uniqueYRows':len({p[1] for p in xy.values()})}})
    result['validation']={'chapters':len(result['chapters']),'quests':sum(len(c['quests']) for c in result['chapters']),'images':sum(len(c['images']) for c in result['chapters']),'passed':all(not c['validation']['questOverlapPairs'] and not c['validation']['linesCrossingThirdNodes'] for c in result['chapters'])}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'dimensions-plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for c in result['chapters']:print(c['filename'],c['validation'])
    assert result['validation']['passed'],'Geometry issues must be manually corrected before handoff'

if __name__=='__main__':main()
