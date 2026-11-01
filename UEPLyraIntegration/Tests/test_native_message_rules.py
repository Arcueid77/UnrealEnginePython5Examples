import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
from uep_lyra_native import message_rules as r


class MessageRules(unittest.TestCase):
    def setUp(self):
        self.a,self.b,self.c='A','B','C'
        self.cast=lambda p:p if p in ('A','B','C') else None
        self.tags={2:'double',3:'triple'}

    def streak(self,h,a='A',b='B'):
        return list(r.streak_elimination(h,a,b,self.cast,self.tags))

    def test_streak_counts_and_thresholds(self):
        h={};self.assertEqual(self.streak(h),[])
        self.assertEqual(self.streak(h),[('double','A',2)])
        self.assertEqual(self.streak(h),[('triple','A',3)])
        self.assertEqual(self.streak(h),[]);self.assertEqual(h,{'A':4})

    def test_streak_self_elimination_clears_target(self):
        h={'A':3};self.assertEqual(self.streak(h,'A','A'),[]);self.assertEqual(h,{})

    def test_streak_invalid_instigator_still_clears_victim(self):
        h={'B':3};self.assertEqual(self.streak(h,'other','B'),[]);self.assertEqual(h,{})

    def test_streak_broadcast_precedes_target_clear(self):
        h={'A':1,'B':7};events=r.streak_elimination(h,'A','B',self.cast,self.tags)
        self.assertEqual(next(events),('double','A',2));self.assertEqual(h['B'],7)
        list(events);self.assertNotIn('B',h)

    def chain(self,h,now,window=4.5,a='A',b='B'):
        return list(r.chain_elimination(h,a,b,self.cast,self.tags,lambda:now,window))

    def test_chain_first_elimination_has_no_reward(self):
        h={};self.assertEqual(self.chain(h,10.),[]);self.assertEqual(h,{'A':(10.,1)})

    def test_chain_exact_window_remains_in_chain(self):
        h={'A':(10.,1)};self.assertEqual(self.chain(h,14.5),[('double','A',2)])

    def test_chain_exceeded_window_resets(self):
        h={'A':(10.,3)};self.assertEqual(self.chain(h,14.500001),[]);self.assertEqual(h['A'],(14.500001,1))

    def test_chain_before_window_counts(self):
        h={'A':(10.,1)};self.assertEqual(self.chain(h,14.499),[('double','A',2)])

    def test_chain_zero_last_time_resets_even_with_history(self):
        h={'A':(0.,9)};self.assertEqual(self.chain(h,1.),[]);self.assertEqual(h['A'],(1.,1))

    def test_chain_skips_clock_for_self_or_nonplayer(self):
        def forbidden():raise AssertionError('clock must not be read')
        self.assertEqual(list(r.chain_elimination({},'A','A',self.cast,self.tags,forbidden,4.5)),[])
        self.assertEqual(list(r.chain_elimination({},'x','B',self.cast,self.tags,forbidden,4.5)),[])

    def test_chain_does_not_clear_victim_history(self):
        h={'B':(9.,2)};self.chain(h,10.);self.assertEqual(h['B'],(9.,2))

    def test_chain_zero_window_equal_and_next_time(self):
        h={'A':(10.,1)};self.assertEqual(self.chain(h,10.,0.),[('double','A',2)])
        self.assertEqual(self.chain(h,10.1,0.),[])

    def test_assist_accumulates_float_storage(self):
        h={}
        for _ in range(3):r.assist_damage(h,'A','B',.1,self.cast)
        self.assertEqual(h['B']['A'],r.float32(r.float32(r.float32(.1)+.1)+.1))

    def test_assist_self_damage_is_ignored(self):
        h={};r.assist_damage(h,'A','A',4.,self.cast);self.assertEqual(h,{})

    def test_assist_conversion_occurs_after_raw_identity_comparison(self):
        h={};lookup={'pawn':'A','controller':'A'}.get
        r.assist_damage(h,'pawn','controller',2.,lookup);self.assertEqual(h,{'A':{'A':2.}})

    def test_assist_invalid_source_or_target_is_ignored(self):
        h={};r.assist_damage(h,'x','B',2.,self.cast);r.assist_damage(h,'A','x',2.,self.cast);self.assertEqual(h,{})

    def test_assist_excludes_killer_and_clears_only_victim(self):
        h={'B':{'A':30.,'C':70.},'A':{'C':4.}}
        self.assertEqual(list(r.assist_elimination(h,'C','B',self.cast)),[('A','B',30.)])
        self.assertEqual(h,{'A':{'C':4.}})

    def test_assist_target_must_be_player_state(self):
        h={'B':{'A':30.}};self.assertEqual(list(r.assist_elimination(h,'C','pawn',self.cast)),[]);self.assertIn('B',h)

    def test_assist_broadcast_precedes_clear(self):
        h={'B':{'A':30.,'C':70.}};events=r.assist_elimination(h,'C','B',self.cast)
        self.assertEqual(next(events),('A','B',30.));self.assertIn('B',h)
        list(events);self.assertNotIn('B',h)

    def test_assist_nested_damage_is_cleared_after_broadcast(self):
        h={'B':{'A':30.}};events=r.assist_elimination(h,'C','B',self.cast)
        next(events);r.assist_damage(h,'A','B',4.,self.cast);list(events);self.assertEqual(h,{})

    def test_float_overflow_matches_native_float_storage(self):
        self.assertEqual(r.float32(1e300),math.inf);self.assertEqual(r.float32(-1e300),-math.inf)


if __name__=='__main__':unittest.main()
