import unittest
from uep_lyra_characters.hero_parent_test_profiles import defaults

class ParentTestProfileSelectionTests(unittest.TestCase):
    def test_both_parent_and_child_selectors_restore_on_failed_spawn(self):
        data={'UEPHeroDefaultMixinProfile':'Python','PythonMixinProfile':'ChildOriginal'}
        class Cdo:
            def properties(self):return list(data)
            def get_property(self,key):return data[key]
            def set_property(self,key,value):data[key]=value
        class Class:
            def get_cdo(self):return Cdo()
        with self.assertRaisesRegex(RuntimeError,'spawn failed'):
            with defaults(Class(),'BlueprintFallback'):
                self.assertEqual(set(data.values()),{'BlueprintFallback'});raise RuntimeError('spawn failed')
        self.assertEqual(data,{'UEPHeroDefaultMixinProfile':'Python','PythonMixinProfile':'ChildOriginal'})
