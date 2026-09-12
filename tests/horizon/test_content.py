"""Check archive boundaries using original miniature input ZIPs, never game data."""
import subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class ContentTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def run_stage(self,names):
  archive=self.root/'input.zip'
  with zipfile.ZipFile(archive,'w') as z:
   for name,data in names:z.writestr(name,data)
  out=self.root/'output'
  return subprocess.run([sys.executable,ROOT/'tools/stage-content/stage.py',archive,out],capture_output=True,text=True),out
 def test_only_content_staged(self):
  result,out=self.run_stage([('Content/a.txt','original fixture'),('Celeste.exe','not a real executable')])
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual((out/'Content/a.txt').read_text(),'original fixture')
  self.assertFalse((out/'Celeste.exe').exists())
 def test_traversal_rejected_before_writing(self):
  result,out=self.run_stage([('Content/../../escaped.txt','escape')])
  self.assertNotEqual(result.returncode,0)
  self.assertFalse(out.exists());self.assertFalse((self.root/'escaped.txt').exists())
 def test_case_collision_rejected(self):
  result,out=self.run_stage([('Content/A.txt','one'),('Content/a.txt','two')])
  self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())
 def test_packager_preserves_existing_output(self):
  out=self.root/'existing';out.mkdir();sentinel=out/'save';sentinel.write_text('retain')
  result=subprocess.run([sys.executable,ROOT/'tools/package/package.py','--output',out,
    '--application',self.root/'absent-app','--content',self.root/'absent-content','--sources-lock',self.root/'absent-lock'],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0);self.assertEqual(sentinel.read_text(),'retain')
if __name__=='__main__':unittest.main()
