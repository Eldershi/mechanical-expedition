import hashlib,importlib.util,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
SNAPSHOT=HERE/'snapshot_current.py'
if not SNAPSHOT.is_file():SNAPSHOT=HERE.parent/'tools/snapshot_current.py'
FILTER=SNAPSHOT.with_name('publication_filter.py')
if not FILTER.is_file():
    FILTER=next(root/'tools/github-sync/publication_filter.py' for root in HERE.parents
                if (root/'tools/github-sync/publication_filter.py').is_file())
SHA=lambda data:hashlib.sha256(data).hexdigest()

class SnapshotExternalReferences(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.project=self.root/'workspace';self.active=self.root/'client';self.repo=self.root/'published';self.server=self.root/'server'
        for p in [self.project,self.active/'mods',self.server/'config',self.repo/'tools']:p.mkdir(parents=True,exist_ok=True)
        (self.project/'AGENTS.md').write_text('当前活动客户端实例为 `'+str(self.active)+'`\n')
        tsv=self.project/'clients/cmi-expedition/distribution/repository/mods.tsv';tsv.parent.mkdir(parents=True);tsv.write_text('')
        for n in ['server-patches.json','server-additions.json']:(self.server/n).write_text('{"mods":[]}')
        (self.server/'config/server.json').write_text('{"ordinary":true}')
        shutil.copy2(SNAPSHOT,self.repo/'tools/snapshot_current.py');shutil.copy2(FILTER,self.repo/'tools/publication_filter.py')
        self.pack='config/paxi/resourcepacks/Private.zip';self.script='kubejs/startup_scripts/90_private_visuals.js'
        self.blobs={self.pack:b'private-resource-art-do-not-copy',self.script:b'console.info("separate repository");'}
        for name,data in self.blobs.items():
            p=self.active/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        (self.active/'config/paxi/resourcepack_load_order.json').write_text('{"loadOrder":["Private.zip"]}')
        public=self.active/'resourcepacks/Public.zip';public.parent.mkdir();public.write_bytes(b'preexisting-public-pack')
        self.manifest=self.repo/'integrations/resourcepacks/external.json';self.manifest.parent.mkdir(parents=True)
        self.entries=[{'path':p,'sha256':SHA(data)}for p,data in self.blobs.items()]
        self.write_manifest(self.entries)
    def tearDown(self):self.tmp.cleanup()
    def write_manifest(self,entries):self.manifest.write_text(json.dumps({'clientFiles':entries}))
    def run_snapshot(self):
        out=self.root/'stage/current-snapshot'
        r=subprocess.run([sys.executable,str(self.repo/'tools/snapshot_current.py'),'--project',str(self.project),'--instance',str(self.active),'--server-source',str(self.server),'--output',str(out)],text=True,capture_output=True)
        return r,out
    def test_verified_external_bytes_not_copied_but_loadorder_preserved(self):
        r,out=self.run_snapshot();self.assertEqual(r.returncode,0,r.stderr)
        for name in self.blobs:self.assertFalse((out/'current/client'/name).exists())
        self.assertEqual((out/'current/client/resourcepacks/Public.zip').read_bytes(),b'preexisting-public-pack')
        report=json.loads((out.parent/'snapshot-result.json').read_text())
        self.assertEqual({p['path']for p in report['externalResourceReferences']},set(self.blobs))
        self.assertEqual(report['resourcePackLoadOrder'],['Private.zip'])
        self.assertFalse(any(r['path']in self.blobs for r in report['files']))
    def test_unknown_missing_pack_not_waived_by_other_reference(self):
        (self.active/'config/paxi/resourcepack_load_order.json').write_text('{"loadOrder":["Unknown.zip"]}')
        r,_=self.run_snapshot();self.assertNotEqual(r.returncode,0);self.assertIn('Configured resource pack was not preserved: Unknown.zip',r.stderr)
    def test_wrong_hash_fails_before_snapshot_created(self):
        self.entries[0]['sha256']='0'*64;self.write_manifest(self.entries)
        r,out=self.run_snapshot();self.assertNotEqual(r.returncode,0);self.assertIn('source hash mismatch',r.stderr);self.assertFalse(out.exists())
    def test_declared_but_missing_source_is_not_accepted(self):
        (self.active/self.pack).unlink();r,out=self.run_snapshot();self.assertNotEqual(r.returncode,0);self.assertIn('source is missing',r.stderr);self.assertFalse(out.exists())
    def test_path_traversal_rejected(self):
        self.write_manifest([{'path':'../Private.zip','sha256':'0'*64}]);r,_=self.run_snapshot();self.assertNotEqual(r.returncode,0);self.assertIn('client-relative path',r.stderr)
    def test_symlinked_declared_source_rejected(self):
        p=self.active/self.pack;p.unlink();target=self.root/'outside.zip';target.write_bytes(self.blobs[self.pack]);p.symlink_to(target)
        r,_=self.run_snapshot();self.assertNotEqual(r.returncode,0);self.assertIn('must not be symlinked',r.stderr)
    def test_workspace_integration_directory_supported(self):
        target=self.project/'integrations/resourcepacks/external.json';target.parent.mkdir(parents=True);shutil.move(self.manifest,target)
        r,_=self.run_snapshot();self.assertEqual(r.returncode,0,r.stderr)
    def test_workspace_repository_integration_directory_supported(self):
        target=self.project/'clients/cmi-expedition/distribution/repository/integrations/resourcepacks/external.json';target.parent.mkdir(parents=True);shutil.move(self.manifest,target)
        r,_=self.run_snapshot();self.assertEqual(r.returncode,0,r.stderr)
    def test_conflicting_manifest_hash_rejected(self):
        another=self.manifest.with_name('conflict.json');another.write_text(json.dumps({'clientFiles':[{'path':self.pack,'sha256':'0'*64}]}))
        r,_=self.run_snapshot();self.assertNotEqual(r.returncode,0)
    def test_source_revalidated_before_loadorder_exception(self):
        spec=importlib.util.spec_from_file_location('staged_snapshot',self.repo/'tools/snapshot_current.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        external=module.external_resource_files(self.project,self.active)
        (self.active/self.pack).write_bytes(b'changed-after-initial-verification')
        with self.assertRaisesRegex(RuntimeError,'Configured external resource pack hash mismatch'):
            module.configured_pack_preserved(self.root/'empty-current-client',self.active,'Private.zip',external)

if __name__=='__main__':unittest.main(verbosity=2)
