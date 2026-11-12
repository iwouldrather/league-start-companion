import copy
import unittest
import pob_import as pob
import gem_acquisition as acquisition


class GemCoverageTests(unittest.TestCase):
    def test_siosa_prices_are_attached_to_the_correct_vendor_option(self):
        catalog=pob.gem_catalog()
        for name,currency in [('Infused Channelling','Scroll of Wisdom'),('Desecrate','Orb of Alteration'),('Fortify','Orb of Chance'),('Molten Shell','Orb of Alteration')]:
            _,options,_=acquisition.resolve(name,catalog[name],'Duelist')
            siosa=next(r for r in options if r['vendor']=='Siosa')
            self.assertEqual(siosa['cost']['amount'],1)
            self.assertEqual(siosa['cost']['currency'],currency)
            self.assertFalse(any(r.get('cost') for r in options if r['vendor']!='Siosa'))

    def test_saved_guides_refresh_when_price_data_was_not_yet_present(self):
        data={'acquisitionVersion':acquisition.snapshot().get('checkedAt'),'build':{'className':'Marauder'},'warnings':[],
              'sets':[{'groups':[{'gems':[{'nameSpec':'Molten Shell','level':'1','quality':'0'}]}]}]}
        refreshed=pob.refresh_acquisition(data)
        siosa=next(r for r in refreshed['acquisitionOptions']['Molten Shell'] if r['vendor']=='Siosa')
        self.assertEqual(siosa['cost']['currency'],'Orb of Alteration')
        self.assertEqual(refreshed['acquisitionVersion'],acquisition.data_version())

    def test_every_catalog_entry_resolves_for_every_base_class(self):
        catalog=pob.gem_catalog()
        self.assertGreaterEqual(len(catalog),821)
        for cls in acquisition.CLASSES:
            for name,meta in catalog.items():
                with self.subTest(character_class=cls,gem=name):
                    route,options,note=acquisition.resolve(name,meta,cls)
                    self.assertNotEqual(route[3],'unknown')
                    self.assertTrue(meta.get('minLevel'))
                    if route[3]=='vendor' and route[1] not in ('Siosa','Lilly Roth'):
                        self.assertTrue(any(cls in row['classes'] and row['vendor']==route[1] and row['quest']==route[2] for row in options))

    def test_class_specific_early_routes_and_universal_fallbacks(self):
        catalog=pob.gem_catalog()
        def route(name,cls):return acquisition.resolve(name,catalog[name],cls)[0]
        self.assertEqual(route('Fireball','Witch')[3],'starter')
        self.assertEqual(route('Fireball','Marauder')[:2],[1,'Nessa'])
        self.assertEqual(route('Fireball','Duelist')[:2],[3,'Siosa'])
        self.assertEqual(route('Cyclone','Duelist')[:2],[3,'Clarissa'])
        self.assertEqual(route('Cyclone','Witch')[:2],[3,'Siosa'])
        self.assertEqual(route('Phase Run','Witch')[:2],[6,'Lilly Roth'])
        self.assertEqual(route('Phase Run','Ranger')[:2],[4,'Petarus and Vanja'])
        self.assertEqual(route('Holy Flame Totem','Templar')[:2],[1,'Nessa'])

    def test_faster_attacks_uses_act_one_vendor_for_every_class(self):
        meta=pob.gem_catalog()['Faster Attacks']
        for cls in acquisition.CLASSES:
            primary,options,_=acquisition.resolve('Faster Attacks',meta,cls)
            self.assertEqual(primary[:4],[1,'Nessa','The Caged Brute','vendor'])
            self.assertFalse(any(r['vendor']=='Yeena' for r in options))
        for cls in acquisition.CLASSES:
            primary,_,_=acquisition.resolve('Faster Casting',pob.gem_catalog()['Faster Casting'],cls)
            self.assertEqual(primary[:4],[2,'Yeena','Sharp and Cruel','vendor'])
        routes=acquisition.snapshot()['gems']['Faster Attacks']['routes']
        fixed=acquisition.corrected_routes('Faster Attacks',routes)
        self.assertEqual(acquisition.corrected_routes('Faster Attacks',fixed),fixed)

    def test_vendor_refresh_adds_missing_class_routes_and_normalizes_locations(self):
        import runpy
        reconcile=runpy.run_path(str(pob.ROOT/'scripts/update-gem-data.py'))['reconcile_routes']
        routes=[{'act':3,'quest':'Sever the Right Hand','vendor':'Nessa','kind':'vendor','classes':['Witch']}]
        matrix=[{'act':3,'quest':'Sever the Right Hand','vendor':'Clarissa','kind':'vendor','classes':['Scion']}]
        merged=reconcile('Firestorm',routes,matrix)
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['vendor'],'Clarissa')
        self.assertEqual(set(merged[0]['classes']),{'Witch','Scion'})
        routes=[{'act':3,'quest':'A Fixture of Fate','vendor':'Siosa','kind':'vendor','classes':['Witch']}]
        matrix=[dict(routes[0],vendor='Clarissa',classes=['Scion'])]
        self.assertEqual(reconcile('Cursed Ground',routes,matrix)[0]['vendor'],'Siosa')

    def test_special_gems_and_effects_are_not_campaign_purchases(self):
        catalog=pob.gem_catalog()
        for name,kind in [('Cyclone of Tumult','transfigured'),('Heavy Strike of Trarthus','trarthus'),('Vaal Fireball','vaal'),('Awakened Added Fire Damage','awakened'),('Empower','drop'),('Portal','special')]:
            self.assertEqual(acquisition.resolve(name,catalog[name],'Scion')[0][3],kind)
        gem,meta=pob.normalize_gem({'skillId':'TriggeredSupportShockwave','nameSpec':'Shockwave'},'Item: staff')
        self.assertTrue(gem['itemGranted'])
        self.assertEqual(acquisition.resolve(gem['nameSpec'],meta,'Witch')[0][3],'item')

    def test_variants_support_names_ids_and_unknown_inputs(self):
        def name(gem):return pob.normalize_gem(gem)[0]['nameSpec']
        self.assertEqual(name({'nameSpec':'Cyclone','variantId':'CycloneAltX','gemId':'gem'}),'Cyclone of Tumult')
        self.assertEqual(name({'nameSpec':'Barrage Support','gemId':'gem'}),'Barrage Support')
        self.assertEqual(name({'nameSpec':'Added Fire Damage Support','gemId':'gem'}),'Added Fire Damage')
        self.assertEqual(name({'variantId':'Fireball','gemId':'gem'}),'Fireball')
        gem,meta=pob.normalize_gem({'nameSpec':'Future unsupported gem','gemId':'unknown'})
        self.assertFalse(gem['itemGranted'])
        self.assertEqual(acquisition.resolve(gem['nameSpec'],meta,'Witch')[0][3],'unknown')

    def test_saved_guides_upgrade_without_losing_reviewed_choices(self):
        data={'name':'Saved Witch','build':{'className':'Witch'},'sets':[{'title':'My step','key':'custom','treeImage':'original-tree','items':[{'slot':'Weapon 1'}],'groups':[{'gems':[{'nameSpec':'Fireball','gemId':'gem'}]}]}],
              'warnings':['Class-specific vendor routes are not verified for this class. Unverified routes will be flagged.']}
        original=copy.deepcopy(data)
        upgraded=pob.refresh_acquisition(data)
        self.assertEqual(upgraded['sets'][0]['treeImage'],original['sets'][0]['treeImage'])
        self.assertEqual(upgraded['sets'][0]['items'],original['sets'][0]['items'])
        self.assertEqual(upgraded['sets'][0]['key'],'custom')
        self.assertEqual(upgraded['acquisition']['Fireball'][3],'starter')
        self.assertFalse(upgraded['warnings'])

    def test_guide_generation_for_each_class_with_unrelated_skills(self):
        for cls in acquisition.CLASSES:
            xml=f'''<PathOfBuilding><Build className="{cls}" ascendClassName="None" level="12" mainSocketGroup="1"/>
            <Skills><SkillSet title="Level 12"><Skill enabled="true" slot="Weapon 1">
            <Gem variantId="Fireball" gemId="gem" level="1"/><Gem nameSpec="Barrage Support" gemId="gem"/>
            <Gem nameSpec="Vaal Fireball" gemId="gem"/><Gem nameSpec="Cyclone" variantId="CycloneAltX" gemId="gem"/>
            </Skill></SkillSet></Skills></PathOfBuilding>'''
            draft=pob.parse_build(pob.decode_build(xml))
            guide=pob.make_guide(draft,pob.review_draft(draft)['milestones'],cls+' test')
            self.assertEqual(guide['build']['className'],cls)
            self.assertEqual(guide['build']['ascendClassName'],'')
            self.assertEqual(len(guide['sets'][0]['groups'][0]['gems']),4)
            self.assertIn('Barrage Support',guide['meta'])
            self.assertIn('Cyclone of Tumult',guide['meta'])
            self.assertEqual(guide['acquisition']['Vaal Fireball'][3],'vaal')
            self.assertFalse(any(r[3]=='unknown' for r in guide['acquisition'].values()))


if __name__=='__main__':unittest.main()
