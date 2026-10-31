"""Adapt native valid-start counts in one disposable world, using selected mods' APIs.
Requires next-stage helper/control to be installed AFTER the performance matrix.
No claim is made about all seeds or block placement from native starts alone.
"""
from pathlib import Path
import argparse,copy,json,math,time
ROOT=Path(__file__).resolve().parents[1]
INSTANCE=ROOT/'instance';EXPORT=INSTANCE/'kubejs/exported';CONTROL=INSTANCE/'kubejs/optimization-control.json'
OUT=ROOT/'evidence/optimization/boss-calibration';OUT.mkdir(exist_ok=True)

def read(p,default=None):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return default

def write(p,value):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)

class Driver:
 def __init__(self,world):self.world=world;self.tasks=[];self.sequence=0;self.prefix='bd'+str(int(time.time()));self.error_count=0
 def task(self,action,**options):
  self.sequence+=1;identifier=f'{self.prefix}-{self.sequence}'
  task={'id':identifier,'action':action,'delayTicks':1,**options};self.tasks.append(task);write(CONTROL,{'world':self.world,'tasks':self.tasks})
  deadline=time.time()+300
  while time.time()<deadline:
   status=read(EXPORT/'optimization-control-status.json',{})
   if status.get('world')!=self.world:time.sleep(.3);continue
   value=read(EXPORT/('optimization-'+identifier+'.json'))
   if identifier in status.get('completed',[]) and value:
    write(OUT/(identifier+'.json'),value);return value['result']
   if len(status.get('errors',[]))>self.error_count:
    self.error_count=len(status['errors']);self.tasks.remove(task);write(CONTROL,{'world':self.world,'tasks':self.tasks});raise RuntimeError(status['errors'][-1])
   time.sleep(.3)
  self.tasks.remove(task);write(CONTROL,{'world':self.world,'tasks':self.tasks});raise TimeoutError(identifier)

def collect_baseline():
 rows={}
 for p in (ROOT/'evidence/optimization/run-05-chunky-guard/exports').glob('*.json'):
  d=read(p,{});v=d.get('result',{})
  if not isinstance(v,dict) or 'candidates' not in v or not v.get('structure'):continue
  key=(v['structure'],d.get('dimension','minecraft:overworld'))
  rows[key]={'candidates':len(v['candidates']),'surfaceCompatible':sum(bool(c[2]) for c in v['candidates'])}
 return rows

