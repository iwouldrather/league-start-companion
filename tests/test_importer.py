import base64
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import zlib
import pob_import as p

XML = '''<PathOfBuilding><Build className="Duelist" ascendClassName="Slayer" level="32" bandit="Alira"/>
<Skills><SkillSet id="1" title="Level 1-12"><Skill enabled="true" slot="Body Armour"><Gem nameSpec="Spectral Throw" gemId="gem" skillId="SpectralThrow" level="1" quality="0"/></Skill></SkillSet><SkillSet id="2" title="Level 32"><Skill enabled="true"><Gem nameSpec="Cyclone" gemId="gem" level="1" quality="0"/></Skill></SkillSet></Skills>
<Tree><Spec title="Level 1-12" treeVersion="3_29" nodes="1"/><Spec title="Level 32" treeVersion="3_29" nodes="1,2"/></Tree>
<Items><Item id="1">Rarity: UNIQUE
Test Staff
Royal Staff
LevelReq: 12
{range:0.5}(10-20)% increased Damage</Item><ItemSet title="Level 1-12"><Slot name="Weapon 1" itemId="1"/></ItemSet><ItemSet title="Level 32"><Slot name="Weapon 1" itemId="1"/></ItemSet></Items><Notes>&lt;/script&gt; &lt;img src=x onerror=alert(1)&gt;</Notes></PathOfBuilding>'''
TREE = {'nodes':{'1':{'group':1,'orbit':0,'orbitIndex':0,'out':[2],'name':'Start'},'2':{'group':2,'orbit':0,'orbitIndex':0,'out':[],'name':'Test notable','isNotable':True,'stats':['10% damage']}},'groups':{'1':{'x':0,'y':0},'2':{'x':200,'y':100}},'constants':{'skillsPerOrbit':[1],'orbitRadii':[0]}}

class ImporterTests(unittest.TestCase):
    def test_library_rename_remove_restore_preserves_the_saved_build(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(p,'tree_data',return_value=TREE):
            library=p.BuildLibrary(folder)
            preview=library.preview(XML)
            build=library.create(preview['draftId'],preview['milestones'],'Original')
            before=library.load(build['id'])
            library.rename(build['id'],'Renamed build')
            self.assertEqual(library.list()[0]['name'],'Renamed build')
            after=library.load(build['id'])
            self.assertEqual(before['sets'],after['sets'])
            self.assertEqual(before['createdAt'],after['createdAt'])
            with self.assertRaises(p.ImportProblem):library.rename(build['id'],' ')
            library.remove(build['id'])
            self.assertEqual(library.list(),[])
            self.assertEqual(library.list(removed=True)[0]['name'],'Renamed build')
            with self.assertRaises(p.ImportProblem):library.load(build['id'])
            p.BuildLibrary(folder).restore(build['id'])
            self.assertEqual(library.load(build['id'])['name'],'Renamed build')
            self.assertEqual(library.list(removed=True),[])
            with self.assertRaises(p.ImportProblem):library.restore(build['id'])
            with self.assertRaises(p.ImportProblem):library.remove('../escape')

    def test_code_decode_and_matching(self):
        code=base64.urlsafe_b64encode(zlib.compress(XML.encode())).decode().rstrip('=')
        preview=p.review_draft(p.parse_build(p.decode_build(code)))
        self.assertEqual([r['startLevel'] for r in preview['milestones']],[1,12])
        self.assertEqual(preview['milestones'][1]['treeId'],'1')
        self.assertEqual(preview['milestones'][0]['itemSetId'],'0')
        self.assertIsNone(p.level_from_title('Act 2'))
        self.assertIsNone(p.level_from_title('20 points'))

    def test_bad_inputs_and_network_boundaries(self):
        for value in ['not a code !', '<PathOfBuilding2/>', '<!DOCTYPE x [<!ENTITY x "x">]><PathOfBuilding/>']:
            with self.assertRaises(p.ImportProblem):p.decode_build(value)
        for value in ['http://pobb.in/test','https://127.0.0.1/test','https://pobb.in.evil.test/x','https://pobb.in@127.0.0.1/x','https://pobb.in/x?url=http://localhost']:
            with self.assertRaises(p.ImportProblem):p.fetch_code(value)
        with patch.object(p,'fetch_code',return_value=XML) as fetch:
            self.assertEqual(p.decode_build('https://pobb.in/test').tag,'PathOfBuilding')
            fetch.assert_called_once()
        bomb=base64.urlsafe_b64encode(zlib.compress(('x'*1000).encode())).decode()
        with patch.object(p,'MAX_XML',100),self.assertRaises(p.ImportProblem):p.decode_build(bomb)

    def test_local_library_generate_reopen_and_safe_html(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(p,'tree_data',return_value=TREE):
            library=p.BuildLibrary(folder)
            preview=library.preview(XML)
            generated=library.create(preview['draftId'],preview['milestones'],'Test guide')
            guide=library.load(generated['id'])
            self.assertEqual(len(guide['sets']),2)
            self.assertEqual(guide['sets'][1]['notables'][0]['name'],'Test notable')
            self.assertIn('15% increased Damage',guide['sets'][0]['items'][0]['clean'])
            self.assertEqual(p.BuildLibrary(folder).list()[0]['name'],'Test guide')
            template='<script id="guideData" type="application/json">{}</script>'
            rendered=library.render(template,generated['id'])
            payload=re.search(r'>(.*)</script>',rendered,re.S)[1]
            self.assertNotIn('</script>',payload)
            self.assertEqual(json.loads(payload)['notes'],'</script> <img src=x onerror=alert(1)>')

    def test_ambiguous_sets_levels_and_unknown_acquisition(self):
        draft=p.parse_build(p.decode_build(XML))
        rows=p.review_draft(draft)['milestones']
        rows[1]['startLevel']=1
        with self.assertRaises(p.ImportProblem):p.make_guide(draft,rows,'Invalid')
        rows[1]['startLevel']=32
        rows[0]['treeId']=''
        with self.assertRaises(p.ImportProblem):p.make_guide(draft,rows,'Missing match')
        rows[0]['treeId']='none'
        draft['build']['className']='Witch'
        with patch.object(p,'tree_data',return_value=TREE):
            guide=p.make_guide(draft,rows,'Witch reference')
        self.assertEqual(guide['acquisition']['Cyclone'][:2],[3,'Siosa'])

if __name__=='__main__':unittest.main()
