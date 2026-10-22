"""Synthetic examples only: no licensed application or database in this suite."""
import importlib.util,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import vb425_php8 as app
PHP=os.environ.get('PHP_BINARY','php')
PROJECT=app.HOME

class TransformTests(unittest.TestCase):
    def transform(self,code):return app.worker({'example.php':code},PHP)['example.php']
    def test_literal_strings_comments_and_method_names(self):
        code=b'''<?php
// each($a); $a{0}; count(null)
$literal='each($a) $a{0}';
$o->count(null); Example::count(null);
function &count(&$a) { return $a; }
'''
        self.assertEqual(self.transform(code),code)
    def test_global_calls_and_constants(self):
        result=self.transform(b'<?php $x=\\count(null); $y=each($a); $s=SAPI_NAME; $v=defined(VB_API);')
        self.assertIn(b'\\vb425_php8_count(null)',result)
        self.assertIn(b'vb425_php8_each($a)',result)
        self.assertIn(b'PHP_SAPI',result)
        self.assertIn(b"defined('VB_API')",result)
    def test_offsets_blocks_properties_and_chains(self):
        self.assertEqual(self.transform(b'<?php if ($ok) { $x=$a{0}{1}; $y=$o->item{2}; }'),b'<?php if ($ok) { $x=$a[0][1]; $y=$o->item[2]; }')
    def test_interpolation_and_literal_array_key(self):
        source=b'''<?php $a=$items[thing]; $s="literal {0} {$a{1}} $items[thing]";'''
        result=self.transform(source)
        self.assertIn(b"$items['thing']",result)
        self.assertIn(b'literal {0} {$a[1]} $items[thing]',result)
    def test_idempotent_transformation(self):
        source=b'<?php $n=count(null); $b=$a{0}; $v=$items[thing];'
        once=self.transform(source)
        self.assertEqual(self.transform(once),once)
    def test_crlf_and_non_utf8_bytes_preserved(self):
        result=self.transform(b'<?php\r\n// caf\xe9\r\n$n=count(null);\r\n')
        self.assertIn(b'// caf\xe9\r\n',result)
        self.assertEqual(result.count(b'\r\n'),3)
    def test_normalisation_does_not_hide_code_edits(self):
        a=b'<?php\n|| # vBulletin 4.2.5 - Licence Number EXAMPLE123\n$x=1;\n'
        b=a.replace(b'EXAMPLE123',b'OTHER456')
        self.assertEqual(app.normal_sha(a),app.normal_sha(b))
        self.assertNotEqual(app.normal_sha(a),app.normal_sha(a.replace(b'$x=1',b'$x=2')))
        self.assertNotEqual(app.normal_sha(a),app.normal_sha(a.replace(b'EXAMPLE123',b'EXAMPLE123 */ $x=9; /*')))

