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
        (self.directory / 'fgra_spec.json').write_text(json.dumps(spec))
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

if __name__ == '__main__':
    unittest.main()
