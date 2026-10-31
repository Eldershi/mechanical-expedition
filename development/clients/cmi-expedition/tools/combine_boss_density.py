from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 first=json.loads((ROOT/'evidence/optimization/boss-calibration/report.json').read_text());second=json.loads((ROOT/'evidence/optimization/boss-calibration-retry/report.json').read_text());catalog=json.loads((ROOT/'evidence/optimization/boss-density-catalog-draft.json').read_text());wanted={x['id'] for x in catalog['boss_rows']};sets={}
 for rep in [first,second]:
  for group in rep['groups']:
   if group.get('accepted') and any(m in wanted for m in group['members']):sets[group['set']]=group
 resolved=json.loads((ROOT/'evidence/optimization/boss-calibration-retry/dark-tower-resolved.json').read_text());a={'frequency':resolved['frequency'],'spacing':-1,'separation':0,'counts':{'twilightforest:dark_tower':len(resolved['result']['validatedStarts'])},'allCandidatesValidated':True,'results':[{'dimension':'twilightforest:twilight_forest','structure':'twilightforest:dark_tower',**resolved['result']}]};sets['twilightforest:dark_tower']={'set':'twilightforest:dark_tower','members':['twilightforest:dark_tower'],'status':'native_starts_calibrated','accepted':a}
 rows=[]
 for group in sets.values():
  for member,count in group['accepted']['counts'].items():
   if member not in wanted:continue
   sites=[]
   for sample in group['accepted']['results']:
    if sample['structure']==member:
     for x,z,pieces in sample['validatedStarts']:sites.append({'dimension':sample['dimension'],'chunk':[int(x),int(z)],'blockCenter':[int(x)*16+8,int(z)*16+8],'pieces':int(pieces)})
   rows.append({'structure':member,'set':group['set'],'nativeValidStartsInRadius30000':count,'allCandidatesValidated':group['accepted']['allCandidatesValidated'],'sites':sites})
 assert len(rows)==69 and {x['structure'] for x in rows}==wanted
 assert all(x['allCandidatesValidated'] and 1<=x['nativeValidStartsInRadius30000']<=5 for x in rows)
 output={'status':'native_start_calibration_passed_pending_reboot_and_real_full_chunk_spots','seed':'-7939930663323807154','bossStructures':69,'structureSets':68,'radiusBlocks':30000,'rows':sorted(rows,key=lambda x:x['structure']),'ordinaryStructurePolicy':'Native density retained; SparseStructures global1; sorcerous_keep original frequency restored.','wildlifePolicy':'IceAndFire feature lairs moderately sparse; separate from fixed-site69 target.','limits':['Measured native valid starts for fixed test seed; no all-seed guarantee','Native start counts precede real block-placement checks','Existing generated chunks are not rewritten','Not a complete Boss-fight or survival progression test']}
 (ROOT/'evidence/optimization/boss-density-combined.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'bossStructures':len(rows),'sets':len(sets),'nativeStartCountsPassed':True}))
if __name__=='__main__':main()
