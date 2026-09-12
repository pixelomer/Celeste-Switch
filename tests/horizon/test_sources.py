"""Exercise actual recursive pinned Git fetching and refusal to overwrite user edits."""
import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
SUPPORT=Path(__file__).resolve().parents[2]/'eng/horizon/support.py'
spec=importlib.util.spec_from_file_location('support',SUPPORT);s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class SourceTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def git(self,path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True,stderr=subprocess.DEVNULL).strip()
 def repo(self,name):
  p=self.root/name;p.mkdir();self.git(p,'init');self.git(p,'config','user.name','GPT-6 Astra');self.git(p,'config','user.email','noreply@openai.com');(p/'owned.txt').write_text('original\n');self.git(p,'add','.');self.git(p,'commit','-m','original fixture');return p
 def test_recursive_gitlinks_and_dirty_child(self):
  child=self.repo('child');parent=self.repo('parent');revision=self.git(child,'rev-parse','HEAD')
  (parent/'.gitmodules').write_text('[submodule "child"]\npath = child\nurl = https://example.invalid/child.git\n')
  self.git(parent,'add','.gitmodules');self.git(parent,'update-index','--add','--cacheinfo','160000,'+revision+',child');self.git(parent,'commit','-m','pin child')
  p_spec={'url':'https://example.invalid/parent.git','revision':self.git(parent,'rev-parse','HEAD')}
  mirrors={p_spec['url']:str(parent),'https://example.invalid/child.git':str(child)}
  target=self.root/'target';target.mkdir()
  s.git_source(p_spec,target,mirrors);s.submodules(target,mirrors)
  self.assertEqual(self.git(target/'child','rev-parse','HEAD'),revision)
  self.assertEqual(self.git(target,'status','--porcelain'),'')
  (target/'child/owned.txt').write_text('user edit\n')
  with self.assertRaises(RuntimeError):s.git_source(p_spec,target,mirrors)
  self.assertEqual((target/'child/owned.txt').read_text(),'user edit\n')
 def test_existing_other_revision_is_preserved(self):
  source=self.repo('source');first=self.git(source,'rev-parse','HEAD');spec={'url':str(source),'revision':first}
  target=s.git_source(spec,self.root/'target')
  (source/'owned.txt').write_text('second\n');self.git(source,'commit','-am','second fixture')
  spec['revision']=self.git(source,'rev-parse','HEAD')
  with self.assertRaises(RuntimeError):s.git_source(spec,target)
  self.assertEqual(self.git(target,'rev-parse','HEAD'),first)
 def test_missing_gitlink_rejected(self):
  source=self.repo('source');(source/'.gitmodules').write_text('[submodule "child"]\npath = child\nurl = https://example.invalid/never-fetch.git\n')
  with self.assertRaises(RuntimeError):s.submodules(source)
if __name__=='__main__':unittest.main()
