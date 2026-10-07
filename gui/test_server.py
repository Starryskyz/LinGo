"""Focused tests of artifact validity, architecture constraints and task adapters."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

module = importlib.util.spec_from_file_location('gui_server', Path(__file__).with_name('server.py'))
server = importlib.util.module_from_spec(module)
sys.modules[module.name] = server
module.loader.exec_module(server)

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.old = (server.STATE, server.JOBS, server.ACTIVE)
        self.tmp_patch = patch.object(server, 'TMP', self.directory)
        self.tmp_patch.start()
        self.templates = self.directory / 'spectemplate'
        self.templates.mkdir()
        self.template_patch = patch.object(server, 'SPEC_TEMPLATES', self.templates)
        self.template_patch.start()
        server.STATE = server.initial()
        server.JOBS = {}
        server.ACTIVE = None
        self.save_patch = patch.object(server, 'save')
        self.save_patch.start()

    def tearDown(self):
        self.save_patch.stop()
        self.tmp_patch.stop()
        self.template_patch.stop()
        server.STATE, server.JOBS, server.ACTIVE = self.old
        self.temp.cleanup()

    def test_import_keeps_instance_configuration(self):
        original = copy.deepcopy(server.STATE['spec'])
        checked = server.checked_spec(copy.deepcopy(original))
        for key in ('fgra_gpes', 'fgra_iobs', 'fgra_cg_gibs', 'fgra_fg_gibs'):
            self.assertEqual(original[key], checked[key])

    def test_invalid_coalesce_and_unified_operation_combination(self):
        spec = copy.deepcopy(server.STATE['spec'])
        spec['fgra_iob_sram_banks_coalesce'] = 5
        with self.assertRaises(ValueError):
            server.checked_spec(spec)
        spec = copy.deepcopy(server.STATE['spec'])
        spec['fgra_gpes'][0][0].update(gpe_mode=1, operations=['MUL', 'FMUL'])
        with self.assertRaises(ValueError):
            server.checked_spec(spec)

    def test_operation_catalog_excludes_memory_and_opcode_table(self):
        ops = server.operations()
        self.assertTrue({'FADD', 'FCMP', 'ACC', 'ISEL', 'XCORE'} <= set(ops))
        self.assertFalse({'TLOAD', 'TCLOAD', 'CINPUT', 'OPC'} & set(ops))

    def test_names_cannot_escape_benchmark_directory(self):
        for name in ('../test', 'a/b', 'a;echo', '', '.hidden'):
            with self.assertRaises(ValueError):
                server.bench(name)

    def test_unknown_task_does_not_block_future_tasks(self):
        with self.assertRaises(ValueError):
            server.start('unknown', {})
        self.assertIsNone(server.ACTIVE)

    def test_external_spec_edit_invalidates_hardware(self):
        spec = copy.deepcopy(server.STATE['spec'])
        spec['fgra_gib_num_track_cg'] += 1
        server.spec_path().write_text(json.dumps(spec))
        self.assertEqual(server.snapshot()['spec']['fgra_gib_num_track_cg'], spec['fgra_gib_num_track_cg'])
        self.assertEqual(server.STATE['step'], 0)

    def test_load_spec_preserves_instances_and_invalidates_old_rtl(self):
        original = copy.deepcopy(server.STATE['spec'])
        server.STATE['rtl'] = {'hash': server.digest(original), 'dir': str(self.directory), 'job': 'rtl1'}
        spec = copy.deepcopy(original)
        spec['fgra_iobs'][0][0]['max_delay_cg'] = 9
        spec['fgra_cg_gibs'][0][0]['fclist'] = [4, 4, 2]
        path = self.templates / 'custom.json'
        path.write_text(json.dumps(spec))
        before = path.read_bytes()
        self.assertEqual(server.spec_templates(), ['custom.json'])
        server.apply_spec(server.load_spec_template('custom.json'))
        self.assertEqual(server.STATE['draft'], spec)
        self.assertEqual(server.STATE['spec']['fgra_cg_gibs'][0][0]['fclist'], [4, 4, 2])
        self.assertFalse(server.snapshot()['rtl_current'])
        self.assertEqual(path.read_bytes(), before)

    def test_invalid_template_does_not_replace_current_state(self):
        original = copy.deepcopy(server.STATE)
        (self.templates / 'broken.json').write_text('{invalid json')
        with self.assertRaises(ValueError):
            server.apply_spec(server.load_spec_template('broken.json'))
        self.assertEqual(server.STATE, original)

    def test_template_paths_and_external_symlinks_are_rejected(self):
        outside = self.directory / 'outside.json'
        outside.write_text(json.dumps(server.STATE['spec']))
        (self.templates / 'linked.json').symlink_to(outside)
        self.assertEqual(server.spec_templates(), [])
        for name in ('../outside.json', 'linked.json', '/etc/passwd', None):
            with self.assertRaises(ValueError):
                server.load_spec_template(name)

    def test_rtl_and_dfg_version_invalidation(self):
        source = self.directory / 'demo.c'
        source.write_text('void kernel() {}')
        dfg = self.directory / 'demo.json'
        dfg.write_text('{}')
        server.STATE['rtl'] = {'hash': server.digest(server.STATE['spec']), 'dir': str(self.directory), 'job': 'rtl1'}
        for path in server.rtl_outputs(self.directory):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
        compiled = {'job': 'compile1', 'dfg': str(dfg), 'source_hash': server.digest(source.read_text()), 'compiler': 'llvm'}
        server.STATE['compile']['demo'] = compiled
        server.JOBS['compile1'] = {'id': 'compile1', 'kind': 'compile', 'name': 'demo', 'status': 'succeeded'}
        with patch.object(server, 'bench', return_value=self.directory), patch.object(server, 'benchmarks', return_value=['demo']):
            self.assertTrue(server.compile_current('demo', compiled))
            server.JOBS['compile2'] = {'id': 'compile2', 'kind': 'compile', 'name': 'demo', 'status': 'failed'}
            self.assertFalse(server.compile_current('demo', compiled))
            del server.JOBS['compile2']
            source.write_text('void kernel() { return; }')
            self.assertFalse(server.compile_current('demo', compiled))
            self.assertTrue(server.snapshot()['rtl_current'])
            server.STATE['spec']['fgra_gib_num_track_cg'] += 1
            self.assertFalse(server.snapshot()['rtl_current'])

    def mapping_fixture(self, failure=0):
        directory = self.directory
        (directory / 'result').mkdir()
        for filename, value in [('mappingFailureRate', failure), ('ii', 2), ('latency', 7)]:
            (directory / 'result' / (filename + '.txt')).write_text(str(value))
        (directory / 'mapped_adg.dot').write_text('digraph { GPE1 -> GPE2 }')
        (directory / 'mapped_dfg.dot').write_text('digraph { a -> b }')
        (directory / 'mapped_adg.json').write_text('{}')
        (directory / 'config.bit').write_text('bits')
        (directory / 'demo_cocotb.py').write_text('async def demo(runtime): pass')
        dfg = directory / 'input.json'
        dfg.write_text('{}')
        server.STATE['compile']['demo'] = {'job': 'compile1', 'dfg': str(dfg)}
        server.STATE['rtl'] = {'dir': str(directory), 'hash': 'rtlhash'}
        job = {'id': 'map1', 'kind': 'mapping', 'dir': str(directory), 'log': '', '_started': server.time.monotonic()}
        return job

    def test_mapper_zero_exit_with_failure_is_rejected(self):
        job = self.mapping_fixture(failure=1)
        with patch.object(server, 'run'):
            server.worker(job, {'name': 'demo', 'backend': 'all'})
        self.assertEqual(job['status'], 'failed')
        self.assertIn('did not find a valid mapping', job['error'])
        self.assertNotIn('demo', server.STATE['mapping'])

    def test_mapper_success_records_metrics_and_uses_available_layout(self):
        job = self.mapping_fixture()
        with patch.object(server, 'run') as run:
            server.worker(job, {'name': 'demo', 'backend': 'all'})
        self.assertEqual(job['status'], 'succeeded')
        result = server.STATE['mapping']['demo']
        self.assertEqual((result['ii'], result['latency']), (2, 7))
        self.assertTrue(any('-Kdot' in call.args[1] for call in run.call_args_list))

    def test_save_spec_requires_explicit_overwrite_and_preserves_instances(self):
        spec = copy.deepcopy(server.STATE['draft'])
        spec['fgra_iobs'][0][0]['max_delay_cg'] = 9
        self.assertEqual(server.save_spec_template('custom', spec), {'saved': True, 'name': 'custom.json'})
        before = (self.templates / 'custom.json').read_bytes()
        changed = copy.deepcopy(spec)
        changed['fgra_gib_num_track_cg'] += 1
        self.assertTrue(server.save_spec_template('custom', changed)['exists'])
        self.assertEqual((self.templates / 'custom.json').read_bytes(), before)
        self.assertTrue(server.save_spec_template('custom', changed, overwrite=True)['saved'])
        loaded = server.load_spec_template('custom.json')
        self.assertEqual(loaded['fgra_iobs'][0][0]['max_delay_cg'], 9)
        self.assertEqual(loaded['fgra_gib_num_track_cg'], changed['fgra_gib_num_track_cg'])

    def test_save_spec_rejects_paths_and_symlinks(self):
        for name in ('../escape', '/tmp/escape', '', '.hidden', 'a/b'):
            with self.assertRaises(ValueError):
                server.save_spec_template(name, server.STATE['draft'])
        (self.templates / 'linked.json').symlink_to(self.directory / 'outside.json')
        with self.assertRaises(ValueError):
            server.save_spec_template('linked', server.STATE['draft'], overwrite=True)

    def built_fixture(self):
        rtl = self.directory / 'hardware/rtl'
        for path in server.rtl_outputs(rtl):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
        server.STATE['rtl'] = {'hash': server.digest(server.STATE['spec']), 'dir': str(rtl), 'job': 'rtl1',
            'input_hash': server.rtl_inputs(), 'output_hash': server.files_hash(server.rtl_outputs(rtl))}
        executable = self.directory / 'verification/build/sim_build/Vtop'
        executable.parent.mkdir(parents=True)
        executable.write_text('model')
        model = {'job': 'build1', 'input_hash': server.build_inputs(), 'executable': str(executable),
            'executable_hash': server.file_hash(executable)}
        server.verification_state()['build'] = model
        return model

    def test_build_reuses_model_and_detects_rtl_or_binary_changes(self):
        model = self.built_fixture()
        with patch.object(server.threading, 'Thread') as thread:
            result = server.start('verilator', {})
        self.assertTrue(result['cached'])
        self.assertEqual(result['id'], model['job'])
        thread.assert_not_called()
        self.assertTrue(server.snapshot()['verification']['built'])
        Path(model['executable']).write_text('changed model')
        self.assertFalse(server.snapshot()['verification']['built'])
        Path(model['executable']).write_text('model')
        Path(server.STATE['rtl']['dir'], 'clean.v').write_text('changed RTL')
        self.assertFalse(server.snapshot()['rtl_current'])
        self.assertFalse(server.snapshot()['verification']['built'])

    def test_build_overwrites_only_build_folder_and_preserves_test_edits(self):
        model = self.built_fixture()
        old = Path(model['executable']).parent.parent / 'obsolete.txt'
        old.write_text('old build')
        server.save_verification_source('demo', '# user edit\n')
        Path(model['executable']).unlink()
        with patch.object(server.threading, 'Thread'):
            result = server.start('verilator', {})
        self.assertFalse(result.get('cached', False))
        self.assertFalse(old.exists())
        self.assertEqual(server.test_path('demo').read_text(), '# user edit\n')
        self.assertEqual(Path(server.JOBS[result['id']]['dir']), self.directory / 'verification/build')

    def test_test_template_substitution_saving_and_syntax_validation(self):
        source = server.verification_source('gemm')
        self.assertIn('from gemm import gemm', source)
        self.assertNotIn('example', source)
        edited = source + '\n# user changes\n'
        server.save_verification_source('gemm', edited)
        self.assertEqual(server.verification_source('gemm'), edited)
        with self.assertRaises(SyntaxError):
            server.save_verification_source('gemm', 'def broken(')
        self.assertEqual(server.verification_source('gemm'), edited)
        with self.assertRaises(ValueError):
            server.save_verification_source('hyphen-name', source)

    def test_verification_requires_built_model_current_mapping_and_saved_test(self):
        self.built_fixture()
        with self.assertRaisesRegex(ValueError, 'current mapping'):
            server.start('verification', {'name': 'demo'})
        server.verification_state()['build'] = None
        with self.assertRaisesRegex(ValueError, 'Build Verilator'):
            server.start('verification', {'name': 'demo'})

    def test_compile_fingerprint_tracks_kernel_options_and_included_headers(self):
        source = self.directory / 'source'
        source.mkdir()
        (source / 'demo.c').write_text('#include "values.h"\nvoid kernel() {}')
        header = source / 'values.h'
        header.write_text('#define SIZE 8')
        with patch.object(server, 'bench', return_value=source):
            first = server.compile_inputs('demo', {'compiler': 'llvm', 'kernel': 'kernel'})
            self.assertNotEqual(first, server.compile_inputs('demo', {'compiler': 'llvm', 'kernel': 'other'}))
            header.write_text('#define SIZE 16')
            self.assertNotEqual(first, server.compile_inputs('demo', {'compiler': 'llvm', 'kernel': 'kernel'}))

    def test_compile_reuses_identical_inputs_and_replaces_changed_outputs(self):
        self.built_fixture()
        source = self.directory / 'source'
        source.mkdir()
        (source / 'demo.c').write_text('void kernel() {}')
        output = self.directory / 'benchmarks/demo/compile'
        (output / 'work').mkdir(parents=True)
        dfg = output / 'work/demo.json'
        dfg.write_text('{}')
        (output / 'dfg.svg').write_text('<svg/>')
        marker = output / 'old-output.txt'
        marker.write_text('old result')
        payload = {'name': 'demo', 'compiler': 'llvm', 'kernel': 'kernel'}
        with patch.object(server, 'bench', return_value=source), patch.object(server.threading, 'Thread') as thread:
            server.STATE['compile']['demo'] = {'job': 'compile1', 'dfg': str(dfg), 'compiler': 'llvm',
                'kernel': 'kernel', 'source_hash': server.digest((source / 'demo.c').read_text()),
                'input_hash': server.compile_inputs('demo', payload), 'dfg_hash': server.file_hash(dfg)}
            # Regenerated RTL resets stored progress, but LLVM output survives.
            server.STATE['step'] = 1
            server.STATE['spec']['fgra_gib_num_track_cg'] += 1
            server.STATE['draft'] = copy.deepcopy(server.STATE['spec'])
            self.assertTrue(server.compile_current('demo', server.STATE['compile']['demo']))
            self.assertEqual(server.snapshot()['step'], 0)
            server.STATE['rtl'].update(hash=server.digest(server.STATE['spec']), input_hash=server.rtl_inputs())
            self.assertEqual(server.snapshot()['step'], 2)
            result = server.start('compile', payload)
            self.assertTrue(result['cached'])
            self.assertEqual(server.snapshot()['step'], 2)
            self.assertTrue(marker.is_file())
            thread.assert_not_called()
            result = server.start('compile', dict(payload, kernel='other'))
            self.assertFalse(result.get('cached', False))
            self.assertFalse(marker.exists())
            self.assertEqual(Path(server.JOBS[result['id']]['dir']), output)
            thread.assert_called_once()

    def test_legacy_migration_preserves_current_results_and_archives_old_runs(self):
        old = self.directory / 'runs'
        rtl = old / 'rtl1/hardware'
        for path in server.rtl_outputs(rtl):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
        compile_dir = old / 'compile1'
        (compile_dir / 'work').mkdir(parents=True)
        dfg = compile_dir / 'work/demo.json'
        dfg.write_text('{"result":"compile"}')
        mapdir = old / 'map1'
        mapdir.mkdir()
        (mapdir / 'config.bit').write_text('mapped bits')
        obsolete = old / 'old1'
        obsolete.mkdir()
        (obsolete / 'run.log').write_text('previous result')
        server.STATE['rtl'] = {'dir': str(rtl), 'job': 'rtl1'}
        server.STATE['compile']['demo'] = {'job': 'compile1', 'dfg': str(dfg)}
        server.STATE['mapping']['demo'] = {'job': 'map1'}
        for ident, kind in [('rtl1', 'rtl'), ('compile1', 'compile'), ('map1', 'mapping'), ('old1', 'compile')]:
            server.JOBS[ident] = {'id': ident, 'kind': kind, 'dir': str(old / ident), 'status': 'succeeded'}
        (self.directory / 'fgra_spec.json').write_text('{}')
        server.migrate_outputs()
        self.assertFalse(old.exists())
        self.assertEqual(Path(server.STATE['rtl']['dir']), self.directory / 'hardware/rtl')
        self.assertEqual(Path(server.STATE['compile']['demo']['dfg']).read_text(), '{"result":"compile"}')
        self.assertEqual(Path(server.STATE['mapping']['demo']['dir'], 'config.bit').read_text(), 'mapped bits')
        self.assertEqual(Path(server.JOBS['old1']['dir'], 'run.log').read_text(), 'previous result')
        self.assertTrue(server.spec_path().is_file())

    def test_verification_requires_saved_script_and_rejects_external_script_edits(self):
        ready = {'rtl_current': True, 'dirty': False, 'verification': {'built': True, 'benchmarks': ['demo']}}
        with patch.object(server, 'snapshot', return_value=ready):
            with self.assertRaisesRegex(ValueError, 'Save the test script'):
                server.start('verification', {'name': 'demo'})
            server.save_verification_source('demo', '# saved\n')
            with self.assertRaisesRegex(ValueError, 'saved test script changed'):
                server.start('verification', {'name': 'demo', 'test_source': '# older editor\n'})

    def test_mapping_fingerprint_tracks_backend_dfg_and_rtl(self):
        self.built_fixture()
        dfg = self.directory / 'demo.json'
        dfg.write_text('{}')
        server.STATE['compile']['demo'] = {'dfg': str(dfg)}
        first = server.mapping_inputs('demo', {'backend': 'all'})
        self.assertNotEqual(first, server.mapping_inputs('demo', {'backend': 'sdk'}))
        dfg.write_text('{"nodes":[]}')
        self.assertNotEqual(first, server.mapping_inputs('demo', {'backend': 'all'}))

    def test_zero_exit_simulation_with_failed_xml_is_rejected(self):
        self.built_fixture()
        build = self.directory / 'verification/build'
        (build / 'workspace').mkdir()
        server.save_verification_source('demo', '# test\n')
        mapdir = self.directory / 'benchmarks/demo/map'
        mapdir.mkdir(parents=True)
        (mapdir / 'demo_cocotb.py').write_text('# mapped kernel')
        server.STATE['mapping']['demo'] = {'dir': str(mapdir), 'job': 'map1'}
        output = self.directory / 'verification/results/demo'
        output.mkdir(parents=True)
        (output / 'results.xml').write_text('<testsuite><testcase><failure message="Mismatch"/></testcase></testsuite>')
        job = {'id': 'run1', 'kind': 'verification', 'dir': str(output), 'log': '', '_started': server.time.monotonic()}
        with patch.object(server, 'run'):
            server.worker(job, {'name': 'demo'})
        self.assertEqual(job['status'], 'failed')
        self.assertIn('Simulation failed', job['error'])
        self.assertNotIn('demo', server.verification_state()['runs'])

if __name__ == '__main__':
    unittest.main()
