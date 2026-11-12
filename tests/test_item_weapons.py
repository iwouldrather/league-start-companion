import unittest
import pob_import as p

class WeaponItemsTests(unittest.TestCase):
    def test_weapon_base_types_and_magic_names(self):
        cases=[('Rusted Hatchet',1),('Jade Hatchet of the Bear',1),('Bastard Sword',2),('Short Bow',2),('Driftwood Wand',1),('Gnarled Branch',2)]
        for base,hands in cases:
            with self.subTest(base=base):self.assertEqual(p.weapon_metadata(base)['hands'],hands)
        for base in ('Jade Amulet','Tower Shield','Unknown Weapon'):
            self.assertEqual(p.weapon_metadata(base),{})

    def test_imported_unique_and_rare_weapons(self):
        for rarity in ('RARE','UNIQUE'):
            item=p.item_record('Weapon 1',f'Rarity: {rarity}\nExample weapon\nRusted Hatchet\nLevelReq: 1\nAdds 1 to 2 Physical Damage')
            self.assertEqual(item['hands'],1)
            self.assertEqual(item['weaponType'],'One Handed Axe')
            self.assertIn('Adds 1 to 2 Physical Damage',item['clean'])

    def test_existing_guide_enrichment_keeps_item_and_progress_fields(self):
        data={'sets':[{'items':[{'base':'Short Bow','slot':'Weapon 1','item':'original','clean':'unchanged'}]}],'progress':{'test':True}}
        p.refresh_item_metadata(data)
        item=data['sets'][0]['items'][0]
        self.assertEqual(item['hands'],2)
        self.assertEqual(item['item'],'original')
        self.assertEqual(item['clean'],'unchanged')
        self.assertEqual(data['progress'],{'test':True})