class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='vb425-unit-');self.base=Path(self.tmp.name)
        self.utility=self.base/'utility';self.utility.mkdir();shutil.copytree(PROJECT/'php',self.utility/'php')
        self.root=self.base/'forum';(self.root/'includes').mkdir(parents=True)
        (self.root/'includes/class_core.php').write_text("<?php define('FILE_VERSION','4.2.5');")
        self.source=b'<?php $n=count(null);'
        (self.root/'example.php').write_bytes(self.source)
        after=app.worker({'example.php':self.source},PHP)['example.php']
        (self.utility/'profiles').mkdir()
        profile={'required':['example.php'],'files':{'example.php':{'stock_sha256':app.normal_sha(self.source),'patched_sha256':app.normal_sha(after)}}}
        (self.utility/'profiles/4.2.5.json').write_text(json.dumps(profile))
        self.patch=mock.patch.object(app,'HOME',self.utility);self.patch.start()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def do_apply(self):
        report,changes=app.plan(self.root,PHP)
        return app.apply(self.root,PHP,self.base/'backup',report,changes)
    def test_check_is_read_only(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report,_=app.plan(self.root,PHP)
        self.assertTrue(report['safe_to_apply'])
        self.assertEqual(before,{str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
    def test_apply_repeat_and_restore(self):
        result=self.do_apply();self.assertEqual(result['applied'],3)
        report,changes=app.plan(self.root,PHP);self.assertFalse(changes)
        result=app.restore(self.root,Path(result['backup_run']))
        self.assertEqual(result['restored'],3)
        self.assertEqual((self.root/'example.php').read_bytes(),self.source)
        self.assertFalse((self.root/'includes/vb425_php8_runtime.php').exists())
    def test_customised_file_is_not_overwritten(self):
        custom=self.source+b' // my customisation';(self.root/'example.php').write_bytes(custom)
        report,changes=app.plan(self.root,PHP)
        self.assertFalse(report['safe_to_apply'])
        with self.assertRaises(ValueError):app.apply(self.root,PHP,self.base/'backup',report,changes)
        self.assertEqual((self.root/'example.php').read_bytes(),custom)
    def test_restore_refuses_later_edit_before_any_write(self):
        run=Path(self.do_apply()['backup_run']);(self.root/'example.php').write_bytes(b'<?php // later edit')
        before={str(p):p.read_bytes() for p in self.root.rglob('*.php')}
        with self.assertRaises(ValueError):app.restore(self.root,run)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*.php')})
    def test_edit_between_plan_and_apply_is_not_overwritten(self):
        report,changes=app.plan(self.root,PHP)
        later=self.source+b' // later';(self.root/'example.php').write_bytes(later)
        with self.assertRaises(RuntimeError):app.apply(self.root,PHP,self.base/'backup',report,changes)
        self.assertEqual((self.root/'example.php').read_bytes(),later)
    def test_handled_restore_failure_reinstates_removed_helpers(self):
        run=Path(self.do_apply()['backup_run'])
        before={str(p):p.read_bytes() for p in self.root.rglob('*.php')}
        real=Path.unlink;calls=[0]
        def fail_second(path,*args,**kwargs):
            calls[0]+=1
            if calls[0]==2:raise OSError('Simulated restore failure')
            return real(path,*args,**kwargs)
        with mock.patch.object(Path,'unlink',fail_second):
            with self.assertRaises(OSError):app.restore(self.root,run)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*.php')})
    def test_prepared_backup_recovers_partial_interrupted_application(self):
        run=Path(self.do_apply()['backup_run']);manifest=json.loads((run/'manifest.json').read_text())
        manifest['status']='prepared';(run/'manifest.json').write_text(json.dumps(manifest))
        (self.root/'example.php').write_bytes(self.source)
        (self.root/'includes/vb425_php8_runtime.php').unlink()
        result=app.restore(self.root,run)
        self.assertEqual(result['restored'],1)
        self.assertEqual((self.root/'example.php').read_bytes(),self.source)
        self.assertFalse((self.root/'includes/vb425_php8_transformer.php').exists())
    def test_backup_cannot_be_under_forum_or_public_project(self):
        report,changes=app.plan(self.root,PHP)
        for backup in [self.root/'backups',self.utility/'backups']:
            with self.assertRaises(ValueError):app.apply(self.root,PHP,backup,report,changes)
    def test_unsafe_paths_are_rejected(self):
        for name in ['../outside.php','includes/../../file.php','C:/file.php','includes\\file.php']:
            with self.assertRaises(ValueError):app.safe_path(self.root,name)
    def test_missing_required_file_blocks_application(self):
        (self.root/'example.php').unlink()
        report,_=app.plan(self.root,PHP);self.assertFalse(report['safe_to_apply'])
    def test_partial_write_failure_restores_already_written_files(self):
        real=app.atomic;calls=[0]
        def fail_second(*args,**kwargs):
            calls[0]+=1
            if calls[0]==2:raise OSError('Simulated full disk')
            return real(*args,**kwargs)
        with mock.patch.object(app,'atomic',fail_second):
            with self.assertRaises(OSError):self.do_apply()
        self.assertEqual((self.root/'example.php').read_bytes(),self.source)
        self.assertFalse((self.root/'includes/vb425_php8_runtime.php').exists())
    def test_symlinks_are_rejected(self):
        link=self.root/'linked'
        try:link.symlink_to(self.base,target_is_directory=True)
        except OSError:self.skipTest('Symlink creation unavailable on this system')
        with self.assertRaises(ValueError):app.safe_path(self.root,'linked/file.php')
    def test_exclusive_lock_prevents_overlapping_mutations(self):
        with app.site_lock(self.root):
            with self.assertRaises(ValueError):
                with app.site_lock(self.root):pass
        self.assertFalse((self.root/'.vb425-php8-lock').exists())

if __name__=='__main__':unittest.main()
