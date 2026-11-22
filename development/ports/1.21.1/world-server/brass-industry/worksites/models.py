"""Assembly geometry, construction coordinates and working paths in block pixels."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import product

NS = "expedition_industry"
GIRDER = "create:metal_girder"
IRON = "create:industrial_iron_block"
CASING = "create:andesite_casing"
COPPER = "create:copper_casing"
BRICK = "create:small_scoria_bricks"
PIPE = "create:fluid_pipe"
CONNECTOR = "createaddition:large_connector"
BURNER = "createaddition:liquid_blaze_burner"
SMOKESTACK = "railways:smokestack_oilburner"
FURNACE = "shaft_furnace"
CELL = "electrolytic_cell"
TRADE = "trading_station"

DIRECTIONS = {
    "west": (0,-1), "east": (0,1), "down": (1,-1),
    "up": (1,1), "north": (2,-1), "south": (2,1),
}


def occupied(bounds):
    return product(*(range(bounds[i]//16, (bounds[i+3]+15)//16) for i in range(3)))


@dataclass
class Site:
    name: str
    label: str
    size: tuple
    core: tuple
    parts: list = field(default_factory=list)
    live: dict = field(default_factory=dict)
    ports: dict = field(default_factory=dict)
    routes: dict = field(default_factory=dict)
    labels: list = field(default_factory=list)
    signal: tuple | None = None
    launches: list = field(default_factory=list)
    replacements: dict = field(default_factory=dict)
    required_empty: set = field(default_factory=set)

    def box(self, name, material, bounds, block=IRON, motion="body"):
        self.parts.append(dict(name=name, group=material, material=material, bounds=bounds,
                               block=block, motion=motion))

    def tube(self, name, material, bounds, axis, thickness=2, block=PIPE):
        """Four fixed walls and an open bore in the direction of travel."""
        u,v = [j for j in range(3) if j != axis]
        a,b = tuple(bounds[:3]),tuple(bounds[3:])
        for i in (u,v):
            for side in (0,1):
                lo,hi=list(a),list(b)
                if i==v:
                    lo[u]+=thickness
                    hi[u]-=thickness
                if side:
                    lo[i]=hi[i]-thickness
                else:
                    hi[i]=lo[i]+thickness
                self.box(name,material,tuple(lo+hi),block)

    def beam(self, name, axis, start, end, center, bottom, top):
        spans = ((4,bottom,bottom+2),(2,bottom+2,top-2),(4,top-2,top))
        for width,y,Y in spans:
            a,b=center-width,center+width
            bounds=(start,y,a,end,Y,b) if axis==0 else (a,y,start,b,Y,end)
            self.box(name,"girder",bounds,GIRDER)

    def native(self, label, pos, block, state, material, shape=None, choices=None):
        if pos in self.live:
            raise ValueError(pos)
        self.live[pos]={"pos": pos, "block": block, "state": state, "choices": choices}
        frame=tuple(n*16 for n in pos)
        bounds=shape or (1,1,1,15,15,15)
        self.box(label,material,tuple(bounds[i]+frame[i%3] for i in range(6)),block,"native")

    def port(self, name, trait, pos, face, block=PIPE, state=None, anchor=None):
        if pos in self.ports:
            raise ValueError(pos)
        self.ports[pos]=(trait, {"pos":pos, "faces":[face],
                                "io":"OUT" if trait.endswith("_output") else "IN"},
                         block, state or {})
        if anchor is None:
            anchor=boundary(pos,face)
        self.labels.append((name,anchor))

    def terminal(self, depth=12):
        x,y,z=(16*n for n in self.core)
        self.box("维护终端机壳","motor",(x+1,y+2,z+1,x+15,y+14,z+depth),CASING)
        for a,b in ((1,3),(13,15)):
            self.box("显示器侧框","tool",(x+a,y+4,z,x+b,y+12,z+1),CASING)
        for a,b in ((2,4),(12,14)):
            self.box("显示器横框","tool",(x+1,y+a,z,x+15,y+b,z+1),CASING)
        self.box("显示窗","screen",(x+3,y+4,z,x+13,y+12,z+1),CASING)
        self.labels.append(("操作界面",boundary(self.core,"north")))

    def feed(self, pos, toward, family="brass"):
        wall=f"create:{family}_funnel"
        belt=f"create:{family}_belt_funnel"
        self.native("原生漏斗",pos,wall,dict(facing=toward,extracting="false"),"native_funnel",
                    choices=[f"{wall}[facing={toward}]",f"{belt}[facing={toward}]"])
        support=tuple(n-(i==1) for i,n in enumerate(pos))
        self.required_empty.add(support)
        self.labels.append(("固料进料",boundary(pos,toward)))

    def power(self, pos, relay, side="east"):
        # Connector's facing points into the mounting face.
        inward={"east":"west","west":"east","south":"north","north":"south"}[side]
        end = boundary(pos,side)
        self.native("大型连接器",pos,CONNECTOR,dict(facing=inward,mode="push"),"native_power",
                    shape=(1,3,3,12,13,13),choices=[f"{CONNECTOR}[facing={inward}]"])
        self.port("FE 输入","forge_energy_storage",relay,side,CASING,anchor=end)

    def construction(self):
        weights=defaultdict(Counter)
        for part in self.parts:
            if part["motion"]!="body":
                continue
            for cell in occupied(part["bounds"]):
                weights[cell][part["block"]]+=1
        cells={
            pos: {"pos":pos,"block":materials.most_common(1)[0][0],"state":{}}
            for pos,materials in weights.items()
        }
        cells[self.core]={"pos":self.core,"block":f"{NS}:{self.name}","state":{"facing":"north"}}
        for pos,(_,_,block,state) in self.ports.items():
            if pos not in cells:
                raise ValueError(f"{self.name} has no physical port at {pos}")
            cells[pos]={"pos":pos,"block":block,"state":state}
        for pos,info in self.live.items():
            cells[pos]={k:v for k,v in info.items() if k!="choices"}
        for pos,cell in cells.items():
            if cell["block"] == GIRDER:
                x,y,z=pos
                neighbors={"x":((x-1,y,z),(x+1,y,z)),"z":((x,y,z-1),(x,y,z+1)),
                           "top":((x,y+1,z),),"bottom":((x,y-1,z),)}
                cell["state"]={key:"true" for key,pair in neighbors.items()
                               if any(cells.get(p,{}).get("block")==GIRDER for p in pair)}
        assert all(all(0<=n<s for n,s in zip(pos,self.size)) for pos in cells), self.name
        assert not self.required_empty.intersection(cells), (self.name,self.required_empty.intersection(cells))
        for p in self.parts:
            assert all(0<=p["bounds"][i]<p["bounds"][i+3]<=16*self.size[i] for i in range(3)), p
        return {"size":self.size,"cells":sorted(cells.values(),key=lambda d:(d["pos"][1],d["pos"][2],d["pos"][0])),
                "ports":{f"{trait}_{key}":{**data,"trait":trait} for key,(trait,data,_,_) in self.ports.items()},
                "native":[list(p) for p in self.live],
                "air":[list(p) for p in sorted(self.required_empty)]}


def boundary(pos, face):
    axis,sign=DIRECTIONS[face]
    xyz=[n*16+8 for n in pos]
    xyz[axis]+=8*sign
    return tuple(xyz)


def base(site, xs, zs, span):
    for x in xs:
        for z in zs:
            site.box("锚固底板","foot",(x-6,0,z-6,x+6,3,z+6))
            site.box("压紧底脚","frame",(x-4,3,z-4,x+4,13,z+4))
        site.beam("基础纵梁",2,span[0],span[1],x,13,24)
    for z in zs:
        site.beam("基础横梁",0,xs[0]+4,xs[-1]-4,z,13,24)


def shaft_furnace():
    s=Site(FURNACE,"工业高炉",(7,13,8),(3,2,1))
    base(s,(19,93),(29,104),(21,113))
    for x in (19,93):
        for z in (29,104):
            s.box("承托立柱","girder",(x-4,24,z-4,x+4,119,z+4),GIRDER)
            s.box("梁柱节点","foot",(x-6,86,z-6,x+6,94,z+6))
        for y in (78,111):
            s.beam("检修桁架",2,33,100,x,y,y+9)
    for z in (29,104):
        s.beam("炉肩横担",0,23,89,z,78,90)
        s.beam("炉顶横担",0,23,89,z,109,120)
    # The stack narrows at the throat, with separate exhaust and burden paths.
    s.box("耐火炉底","ceramic",(30,24,35,82,32,94),BRICK)
    s.tube("下炉腹","cast_iron",(31,48,37,81,74,94),1,4,IRON)
    s.tube("内衬接缝","ceramic",(29,47,35,83,49,96),1,4,BRICK)
    s.tube("炉身耐热壳","cast_iron",(34,74,40,78,126,90),1,3,IRON)
    for y in (67,91,120):
        s.tube("闭合紧箍","foot",(30,y,36,82,y+4,95),1,7,IRON)
    s.tube("炉喉上盖","tool",(35,126,41,77,130,89),1,8,IRON)
    s.tube("料仓外壳","cylinder",(38,130,44,74,161,83),1,3,CASING)
    s.tube("进料阀与滑槽","tool",(32,144,49,49,158,63),0,2,IRON)
    s.feed((1,9,3),"west")
    s.tube("伸入炉喉的落料管","frame",(49,158,48,63,175,64),1,2,IRON)
    s.box("料仓盖板","tool",(45,173,44,67,177,68))
    s.port("焦炭与返料","item_input",(2,9,3),"west",CASING)
    # A sealed preheater feeds two tuyeres below the burden, never into the exhaust.
    s.native("热风燃烧室",(2,2,3),BURNER,{"blaze":"smouldering"},"glow",
             choices=[f"{BURNER}[blaze={state}]" for state in ("smouldering","fading","kindled","seething")])
    s.native("热风燃烧室",(4,2,3),BURNER,{"blaze":"smouldering"},"glow",
             choices=[f"{BURNER}[blaze={state}]" for state in ("smouldering","fading","kindled","seething")])
    s.box("预热腔顶箱","frame",(31,48,36,81,55,69),CASING)
    s.tube("热风接口","pipe",(7,52,82,31,60,94),0,2)
    s.tube("进氧短管","pipe",(0,52,82,8,60,94),0,2)
    s.tube("熔铁进料","copper",(78,67,82,112,77,94),0,2)
    s.port("氧气进料","fluid_input",(0,3,5),"west")
    s.port("熔融工业铁","fluid_input",(6,4,5),"east")
    s.tube("下行出钢管","copper",(51,18,87,61,30,104),2,2)
    s.tube("出钢接口","copper",(50,18,104,62,30,128),2,2)
    s.port("钢水出口","fluid_output",(3,1,7),"south")
    s.tube("钢坯排出槽","frame",(34,18,0,46,30,45),2,2,IRON)
    s.port("钢坯出口","item_output",(2,1,0),"north",IRON)
    s.box("操作臂","frame",(54,29,25,60,42,37),CASING)
    s.terminal()
    s.box("供电柜","motor",(76,25,91,96,49,109),CASING)
    s.box("电缆保护槽","pipe",(87,49,100,93,70,107),CASING)
    s.box("炉阀接线","frame",(80,68,91,93,74,105),CASING)
    s.power((6,2,6),(5,2,6))
    s.tube("炉喉烟道","frame",(55,137,82,68,148,110),2,2)
    s.tube("排烟立管","frame",(53,137,99,68,189,111),1,2)
    s.tube("烟囱承插座","foot",(49,189,97,68,192,112),1,4,IRON)
    s.native("原生方形烟囱",(3,12,6),SMOKESTACK,{"style":"steel"},"frame")
    s.routes={
        "焦炭与返料":[[(24,152,56),(55,152,56),(55,103,56),(55,61,56)],[(55,52,55),(40,28,40),(40,28,0)]],
        "熔铁与热风":[[(112,72,88),(64,72,88),(55,57,72)],[(0,57,88),(36,57,88),(47,56,58)],
                 [(55,49,79),(55,27,97),(56,25,128)]],
        "排烟":[[(61,70,62),(61,142,62),(61,142,103),(61,202,103)]],
    }
    s.signal=(56,203,104)
    return s


def electrolytic_cell():
    s=Site(CELL,"大型电解池",(7,7,7),(3,2,1))
    base(s,(22,90),(40,92),(32,101))
    for x in (22,90):
        s.box("槽座隔振垫","foot",(x-6,24,39,x+6,30,97))
    s.box("双槽底托","frame",(21,29,42,91,38,93),CASING)
    # Each electrode has its own insulated feedthrough and collection hood.
    for x in (38,74):
        s.tube("隔热槽壁","ceramic",(x-15,38,41,x+15,52,95),1,3,BRICK)
        s.tube("独立气室壳体","cylinder",(x-13,52,42,x+13,70,94),1,3,CASING)
        s.box("集气上盖","tool",(x-15,70,41,x+15,75,95))
        s.box("耐火引线套","insulator",(x-8,75,59,x+8,92,75),CASING)
        s.box("石墨电极","graphite",(x-4,61,63,x+4,102,71),"create:andesite_alloy_block")
        s.box("镀铜母线端片","copper",(x-7,97,60,x+7,104,74),COPPER)
        s.box("液位检视窗","window",(x-8,53,40,x+8,66,42),CASING)
        for y in (52,68):
            s.tube("槽壳紧箍","foot",(x-14,y,41,x+14,y+2,95),1,4,IRON)
    s.replacements["create:andesite_alloy_block"]=["create:andesite_alloy_block","expedition_space:carbon_electrode"]
    s.box("隔膜绝缘中框","insulator",(54,39,42,58,80,94),CASING)
    s.box("分开的汇流排","copper",(35,100,71,77,105,81),COPPER)
    s.box("母线绝缘支座","insulator",(51,81,73,61,100,81),CASING)
    s.tube("西侧产品歧管","pipe",(0,51,67,27,61,77),0,2)
    s.tube("东侧产品歧管","pipe",(85,51,67,112,61,77),0,2)
    # The exterior faces attach to the common pair of product tanks. Native
    # Smart Fluid Pipes downstream keep the products of each recipe separate.
    s.port("产品 A","fluid_output",(0,3,4),"west")
    s.port("产品 B","fluid_output",(6,3,4),"east")
    s.tube("分流进液歧管","copper",(51,35,82,61,45,112),2,2)
    s.port("配方流体入口","fluid_input",(3,2,6),"south")
    s.feed((0,3,2),"west","andesite")
    s.tube("电极投料架","frame",(16,52,36,37,61,46),0,2,IRON)
    s.port("电极或铝料","item_input",(1,3,2),"west",CASING)
    s.tube("铝渣抽出槽","frame",(82,19,0,94,31,47),2,2,IRON)
    s.port("固体产物","item_output",(5,1,0),"north",IRON)
    s.box("操作悬臂","frame",(50,24,23,62,35,43),CASING)
    s.terminal()
    s.box("整流接线柜","motor",(81,33,80,96,52,95),CASING)
    s.box("绝缘升线槽","insulator",(85,52,87,92,103,94),CASING)
    s.box("接线槽端盖","tool",(71,99,77,92,105,94),CASING)
    s.power((6,2,5),(5,2,5))
    s.routes={
        "流体与气体":[[(56,40,112),(56,40,87),(38,57,86),(38,64,72),(0,56,72)],
                     [(56,40,87),(74,57,86),(74,64,72),(112,56,72)]],
        "电极及固料":[[(0,56,40),(23,56,40),(38,64,65)],[(73,42,65),(88,24,39),(88,24,0)]],
        "供电":[[(111,40,88),(88,40,88),(88,101,88),(74,102,69)],[(88,101,88),(38,102,69)]],
    }
    s.signal=(55,98,67)
    return s


def trading_station():
    s=Site(TRADE,"自动贸易终端",(9,9,7),(4,2,1))
    base(s,(20,72,124),(35,92),(27,100))
    for x in (20,72,124):
        s.box("停靠架立柱","girder",(x-4,24,89,x+4,60,96),GIRDER)
    s.box("货运分拣台","cast_iron",(52,17,50,95,30,92),CASING)
    s.box("进货滑槽底座","tool",(49,18,66,63,30,80))
    s.tube("货物送入汇集区","frame",(50,20,68,72,30,78),0,2,IRON)
    s.tube("结算后送往发货架","frame",(72,35,84,104,47,96),0,2,IRON)
    s.box("操作悬臂","frame",(65,25,23,79,35,51),CASING)
    s.terminal()
    # Both pads have open vertical approaches and their own real storage lane.
    for z in (4,5):
        s.native("收货保险库",(2,2,z),"create:item_vault",{"axis":"z"},"vault")
    for z in (3,4):
        s.native("发货保险库",(6,1,z),"create:item_vault",{"axis":"z"},"vault")
    s.native("入库漏斗",(2,1,4),"minecraft:hopper",{"facing":"east"},"frame")
    s.native("出货漏斗",(6,1,5),"minecraft:hopper",{"facing":"north"},"frame")
    s.native("收货拆包机",(2,3,4),"create:packager",{"facing":"up"},"packer")
    s.native("发货打包机",(6,2,4),"create:packager",{"facing":"up"},"packer")
    s.native("收货蜂港",(2,4,4),"create_mobile_packages:bee_port",{"facing":"north"},"receive",
             shape=(0,0,0,16,7,16))
    s.native("起飞蜂港",(6,3,4),"create_mobile_packages:bee_port",{"facing":"north"},"send",
             shape=(0,0,0,16,7,16))
    s.native("发货库存链接",(7,2,4),"create:stock_link",{"face":"wall","facing":"east"},"motor",
             shape=(0,5,5,4,13,12))
    s.box("收货模式开关支架","girder",(8,24,68,16,64,80),GIRDER)
    s.native("收货模式开关底盒",(0,4,4),CASING,{},"motor",shape=(0,0,0,16,16,16))
    s.native("收货模式开关",(1,4,4),"minecraft:lever",{"face":"wall","facing":"east","powered":"true"},"tool",
             shape=(0,3,5,4,12,12))
    s.box("收货蓝色识别梁","receive",(29,60,60,52,64,64),CASING)
    s.box("发货琥珀色识别梁","send",(93,45,60,115,48,64),CASING)
    s.box("收货识别梁座","girder",(29,53,60,32,60,68),GIRDER)
    s.box("发货识别梁座","girder",(112,36,60,115,45,68),GIRDER)
    for x,y in ((2,4),(6,3)):
        for dx,dz in product((-1,0,1),repeat=2):
            for dy in range(1,5):
                s.required_empty.add((x+dx,y+dy,4+dz))
    s.port("收货暂存","item_input",(3,1,4),"west",CASING)
    s.port("发货暂存","item_output",(6,2,5),"down",CASING)
    s.box("接线柜","motor",(106,32,82,128,48,96),CASING)
    s.box("接线桥","pipe",(91,36,84,108,41,92),CASING)
    s.power((8,2,5),(7,2,5))
    s.labels.extend([("收货降落", (40,76,72)),("发货起飞", (104,60,72))])
    s.routes={
        "收货":[[(40,140,101),(40,78,72),(40,58,72),(40,41,72),(40,24,72),(55,24,72),(72,38,63)]],
        "发货":[[(72,38,63),(104,42,88),(104,23,88),(104,23,72),(104,42,72),(104,59,72),(104,132,102)]],
    }
    s.launches=[((40,140,101),(40,76,72)),((104,60,72),(104,132,102))]
    return s


SITES = {site.name:site for site in (shaft_furnace(),electrolytic_cell(),trading_station())}
