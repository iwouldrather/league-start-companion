import unittest
from unittest.mock import patch
import pob_import as p
from test_importer import XML,TREE

class ImportProgressionTests(unittest.TestCase):
    def test_ranges_match_tree_and_switch_at_previous_maximum(self):
        draft=p.parse_build(p.decode_build(XML))
        for i,title in enumerate(('Level 1–12','Level 13–28')):
            draft['skills'][i]['title']=title
            draft['trees'][i]['title']=title.replace('Level ','')
        with patch.object(p,'tree_data',return_value=TREE):review=p.review_draft(draft)
        rows=review['milestones']
        self.assertEqual([r['startLevel'] for r in rows],[1,12])
        self.assertEqual(rows[1]['levelSource'],'Previous bracket maximum')
        self.assertEqual(rows[1]['treeId'],draft['trees'][1]['id'])

    def test_existing_range_guides_and_manual_levels(self):
        data={'sets':[{'title':'1-12','startLevel':1},{'title':'13-28','startLevel':13},{'title':'29-38','startLevel':29}]}
        p.refresh_progression(data)
        self.assertEqual([s['swapLevel'] for s in data['sets']],[1,12,28])
        data['sets'][1].pop('swapLevel')
        data['sets'][1]['startLevel']=16
        p.refresh_progression(data)
        self.assertEqual(data['sets'][1]['swapLevel'],16)
        self.assertEqual(data['sets'][1]['startLevel'],16)

    def test_range_end_switches_to_an_unlabelled_or_gapped_next_step(self):
        for title,level in [('Normal Lab',33),('Level 33-50',33)]:
            data={'sets':[{'title':'Level 1-20','startLevel':1},{'title':title,'startLevel':level}]}
            p.refresh_progression(data)
            self.assertEqual(data['sets'][1]['swapLevel'],20)

    def test_explicit_swap_level_is_preserved(self):
        data={'sets':[{'title':'1-12','startLevel':1,'swapLevel':1},{'title':'13-28','startLevel':13,'swapLevel':13}]}
        p.refresh_progression(data)
        self.assertEqual(data['sets'][1]['swapLevel'],13)

    def test_invalid_and_non_level_labels_are_not_ranges(self):
        for title in ('Act 1','32 points','6 links','Level 40-12','Level 1-101'):
            self.assertIsNone(p.level_bounds(title))
        self.assertEqual(p.level_bounds('Level 12 to 28'),(12,28))
        self.assertEqual(p.level_bounds('Lv. 32'),(32,None))

    def test_missing_name_is_rejected_server_side(self):
        draft=p.parse_build(p.decode_build(XML))
        for name in ('','   ',None):
            with self.assertRaises(p.ImportProblem) as caught:p.make_guide(draft,[{}],name)
            self.assertEqual(caught.exception.field,'name')
