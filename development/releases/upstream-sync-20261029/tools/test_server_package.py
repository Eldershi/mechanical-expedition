#!/usr/bin/env python3
"""Disposable selector tests; no instance or server is deployed."""
from pathlib import Path
import io, sys, tempfile, unittest, zipfile
RELEASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE))
import build_server_package as b
import install_client as c

def jar(mod):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('META-INF/mods.toml', 'modLoader="javafml"\nloaderVersion="[47,)"\nlicense="MIT"\n[[mods]]\nmodId="'+mod+'"\nversion="1.0"\n')
    return out.getvalue()

class ServerPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='expedition-server-package-test-')
        self.root = Path(self.tmp.name)
        self.release = self.root/'release'
        self.stage = self.release/'staging'
        self.live = self.release/'evidence/live-before'
        self.server = self.root/'server'
        self.base = self.root/'active-before'
        old = {'kubejs/server_scripts/a.js':b'old', 'kubejs/server_scripts/removed.js':b'removed',
               'config/user.json':b'original', 'mods/old.jar':jar('package_test_mod')}
        for rel, blob in old.items():
            for base in (self.live, self.base, self.server/'instance'):
                self.put(base,rel,blob)
        for rel,blob in {'kubejs/server_scripts/a.js':b'new', 'config/user.json':b'original',
                         'mods/new.jar':jar('package_test_mod')}.items():self.put(self.stage,rel,blob)
        c.write_json(self.release/'evidence/active-before.json', {'instance':str(self.base),
            'files':{rel:{'sha256':c.digest(self.base/rel),'bytes':len(blob)} for rel,blob in old.items()}})
        self.capture()
        self.selected={p.relative_to(self.stage).as_posix():{'source':p,'origin':'merged staging'} for p in b.files(self.stage)}
        self.manifest={'packageId':'test','mods':[{'file':'new.jar','modIds':['package_test_mod']}],
                       'summary':{'fixtureNamesExcluded':['UpstreamMachineSelectionAudit.js']}}
    def tearDown(self):self.tmp.cleanup()
    def put(self,base,rel,blob):
        p=base/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);return p
    def capture(self):
        c.write_json(self.release/'evidence/live-before-manifest.json',{'files':{
            p.relative_to(self.live).as_posix():{'sha256':c.digest(p),'bytes':p.stat().st_size} for p in b.files(self.live)}})
    def delta(self):return b.delta_plan(self.selected,self.manifest,self.live,self.release,self.server)

    def test_known_changes_are_writes_and_original_removal_is_move_to_backup(self):
        d,_=self.delta();ops={r['path']:r for r in d['operations']}
        self.assertFalse(d['conflicts']);self.assertEqual(ops['mods/old.jar']['action'],'move_to_backup')
        self.assertEqual(ops['kubejs/server_scripts/removed.js']['action'],'move_to_backup')
        self.assertIsNone(ops['mods/new.jar']['beforeSha256'])
        self.assertEqual(ops['kubejs/server_scripts/a.js']['beforeSha256'],c.digest(self.live/'kubejs/server_scripts/a.js'))
        self.assertTrue((self.live/'mods/old.jar').exists())
    def test_overlapping_edits_refuse(self):
        self.put(self.live,'kubejs/server_scripts/a.js',b'new live edit');self.capture()
        self.assertEqual([r['path'] for r in self.delta()[0]['conflicts']],['kubejs/server_scripts/a.js'])
    def test_unchanged_target_keeps_latest_server_setting(self):
        self.put(self.live,'config/user.json',b'latest live');self.capture();d,f=self.delta()
        self.assertFalse(d['conflicts']);self.assertEqual(f['config/user.json']['source'].read_bytes(),b'latest live')
        self.assertNotIn('config/user.json',[r['path'] for r in d['operations']])
    def test_custom_controls_client_scripts_and_extra_server_mod_survive_full(self):
        additions=['kubejs/client_scripts/Custom.js','kubejs/config/idle-pregeneration-20261020.json',
                   'kubejs/config/idle-pregeneration-20261020-state.json','mods/custom.jar']
        for rel in additions:self.put(self.live,rel,jar('package_custom') if rel.endswith('.jar') else b'production state')
        self.put(self.live,'kubejs/exported/probe.json',b'generated')
        self.put(self.live,'kubejs/server_scripts/UpstreamMachineSelectionAudit.js',b'fixture')
        self.capture();d,f=self.delta()
        for rel in additions:self.assertIn(rel,f)
        self.assertNotIn('kubejs/exported/probe.json',f)
        self.assertNotIn('kubejs/server_scripts/UpstreamMachineSelectionAudit.js',f)
    def test_unknown_old_mod_cannot_be_removed(self):
        self.put(self.live,'mods/old.jar',jar('package_test_mod')+b'unknown patch');self.capture()
        self.assertIn('mods/old.jar',[r['path'] for r in self.delta()[0]['conflicts']])
    def test_snapshot_tampering_refuses(self):
        self.put(self.live,'config/user.json',b'after capture')
        with self.assertRaisesRegex(c.PatchError,'snapshot SHA changed'):self.delta()
    def test_worldgen_overlays_do_not_rollback_recipes_or_quests(self):
        paths=['kubejs/data/minecraft/worldgen/noise_settings/overworld.json',
               'kubejs/server_scripts/recipes/new.js','config/ftbquests/quests/chapters/steam_railway.snbt']
        for rel in paths:
            self.put(self.stage,rel,b'merged');self.put(self.server/'deployment',rel,b'legacy')
        selected,_,_=b.content(self.stage,self.server/'deployment',set())
        self.assertEqual(selected[paths[0]]['source'].read_bytes(),b'legacy')
        for rel in paths[1:]:self.assertEqual(selected[rel]['source'].read_bytes(),b'merged')
    def test_fixture_and_machine_local_data_cannot_enter_stage_selection(self):
        paths=['server.properties','libraries/a.jar','world/level.dat','kubejs/exported/a.json',
               'kubejs/server_scripts/UpstreamMachineSelectionAudit.js',
               'kubejs/config/idle-pregeneration-20261020.json','kubejs/client_scripts/client.js']
        for rel in paths:self.put(self.stage,rel,b'fixture')
        selected,_,_=b.content(self.stage,self.server/'deployment',{'UpstreamMachineSelectionAudit.js'})
        self.assertFalse(set(paths)&set(selected))
    def test_quest_default_noise_is_equal_but_task_id_change_is_not(self):
        a=self.put(self.root,'a.snbt',b'{order_index:12 quests:[{id:"1234567890123456" tasks:[{id:"1234567890123457" item:"minecraft:stone"}]}]}')
        z=self.put(self.root,'z.snbt',b'{order_index:2 quests:[{id:"1234567890123456" optional:false tasks:[{id:"1234567890123457" item:{id:"minecraft:stone" Count:1 tag:{Damage:0}}}]}]}')
        self.assertEqual(b.quest_semantics(a),b.quest_semantics(z))
        z.write_text(z.read_text().replace('1234567890123457','2234567890123457'))
        self.assertNotEqual(b.quest_semantics(a),b.quest_semantics(z))
    def test_no_final_build_without_passed_runtime_reports(self):
        with self.assertRaisesRegex(c.PatchError,'requires passing'):b.build(self.release)
    def test_hash_is_reproducible_and_content_sensitive(self):
        rows=[{'path':'a','sha256':'1'*64,'bytes':1},{'path':'b','sha256':'2'*64,'bytes':2}]
        self.assertEqual(b.tree_hash(rows),b.tree_hash(list(reversed(rows))))
        self.assertNotEqual(b.tree_hash(rows),b.tree_hash([{**rows[0],'bytes':2},rows[1]]))
    def test_symlink_source_refuses(self):
        p=self.stage/'kubejs/link.js';p.symlink_to(self.stage/'kubejs/server_scripts/a.js')
        with self.assertRaisesRegex(c.PatchError,'Symbolic runtime file'):list(b.files(self.stage))
    def test_full_and_delta_archives_have_only_selected_runtime_bytes(self):
        d,f=self.delta();m={**self.manifest,'summary':dict(self.manifest['summary'])}
        b.refresh_files(m,f);out=self.root/'output';out.mkdir()
        full=b.write_archive(out,f,m,d);small=b.write_archive(out,f,m,d,True)
        for result in (full,small):
            with zipfile.ZipFile(result['archive']) as z:
                self.assertIsNone(z.testzip());self.assertNotIn('mods/old.jar',z.namelist())
                self.assertIn('kubejs/exported/', z.namelist())
                self.assertEqual(z.read('kubejs/exported/'), b'')
                unpacked=self.root/('unpacked-'+Path(result['archive']).stem)
                z.extractall(unpacked)
                self.assertTrue((unpacked/'kubejs/exported').is_dir())
                self.assertEqual(list((unpacked/'kubejs/exported').iterdir()), [])
                self.assertIn('server-delta-manifest.json',z.namelist())
                self.assertEqual(z.read('kubejs/server_scripts/a.js'),b'new')
        with zipfile.ZipFile(small['archive']) as z:self.assertNotIn('config/user.json',z.namelist())
    def test_server_patch_overlay_requires_exact_reviewed_hash(self):
        original=self.stage/'mods/new.jar';patched=original.read_bytes()+b'dedicated patch'
        self.put(self.server/'deployment','mods/new.jar',patched)
        c.write_json(self.server/'deployment/server-patches.json',{'schemaVersion':1,'mods':[{
            'file':'new.jar','patchId':'test-patch','upstreamSha256':c.digest(original),
            'patchedSha256':c.digest(self.server/'deployment/mods/new.jar')}]})
        validation=self.root/'validation';self.put(validation,'mods/new.jar',patched)
        self.put(validation,'mods/old.jar.before-test',b'inactive captured archive')
        _,rows,_,_=b.mods(self.stage,validation,self.server,self.release)
        self.assertEqual(rows[0]['patchId'],'test-patch')
        self.put(validation,'mods/new.jar',original.read_bytes())
        with self.assertRaisesRegex(c.PatchError,'Dedicated patched mod differs'):
            b.mods(self.stage,validation,self.server,self.release)
    def test_quest_ancestor_survives_client_install_before_server_build(self):
        rel='config/ftbquests/quests/chapters/base.snbt'
        old=b'{order_index:12 quests:[{id:"1234567890123456" title:"old" optional:false}]}'
        live=b'{order_index:2 quests:[{id:"1234567890123456" title:"old"}]}'
        new=b'{order_index:12 quests:[{id:"1234567890123456" title:"new" optional:false}]}'
        self.put(self.server/'instance',rel,old);self.put(self.base,rel,old);self.put(self.live,rel,live)
        snap=c.read_json(self.release/'evidence/active-before.json')
        snap['files'][rel]={'sha256':c.digest(self.base/rel),'bytes':len(old)}
        c.write_json(self.release/'evidence/active-before.json',snap)
        self.put(self.base,rel,new)
        source=self.put(self.stage,rel,new);self.selected[rel]={'source':source,'origin':'merged staging'};self.capture()
        delta,_=self.delta();self.assertFalse(delta['conflicts'])
        self.assertIn(rel,[r['path'] for r in delta['operations']])
    def test_stopped_refresh_accepts_controls_and_refuses_recipe_drift(self):
        import shutil
        rel='kubejs/config/idle-pregeneration-20261020.json'
        self.put(self.live,rel,b'{"armed":false}');self.capture()
        fresh=self.root/'stopped'
        shutil.copytree(self.live/'config',fresh/'config')
        shutil.copytree(self.live/'kubejs',fresh/'kubejs')
        self.put(fresh,rel,b'{"armed":false,"centerX":123}')
        d,selected=self.delta();m={}
        b.refresh_controls(selected,m,fresh,self.release)
        self.assertEqual(selected[rel]['source'].read_bytes(),b'{"armed":false,"centerX":123}')
        self.assertFalse(m['stoppedControlRefresh']['nonControlChanges'])
        self.put(fresh,'kubejs/server_scripts/a.js',b'changed beyond control scope')
        with self.assertRaisesRegex(c.PatchError,'non-control changes'):
            b.refresh_controls(selected,m,fresh,self.release)

    def test_spark_temp_cleanup_is_volatile_but_formal_config_is_preserved(self):
        import shutil
        temps=['config/spark/tmp/spark-164de2245727fe-libasyncProfiler.so.tmp',
               'config/spark/tmp/profile-data.jfr.tmp']
        regular='config/spark/config.json'
        self.put(self.live,regular,b'{"enabled":true}')
        self.put(self.live,'kubejs/config/idle-pregeneration-20261020.json',b'{"armed":false}')
        for rel in temps:
            self.put(self.live,rel,b'profiler temp');self.put(self.stage,rel,b'stage temp')
        self.capture();fresh=self.root/'stopped-spark'
        shutil.copytree(self.live/'config',fresh/'config')
        shutil.copytree(self.live/'kubejs',fresh/'kubejs')
        for rel in temps:(fresh/rel).unlink()
        self.put(fresh,'config/spark/tmp/new-runtime-cache.bin',b'new transient')
        delta,selected=self.delta();manifest={}
        b.refresh_controls(selected,manifest,fresh,self.release)
        self.assertEqual(selected[regular]['source'].read_bytes(),b'{"enabled":true}')
        self.assertFalse(any(b.transient_path(rel) for rel in selected))
        self.assertTrue(set(temps).issubset({row['path'] for row in manifest['omittedTransientFiles']}))
        self.assertTrue(all(row['stoppedSha256'] is None for row in manifest['omittedTransientFiles'] if row['path'] in temps))
        chosen,_,_=b.content(self.stage,self.server/'deployment',set())
        self.assertFalse(any(b.transient_path(rel) for rel in chosen))
        self.put(fresh,regular,b'{"enabled":false}')
        with self.assertRaisesRegex(c.PatchError,'non-control changes'):
            b.refresh_controls(selected,manifest,fresh,self.release)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ServerPackageTests))
    c.write_json(RELEASE/'evidence/server-package-tests.json',{'passed':result.wasSuccessful(),'testsRun':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'environment':'Temporary copies only; no live deployment.'})
    raise SystemExit(0 if result.wasSuccessful() else 1)
