"""Recompile may reorder sibling CDO subobjects but must not alter their data."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from explorer_character_cdo import canonical_cdo

def cdo(parts):return 'Begin Object Class=Actor Name="Root"\n'+parts+'\nEnd Object'
CAMERA='Begin Object Name="Camera"\nField=1\nEnd Object\n'
MESH='Begin Object Name="Mesh"\nField=2\nEnd Object\n'
class ExplorerCharacterCDOTests(unittest.TestCase):
    def test_reordered_sibling_subobjects_compare_equal(self):self.assertEqual(canonical_cdo(cdo(CAMERA+MESH)),canonical_cdo(cdo(MESH+CAMERA)))
    def test_property_change_is_detected(self):self.assertNotEqual(canonical_cdo(cdo(MESH)),canonical_cdo(cdo(MESH.replace('Field=2','Field=3'))))
    def test_object_identity_and_archetype_are_not_discarded(self):
        self.assertNotEqual(canonical_cdo(cdo(CAMERA)),canonical_cdo(cdo(CAMERA.replace('Name="Camera"','Name="Camera" Archetype="Other"'))))
    def test_nested_ownership_is_not_flattened(self):self.assertNotEqual(canonical_cdo(cdo(CAMERA+MESH)),canonical_cdo(cdo(CAMERA.replace('End Object',MESH+'End Object'))))
    def test_unbalanced_or_multiple_roots_rejected(self):
        for text in ('End Object',cdo(CAMERA)+'\n'+cdo(MESH),'Begin Object Name="Root"'):
            with self.subTest(text=text),self.assertRaises(ValueError):canonical_cdo(text)
