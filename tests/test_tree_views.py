import base64
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pob_import as p
import poe_tree as t
from test_importer import XML, TREE


class TreeViewTests(unittest.TestCase):
    def test_point_counts_and_estimates_exclude_ascendancy_and_starts(self):
        tree={'nodes':{'1':{'classStartIndex':4},'2':{},'3':{'ascendancyName':'Slayer','isAscendancyStart':True},'4':{'ascendancyName':'Slayer'},'5':{'ascendancyName':'Ascendant','isMultipleChoiceOption':True}}}
        self.assertEqual(t.point_counts({'nodes':'1,2,3,4,5,999'},tree),(2,1,1))
        result=t.estimate_level({'nodes':'1,2,3,4'},tree)
        self.assertEqual(result['level'],2)
        self.assertTrue(result['approximate'])
        normal={'nodes':{str(i):{} for i in range(1,121)}}
        levels=[t.estimate_level({'nodes':','.join(str(i) for i in range(1,n+1))},normal)['level'] for n in (10,35,72,119)]
        self.assertEqual(levels,sorted(levels))
        self.assertEqual(levels[-1],96)

    def test_review_infers_unlabelled_levels_but_keeps_labels(self):
        draft=p.parse_build(p.decode_build(XML))
        draft['skills'][0]['title']=draft['trees'][0]['title']='Starter'
        with patch.object(p,'tree_data',return_value=TREE):
            rows=p.review_draft(draft)['milestones']
        self.assertEqual(rows[0]['startLevel'],2)
        self.assertEqual(rows[0]['levelSource'],'Estimated from tree')
        self.assertEqual(rows[1]['startLevel'],32)
        self.assertEqual(rows[1]['levelSource'],'Label')

    def test_review_errors_identify_the_row_and_field(self):
        draft=p.parse_build(p.decode_build(XML));rows=p.review_draft(draft)['milestones']
        rows[1]['startLevel']=0
        with self.assertRaises(p.ImportProblem) as caught:p.make_guide(draft,rows,'Test')
        self.assertEqual((caught.exception.row,caught.exception.field),(1,'level'))
        self.assertIn('Level 32',str(caught.exception))
        rows[1]['startLevel']=1
        with self.assertRaises(p.ImportProblem) as caught:p.make_guide(draft,rows,'Test')
        self.assertIn('alternative setup',str(caught.exception))

    def test_diff_separates_ascendancy_and_namespaces_svg_assets(self):
        tree=dict(TREE,nodes=dict(TREE['nodes']))
        tree['nodes']['3']={'group':1,'orbit':0,'orbitIndex':0,'name':'Ascendancy','ascendancyName':'Slayer','isAscendancyStart':True,'out':[4]}
        tree['nodes']['4']={'group':2,'orbit':0,'orbitIndex':0,'name':'Impact','ascendancyName':'Slayer','isNotable':True,'stats':['Test']}
        with patch.object(t,'sprite',return_value='data:image/png;base64,eA=='),patch.object(t,'local_art',return_value=None):
            main,details,delta=t.svg_view(tree,'3_29',{'1','4'},{'2'},'Slayer',True)
            mini,asc,asc_delta=t.svg_view(tree,'3_29',{'1','4'},{'2'},'Slayer',True,True)
        self.assertEqual((delta['added'],delta['removed']),(1,1))
        self.assertNotIn('4',details);self.assertIn('4',asc)
        self.assertEqual(asc_delta['added'],1)
        text=base64.b64decode(main.split(',')[1]).decode()
        asc_text=base64.b64decode(mini.split(',')[1]).decode()
        ET.fromstring(text);ET.fromstring(asc_text)
        self.assertIn('treeAsset0',text);self.assertIn('ascAsset0',asc_text)
        self.assertIn('#ef8c80',text);self.assertIn('#86d5ff',text)

    def test_changes_keeps_distant_previously_allocated_nodes_visible(self):
        tree=dict(TREE,groups={'1':{'x':0,'y':0},'2':{'x':5000,'y':100}})
        with patch.object(t,'sprite',return_value=None),patch.object(t,'local_art',return_value=None):
            image,details,delta=t.svg_view(tree,'3_29',{'1','2'},{'1'},diff=True)
        self.assertEqual(details['1']['state'],'kept')
        self.assertEqual(details['2']['state'],'new')
        self.assertEqual(delta,{'added':1,'removed':0,'kept':1})
        svg=ET.fromstring(base64.b64decode(image.split(',')[1]))
        self.assertTrue(any('L200' not in path.get('d','') and 'L5000' in path.get('d','') for path in svg.findall('{http://www.w3.org/2000/svg}path')))


if __name__=='__main__':unittest.main()
