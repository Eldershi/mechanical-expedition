"""Draft a deterministic division of vanilla-biome vegetation among selected mods.
Never applies automatically. Terrain router, oceans, ore stages and modded biomes are retained.
"""
from pathlib import Path
import json,zipfile
ROOT=Path(__file__).resolve().parents[1]
MODS=ROOT/'instance/mods'
OUT=ROOT/'evidence/optimization/foliage-compat-draft'
def main():
 zips={name:zipfile.ZipFile(next(MODS.glob(pattern))) for name,pattern in {'terralith':'Terralith*','geophilic':'Geophilic*','wwoo':'WWOO*'}.items()}
 def biomes(z):return {p:z.read(p) for p in z.namelist() if p.startswith('data/minecraft/worldgen/biome/') and p.endswith('.json')}
 resources={name:biomes(z) for name,z in zips.items()}
 OUT.mkdir(parents=True,exist_ok=True);rows=[]
 # WWOO's vanilla overworld list is the explicit domain. Nether/End generators are not edited.
 for path,raw in resources['wwoo'].items():
  if path not in resources['terralith']:continue
  base=json.loads(resources['terralith'][path]);owner='geophilic' if path in resources['geophilic'] else 'wwoo';donor=json.loads(resources[owner][path])
  old=base['features'][9];new=donor['features'][9]
  assert len(new)==len(set(new)),path
  base['features'][9]=new
  dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
  rows.append({'resource':path,'vegetationOwner':owner,'retainedFromTerralith':['climate parameters','carvers','other feature stages','mob spawns','effects'],'oldVegetation':old,'newVegetation':new})
 for path,raw in resources['geophilic'].items():
  if path in resources['terralith'] or path not in resources['wwoo']:continue
  base=json.loads(resources['wwoo'][path]);donor=json.loads(raw);old=base['features'][9];base['features'][9]=donor['features'][9]
  dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
  rows.append({'resource':path,'vegetationOwner':'geophilic','retainedFromWWOO':['all non-vegetation fields'],'oldVegetation':old,'newVegetation':donor['features'][9]})
 report={'status':'DRAFT_UNAPPLIED_REQUIRES_RUNTIME_FEATURE_CYCLE_AND_SURFACE_TEST','policy':'Geophilic vegetation in its vanilla-biome subset; WWOO vegetation in remaining shared vanilla biomes; retain Terralith custom biomes and terrain data. Never concatenate three complete tree lists.','rows':rows}
 (OUT/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'drafts':len(rows),'geophilic':sum(x['vegetationOwner']=='geophilic' for x in rows),'wwoo':sum(x['vegetationOwner']=='wwoo' for x in rows)}))
if __name__=='__main__':main()