def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--world',default='Optimization-BossDensity');parser.add_argument('--sets',nargs='*');parser.add_argument('--output',type=Path,default=OUT);parser.add_argument('--keep-open',action='store_true');args=parser.parse_args();OUT=args.output;OUT.mkdir(parents=True,exist_ok=True)
 state=read(EXPORT/'optimization-control-status.json',{});assert state.get('world')==args.world,'Start intended disposable world first'
 probe=read(EXPORT/'optimization-probe.json',{});assert args.world in probe.get('world',''),'Probe belongs to another world'
 catalog=read(ROOT/'evidence/optimization/boss-density-catalog-draft.json')['boss_rows'];definitions=probe['registries']['structure_sets'];boss={r['id']:r for r in catalog};groups=[]
 for set_id,definition in definitions.items():
  members=[e['structure'] for e in definition.get('structures',[]) if e['structure'] in boss]
  if members:groups.append({'id':set_id,'definition':definition,'members':members})
 assert len({x for g in groups for x in g['members']})==len(boss),'Unmapped boss candidate'
 if args.sets:
  groups=[g for g in groups if g['id'] in args.sets]
  assert len(groups)==len(set(args.sets)),'Unknown requested structure set'
 driver=Driver(args.world);baseline=collect_baseline();special=read(INSTANCE/'config/expedition-boss-density.json',{'twilightLandmarkFrequencies':{}})
 before=INSTANCE/'config/structurify.json';snapshot=OUT/'structurify-before.json'
 if not snapshot.exists():snapshot.write_bytes(before.read_bytes())
 report={'world':args.world,'seed':state.get('seed'),'status':'running','radiusBlocks':30000,'targetAcceptedStartsPerBoss':[1,5],'nativeStartsOnly':True,'weightedSelectionAppliedToSharedSets':True,'groups':[],'exceptions':[],'limits':['Candidate catalog still needs encounter audit; no guarantee of all random seeds','Native starts do not place blocks or run boss encounters','Twilight ordinary landmarks and native biome layout retained; map behavior needs separate verification','Feature-based dragon/cyclops/hydra lairs require separate handling']}
 write(OUT/'report.json',report)
 for group in sorted(groups,key=lambda x:x['id']):
  row={'set':group['id'],'members':group['members'],'attempts':[]};report['groups'].append(row);placement=group['definition']['placement'];kind=placement['type'];old_frequency=placement.get('frequency',1.0);spacing=placement.get('spacing',-1);separation=placement.get('separation',0);original=(spacing,separation,old_frequency)
  try:
   if kind=='goety_revelation:church_placement':
    dimensions=['minecraft:the_nether'];frequency=1.0
   else:
    dimensions=sorted({d for member in group['members'] for d in boss[member]['inferred_dimensions']})
    if not dimensions:raise RuntimeError('No dimension identified')
    if kind=='twilightforest:forced_landmark':
     frequency=.001
     row['baselineSummary']={'scope':'Start with a sparse hash filter before native eligibility; avoid enumerating all unthinned Twilight biome checks in one tick.'}
    elif kind=='eternal_starlight:landmark':frequency=.001
    else:
     estimates=[]
     for member in group['members']:
      estimate=sum(baseline.get((member,d),{}).get('surfaceCompatible',0) for d in dimensions)
      if member=='mowziesmobs:frostmaw_spawn':estimate=164
      elif member=='mowziesmobs:wrought_chamber':estimate=9800
      elif member=='mowziesmobs:monastery':estimate=300
      elif member=='mowziesmobs:umvuthana_grove':estimate=140
      elif member.startswith('iceandfire:'):estimate=108
      elif member=='terramity:court_of_gnomes':estimate=58
      elif member=='cataclysm:cursed_pyramid':estimate=5
      estimates.append(max(estimate,1))
     expected=max(estimates) # Shared set chooses one entry, not all entries per candidate.
     frequency=min(1.0,old_frequency*(6 if len(group['members'])>1 else 4)/expected)
   accepted=False
   for revision in range(10):
    if kind=='twilightforest:forced_landmark':
     special['twilightLandmarkFrequencies'][group['id']]=frequency;write(INSTANCE/'config/expedition-boss-density.json',special);driver.task('reloadSpecialDensity')
    elif kind!='goety_revelation:church_placement':driver.task('configureSet',set=group['id'],spacing=spacing,separation=separation,frequency=frequency)
    summary=None
    for summary_dimension in dimensions:
     check=driver.task('placementSummary',structure=group['members'][0],dimension=summary_dimension)
     if check.get('placements'):summary=check;break
    if not summary:raise RuntimeError('No native placements in any inferred dimension')
    if kind=='twilightforest:forced_landmark' and summary['placements'][0].get('structurifySet')!=group['id']:raise RuntimeError('Specialized filter has no correct Structurify identity')
    results=[];counts={m:0 for m in group['members']};complete=True;too_dense=False
    for member in group['members']:
     for dimension in dimensions:
      options={'structure':member,'dimension':dimension,'limit':128,'budgetMs':75,'maxCandidates':5000,'stopAfterValid':10}
      if len(group['members'])>1:options['selection']=group['definition']['structures']
      result=driver.task('validationBatch',**options);results.append({'dimension':dimension,'structure':member,**result});counts[member]+=len(result['validatedStarts']);complete=complete and result['allCandidatesValidated'];too_dense=too_dense or len(result['validatedStarts'])>=10
    attempt={'revision':revision,'frequency':frequency,'spacing':spacing,'separation':separation,'effectivePlacement':summary,'counts':counts,'allCandidatesValidated':complete,'results':results};row['attempts'].append(attempt);write(OUT/'report.json',report)
    if complete and all(1<=c<=5 for c in counts.values()):accepted=True;row['accepted']=attempt;break
    highest=max(counts.values());lowest=min(counts.values())
    if too_dense or highest>5:frequency=max(1e-9,frequency*3.8/highest)
    elif not complete:raise RuntimeError('Candidate cap exceeded before a complete count')
    elif lowest==0:
     if frequency<.999:frequency=min(1.0,frequency*2.5)
     elif spacing>=2:
      new_spacing=max(2,math.floor(spacing*.7));separation=min(new_spacing-1,math.floor(separation*new_spacing/spacing));spacing=new_spacing
     else:raise RuntimeError('No valid starts at full frequency')
    else:raise RuntimeError('Unresolved count pattern')
   if not accepted:raise RuntimeError('Convergence limit; baseline restored for this set')
   row['status']='native_starts_calibrated'
  except Exception as error:
   row['status']='deferred_exception';row['error']=str(error);report['exceptions'].append({'set':group['id'],'error':str(error)})
   try:
    if kind=='twilightforest:forced_landmark':special['twilightLandmarkFrequencies'].pop(group['id'],None);write(INSTANCE/'config/expedition-boss-density.json',special);driver.task('reloadSpecialDensity')
    elif kind!='goety_revelation:church_placement':driver.task('configureSet',set=group['id'],spacing=original[0],separation=original[1],frequency=original[2])
   except Exception as restore_error:row['restoreError']=str(restore_error)
  write(OUT/'report.json',report)
  write(OUT/'status.json',{'completed':len(report['groups']),'total':len(groups),'set':group['id'],'status':row['status'],'exceptions':len(report['exceptions'])})
 report['status']='calibration_pass_finished_pending_reboot_and_encounter_review';write(OUT/'report.json',report)
 driver.task('persistStructurify')
 driver.task('commands',commands=['save-all flush'])
 if not args.keep_open:driver.task('stop')
 print(json.dumps({'groups':len(groups),'accepted':sum(r['status']=='native_starts_calibrated' for r in report['groups']),'exceptions':len(report['exceptions'])}))
if __name__=='__main__':main()
