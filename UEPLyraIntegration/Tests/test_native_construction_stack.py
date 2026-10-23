"""Actual read-only Win64 stack capture;no Unreal process is started."""
import importlib.util,os,struct,tempfile,unittest
from pathlib import Path
from uep_lyra_abilities import native_construction_stack as stack
spec=importlib.util.spec_from_file_location('construction_symbols',Path(__file__).resolve().parents[1]/'Tools/resolve_native_construction_stacks.py')
symbols=importlib.util.module_from_spec(spec);spec.loader.exec_module(symbols)

class NativeConstructionStackTests(unittest.TestCase):
    def test_frame_budget_rejects_unbounded_or_noninteger_inputs(self):
        for value in (0,97,-1,True,3.5,'64'):
            with self.assertRaises(ValueError):stack.capture(value)
    def test_offline_pe_image_range_is_not_the_file_length_or_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.dll';data=bytearray(512);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,128);data[128:132]=b'PE\0\0';struct.pack_into('<I',data,128+24+56,0x40000);path.write_bytes(data)
            self.assertEqual(symbols.image_size(path),0x40000)
    def test_invalid_or_empty_pe_image_cannot_create_symbol_range(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'invalid.dll'
            for data in (b'',b'x'*512,b'MZ'+b'\0'*510):
                path.write_bytes(data)
                with self.assertRaises(ValueError):symbols.image_size(path)
    def test_provenance_distinguishes_reinstancing_duplication_spawn_and_destroy(self):
        self.assertEqual(symbols.provenance(['UWorld::SpawnActor','ALyraGameMode::RestartPlayer']),['native-spawn','native-restart'])
        self.assertEqual(symbols.provenance(['FBlueprintCompileReinstancer::ReinstanceObjects','StaticDuplicateObjectEx']),['blueprint-reinstancing','object-duplication'])
        self.assertEqual(symbols.provenance(['AActor::RerunConstructionScripts','UWorld::DestroyActor']),['construction-rerun','native-destruction'])
        self.assertEqual(symbols.provenance(['UnresolvedOrGenericAllocation']),[])
    def test_changed_module_fingerprint_is_rejected_before_symbol_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'changed.dll';path.write_bytes(b'changed')
            resolver=symbols.Resolver.__new__(symbols.Resolver)
            with self.assertRaisesRegex(ValueError,'changed before resolution'):
                resolver.resolve(dict(address='0x1001',base='0x1000',rva='0x1',module=dict(path=str(path),file_size=1,mtime_ns='0')))
    def test_inconsistent_native_address_math_fails(self):
        resolver=symbols.Resolver.__new__(symbols.Resolver)
        with self.assertRaisesRegex(ValueError,'address/base/offset'):
            resolver.resolve(dict(address='0x1002',base='0x1000',rva='0x1',module=dict(path='unused')))
    def test_different_images_cannot_share_one_process_symbol_base(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'second.dll';path.write_bytes(b'image');stat=path.stat()
            resolver=symbols.Resolver.__new__(symbols.Resolver);resolver.loaded={0x1000:dict(path='another-image.dll')}
            with self.assertRaisesRegex(ValueError,'base reused'):
                resolver.resolve(dict(address='0x1001',base='0x1000',rva='0x1',module=dict(path=str(path),file_size=stat.st_size,mtime_ns=str(stat.st_mtime_ns))))
    @unittest.skipUnless(os.name=='nt','Windows current-thread ABI')
    def test_actual_addresses_match_module_base_plus_offset_without_precision_loss(self):
        result=stack.capture(48);self.assertTrue(0<len(result['frames'])<=48);known=0
        for f in result['frames']:
            self.assertIsInstance(f['address'],str);self.assertGreater(int(f['address'],16),0)
            if f['module']:
                known+=1;self.assertEqual(int(f['address'],16),int(f['base'],16)+int(f['rva'],16))
                self.assertEqual(Path(f['module']['path']).stat().st_size,f['module']['file_size'])
                self.assertEqual(str(Path(f['module']['path']).stat().st_mtime_ns),f['module']['mtime_ns'])
        self.assertGreater(known,0);self.assertEqual(result['pid'],os.getpid())
        for key in ('symbols_resolved_in_unreal','debugger_attached','unreal_state_written'):self.assertFalse(result[key])
    @unittest.skipUnless(os.name=='nt','Windows current-thread ABI')
    def test_repeated_capture_keeps_the_requested_bound(self):
        for _ in range(3):self.assertLessEqual(len(stack.capture(8)['frames']),8)

if __name__=='__main__':unittest.main()
