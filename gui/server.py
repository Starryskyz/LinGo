#!/usr/bin/env python3
"""Local LinGo workbench. Python standard library only."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / 'gui'
TMP = GUI / 'tmp'
TMP.mkdir(exist_ok=True)
MODULE = importlib.util.spec_from_file_location('spec_builder', ROOT / 'hardware/generate_fgra_spec.py')
builder = importlib.util.module_from_spec(MODULE)
import sys
sys.modules[MODULE.name] = builder
MODULE.loader.exec_module(builder)
LOCK = threading.RLock()
JOBS = {}
ACTIVE = None
PROC = None
STATE_FILE = TMP / 'state.json'
SOURCE_SPEC = ROOT / 'hardware/src/main/resources/fgra_spec.json'
SPEC_TEMPLATES = ROOT / 'hardware/spectemplate'
MODEL_FILES = ['Makefile', 'circuits/test_cgra.v', 'circuits/LinGoWithAXI.v',
               'circuits/axilite_spec.json', 'circuits/lingo_cgra_adg.json',
               'sim_build/Vtop.mk', 'sim_build/Vtop_classes.mk']

def spec_path():
    path = TMP / 'hardware/fgra_spec.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def file_hash(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def files_hash(paths):
    return digest({str(p): file_hash(p) for p in sorted(map(Path, paths))})

def tool_stamp(name, search_path=None):
    path = name if Path(name).is_file() else shutil.which(name, path=search_path or env_tools()['PATH'])
    if not path:
        conda = shutil.which('conda')
        candidate = Path(conda).parent.parent / 'envs/lingo/bin' / name if conda else None
        path = str(candidate) if candidate and candidate.is_file() else None
    if not path:
        return None
    stat = Path(path).stat()
    return [path, stat.st_size, stat.st_mtime_ns]

def rtl_inputs():
    return digest({'spec': STATE['spec'], 'sources': files_hash(
        list((ROOT / 'hardware/src/main/scala').rglob('*.scala')) +
        [ROOT / 'hardware/build.sbt'] + list((ROOT / 'hardware/project').glob('*.sbt')))})

def rtl_outputs(directory):
    directory = Path(directory)
    return [directory / 'clean.v', directory / 'LinGoWithAXI.v'] + [directory / 'lingo-spec' / name
        for name in ('lingo_adg.json', 'operations.json', 'axilite_spec.json', 'lingo_spec.json')]

def compile_inputs(name, payload):
    paths = [p for p in bench(name).rglob('*') if p.is_file() and p.suffix in ('.c', '.h', '.hpp')]
    compiler = payload.get('compiler', 'llvm')
    return digest({'sources': files_hash(paths), 'compiler': compiler, 'kernel': payload.get('kernel', 'kernel'),
        'adapter': file_hash(ROOT / 'benchmarks' / ('compile.sh' if compiler == 'llvm' else 'mlirCompile.sh')),
        'tools': [tool_stamp(name) for name in (['clang-15', 'opt', str(ROOT / 'compiler/build/llvm-pass/libCDFGPass.so')]
                  if compiler == 'llvm' else ['cgeist', str(ROOT / 'adora/build/bin/cgra-opt')])],
        'scripts': files_hash([ROOT / 'adora/tools/adoracc/adoracc.py', ROOT / 'adora/scripts/cdfg_to_lingo.py']) if compiler == 'mlir' else None,
        'rtl': files_hash(rtl_outputs(STATE['rtl']['dir'])) if compiler == 'mlir' else None})

def mapping_inputs(name, payload):
    return digest({'dfg': file_hash(STATE['compile'][name]['dfg']),
        'rtl': files_hash(rtl_outputs(STATE['rtl']['dir'])), 'backend': payload.get('backend', 'all'),
        'mapper': tool_stamp(str(ROOT / 'mapper/build/mapperPro'))})

def build_inputs():
    rtl = STATE.get('rtl')
    if not rtl:
        return None
    sim_path = simulation_env()['PATH']
    return digest({'rtl': files_hash(rtl_outputs(rtl['dir'])),
        'build_options': {'optimization': 'O0', 'jobs': 4, 'standard': 'c++17'},
        'makefile': file_hash(ROOT / 'simulation/Makefile'),
        'testbench': file_hash(ROOT / 'simulation/circuits/test_cgra.v'),
        'verilator': tool_stamp('verilator', sim_path), 'cocotb': tool_stamp('cocotb-config', sim_path),
        'cxx': tool_stamp(simulation_cxx())})

def verification_state():
    return STATE.setdefault('verification', {'build': None, 'runs': {}})

def test_path(name):
    bench(name)
    return TMP / 'verification/tests' / name / 'test_cgra.py'

def verification_source(name):
    path = test_path(name)
    return path.read_text() if path.is_file() else (ROOT / 'simulation/workspace/test_cgra_template.py').read_text().replace('example', name)

def save_verification_source(name, source):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name or ''):
        raise ValueError('Python simulation benchmark names cannot contain hyphens')
    if not isinstance(source, str):
        raise ValueError('Test source must be text')
    ast.parse(source)
    path = test_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)

def save_spec_template(name, spec, overwrite=False):
    if not isinstance(name, str):
        raise ValueError('Use letters, digits, _, - or . for the spec name')
    if not name.endswith('.json'):
        name += '.json'
    if not re.fullmatch(r'\w[\w.-]{0,127}', name):
        raise ValueError('Use letters, digits, _, - or .; the filename must be at most 128 characters')
    SPEC_TEMPLATES.mkdir(parents=True, exist_ok=True)
    path = SPEC_TEMPLATES / name
    if path.is_symlink() or path.resolve().parent != SPEC_TEMPLATES.resolve():
        raise ValueError('Invalid spec path')
    spec = checked_spec(copy.deepcopy(spec))
    if path.exists() and not overwrite:
        return {'exists': True, 'name': name}
    if overwrite:
        pending = path.with_suffix('.pending')
        pending.write_bytes(builder.render_spec(spec))
        pending.replace(path)
    else:
        try:
            with path.open('xb') as out:
                out.write(builder.render_spec(spec))
        except FileExistsError:
            return {'exists': True, 'name': name}
    return {'saved': True, 'name': name}

def spec_templates():
    return sorted(p.name for p in SPEC_TEMPLATES.glob('*.json')
                  if p.is_file() and p.resolve().parent == SPEC_TEMPLATES.resolve())

def load_spec_template(name):
    if not isinstance(name, str) or name not in spec_templates():
        raise ValueError('Select a JSON spec from hardware/spectemplate')
    return checked_spec(json.loads((SPEC_TEMPLATES / name).read_text()))

def apply_spec(spec):
    spec = checked_spec(copy.deepcopy(spec))
    spec_path().write_bytes(builder.render_spec(spec))
    STATE['draft'] = copy.deepcopy(spec)
    STATE['spec'] = spec
    if not STATE['rtl'] or digest(spec) != STATE['rtl']['hash']:
        STATE['step'] = 0

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def atomic_json(path, value):
    temp = path.with_suffix('.pending')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)

def initial():
    spec = json.loads(SOURCE_SPEC.read_text())
    return {'draft': spec, 'spec': spec, 'rtl': None, 'compile': {}, 'mapping': {}, 'step': 0}

STATE = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else initial()

def save():
    atomic_json(STATE_FILE, STATE)

def checked_spec(spec):
    builder.validate_spec(spec)
    for field in ('fgra_gib_num_track_cg', 'fgra_gib_num_track_fg'):
        if type(spec[field]) is not int or spec[field] < 0:
            raise ValueError(field + ' must be a non-negative integer')
    if spec['fgra_num_row'] < 1 or spec['fgra_num_colum'] < 1:
        raise ValueError('Array dimensions must be positive')
    col = spec['fgra_num_colum']
    coalesce = spec['fgra_iob_sram_banks_coalesce']
    if type(coalesce) is not int or coalesce < 1 or col % coalesce:
        raise ValueError('Coalesce must divide the column count')
    if not 4 <= spec['spad_bank_lg_size'] <= 24:
        raise ValueError('Data bank capacity must be between 16 bytes and 16 MiB')
    spec['spad_num_banks'] = 2 * col
    spec['fgra_iob_sram_addr_width'] = spec['spad_bank_lg_size'] + (coalesce - 1).bit_length()
    known = set(operations()) | {'FCMP', 'FADDSUB', 'FEAS'}
    for row in spec['fgra_gpes']:
        for pe in row:
            if any(op not in known for op in pe['operations']):
                raise ValueError('Unknown hardware operation')
            if 'MAC' in pe['operations'] and 'ACC' not in pe['operations']:
                raise ValueError('MAC requires ACC')
    return spec

def operations():
    text = (ROOT / 'hardware/src/main/scala/op/Operations.scala').read_text()
    text = re.sub(r'//[^\n]*', '', text)
    # Read operation information maps, excluding memory operations and opcode tables.
    text = text.split('val OpInfoMap:', 1)[0]
    text = re.sub(r'val LSOpInfoMap:.*?\n\s*\)', '', text, flags=re.S)
    text = re.sub(r'val CMACInfoMap:.*?\n\s*\)', '', text, flags=re.S)
    ops = re.findall(r'"([A-Z][A-Z0-9_]*)"\s*->', text)
    return sorted(set(ops) - {'LUT'} | {'FCMP', 'FADDSUB', 'FEAS'})

def bench(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', name or ''):
        raise ValueError('Use a name starting with a letter, with letters, digits, _ or -')
    path = (ROOT / 'benchmarks' / name).resolve()
    if path.parent != (ROOT / 'benchmarks').resolve():
        raise ValueError('Invalid benchmark path')
    return path

def benchmarks():
    return sorted(p.name for p in (ROOT / 'benchmarks').iterdir()
                  if p.is_dir() and (p / (p.name + '.c')).is_file())

def compile_current(name, result):
    path = bench(name) / (name + '.c')
    latest = latest_job('compile', name)
    return bool(result and path.exists() and Path(result['dfg']).is_file()
                and (not latest or latest['id'] == result['job'] and latest['status'] == 'succeeded')
                and result['source_hash'] == digest(path.read_text())
                and (result['compiler'] != 'mlir' or result.get('rtl_hash') == (STATE['rtl'] or {}).get('hash'))
                and (not result.get('input_hash') or result['input_hash'] == compile_inputs(name, result))
                and (not result.get('input_hash') or (Path(result['dfg']).parent.parent / 'dfg.svg').is_file())
                and (not result.get('dfg_hash') or result['dfg_hash'] == file_hash(result['dfg'])))

def latest_job(kind, name=None):
    return next((j for j in reversed(list(JOBS.values())) if j['kind'] == kind and
                 (name is None or j.get('name') == name)), None)

def snapshot():
    with LOCK:
        # Detect external edits to the GUI's generated specification as well.
        cached_spec = spec_path()
        if not ACTIVE and cached_spec.is_file():
            try:
                external = checked_spec(json.loads(cached_spec.read_text()))
                if digest(external) != digest(STATE['spec']):
                    if digest(STATE['draft']) == digest(STATE['spec']):
                        STATE['draft'] = copy.deepcopy(external)
                    STATE['spec'] = external
                    STATE['step'] = 0
                    save()
            except (ValueError, KeyError, TypeError):
                pass
        data = copy.deepcopy(STATE)
        data['ui'] = copy.deepcopy(STATE.get('ui', {}))
        data['spec_templates'] = spec_templates()
        data['benchmarks'] = benchmarks()
        data['operations'] = operations()
        data['profiles'] = builder.PE_PROFILES
        data['jobs'] = copy.deepcopy(JOBS)
        data['active'] = ACTIVE
        data['dirty'] = digest(data['draft']) != digest(data['spec'])
        latest = latest_job('rtl')
        data['rtl_current'] = bool(data['rtl'] and data['rtl']['hash'] == digest(data['spec'])
                                   and all(p.is_file() for p in rtl_outputs(data['rtl']['dir']))
                                   and (not data['rtl'].get('input_hash') or data['rtl']['input_hash'] == rtl_inputs())
                                   and (not data['rtl'].get('output_hash') or data['rtl']['output_hash'] == files_hash(rtl_outputs(data['rtl']['dir'])))
                                   and (not latest or latest['id'] == data['rtl']['job'] and latest['status'] == 'succeeded'))
        for name, result in data['compile'].items():
            result['current'] = compile_current(name, result)
        for name, result in data['mapping'].items():
            compiled = data['compile'].get(name)
            latest = latest_job('mapping', name)
            result['current'] = bool(data['rtl_current'] and compiled and compiled['current']
                                     and (not latest or latest['id'] == result['job'] and latest['status'] == 'succeeded')
                                     and result['compile_id'] == compiled['job'] and result['rtl_hash'] == data['rtl']['hash']
                                     and (not result.get('input_hash') or result['input_hash'] == mapping_inputs(name, result)))
            directory = Path(result.get('dir', str(TMP / 'runs' / result['job'])))
            result['current'] = result['current'] and all((directory / p).is_file() for p in ('mapped_adg.json', 'mapped_adg.dot', 'config.bit'))
            if result.get('output_hash'):
                result['current'] = result['current'] and result['output_hash'] == files_hash([directory / p for p in result['output_files']])
            result['files'] = sorted(p.name for p in directory.iterdir()
                                     if p.is_file() and p.suffix in ('.bit', '.py', '.c', '.dot')
                                     and p.name != 'mapped_adg_view.dot') if directory.is_dir() else []
        verification = copy.deepcopy(verification_state())
        model = verification.get('build')
        latest = latest_job('verilator')
        verification['built'] = bool(data['rtl_current'] and not data['dirty'] and model
            and model.get('input_hash') == build_inputs() and Path(model['executable']).is_file()
            and model.get('executable_hash') == file_hash(model['executable'])
            and (not model.get('files') or (all((Path(model['executable']).parent.parent / p).is_file() for p in model['files'])
                and model['output_hash'] == files_hash([Path(model['executable']).parent.parent / p for p in model['files']])))
            and (not latest or latest['id'] == model['job'] and latest['status'] == 'succeeded'))
        verification['benchmarks'] = [name for name, result in data['mapping'].items() if result['current']
            and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name)
            and (Path(result.get('dir', str(TMP / 'runs' / result['job']))) / (name + '_cocotb.py')).is_file()]
        for name, result in verification.get('runs', {}).items():
            mapped = data['mapping'].get(name)
            latest_run = latest_job('verification', name)
            result['current'] = bool(verification['built'] and mapped and mapped['current']
                and (not latest_run or latest_run['id'] == result['job'] and latest_run['status'] == 'succeeded')
                and result.get('map_job') == mapped['job'] and result.get('build_hash') == model['input_hash']
                and result.get('test_hash') == file_hash(test_path(name))
                and result.get('runtime_hash') == files_hash((ROOT / 'simulation/server').glob('*.py')))
            result['current'] = result['current'] and (TMP / 'verification/results' / name / 'results.xml').is_file()
        data['verification'] = verification
        # Progress follows valid artifacts, including reused compiler output
        # after an architecture change, rather than the last action taken.
        data['step'] = 0
        if data['rtl_current'] and not data['dirty']:
            data['step'] = 1
            if any(result['current'] for result in data['compile'].values()):
                data['step'] = 2
            if any(result['current'] for result in data['mapping'].values()):
                data['step'] = 3
        return data

def run(job, args, cwd, env=None):
    global PROC
    job['log'] += '$ ' + ' '.join(map(str, args)) + '\n'
    with (Path(job['dir']) / 'run.log').open('a') as log:
        log.write('$ ' + ' '.join(map(str, args)) + '\n')
    with LOCK:
        if job.get('cancelled'):
            raise RuntimeError('Cancelled')
        PROC = subprocess.Popen(list(map(str, args)), cwd=cwd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors='replace', start_new_session=True)
        process = PROC
    timer = threading.Timer(3600, lambda: os.killpg(process.pid, signal.SIGTERM) if process.poll() is None else None)
    timer.start()
    try:
        with (Path(job['dir']) / 'run.log').open('a') as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                with LOCK:
                    job['log'] = (job['log'] + line)[-250000:]
        code = process.wait()
    finally:
        timer.cancel()
        with LOCK:
            PROC = None
    if job.get('cancelled'):
        raise RuntimeError('Cancelled')
    if code:
        raise RuntimeError('Command failed (exit ' + str(code) + ')')

def env_tools():
    env = os.environ.copy()
    dirs = [ROOT / p for p in ('llvm-project/install/bin', 'adora/build/bin', 'Polygeist/build/bin', 'oss-cad-suite/bin')]
    env['PATH'] = os.pathsep.join(map(str, dirs)) + os.pathsep + env.get('PATH', '')
    return env

def simulation_env():
    env = env_tools()
    conda = shutil.which('conda')
    if conda:
        bindir = Path(conda).resolve().parent
        lingo = bindir.parent / 'envs/lingo/bin'
        # Keep the template's Cocotb 1.9 runtime ahead of oss-cad-suite's bundled runtime.
        env['PATH'] = os.pathsep.join([str(lingo), env['PATH']])
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['CXXFLAGS'] = env.get('CXXFLAGS', '') + ' -std=c++17'
    return env

def simulation_cxx():
    path = env_tools()['PATH']
    return shutil.which('clang++', path=path) or shutil.which('g++', path=path) or 'g++'

def graph_json(dot, out, job, env):
    run(job, ['dot', '-Tdot_json', dot, '-o', out], out.parent, env)
    value = json.loads(out.read_text())
    return {'nodes': len([n for n in value.get('objects', []) if 'name' in n and 'nodes' not in n]),
            'edges': len(value.get('edges', []))}

def worker(job, payload):
    global ACTIVE
    directory = Path(job['dir'])
    env = env_tools()
    try:
        kind = job['kind']
        if kind == 'rtl':
            spec = copy.deepcopy(STATE['spec'])
            specfile = spec_path()
            specfile.write_bytes(builder.render_spec(spec))
            env.update(LINGO_SPEC=str(specfile), LINGO_OUTPUT_DIR=str(directory))
            run(job, ['conda', 'run', '--no-capture-output', '-n', 'lingo', 'sbt', 'runMain fgramemfp.VerilogGen'], ROOT / 'hardware', env)
            output = directory
            verilog = output / 'LinGoWithAXI.v'
            for path in (verilog, output / 'lingo-spec/lingo_adg.json', output / 'lingo-spec/operations.json'):
                if not path.is_file():
                    raise RuntimeError('Missing generated artifact: ' + path.name)
            (output / 'clean.v').write_text(re.sub(r'//\s*@[^\n]*', '', verilog.read_text()))
            if not all(p.is_file() for p in rtl_outputs(output)):
                raise RuntimeError('RTL generation is missing hardware description files')
            result = {'hash': digest(spec), 'dir': str(output), 'job': job['id'],
                      'input_hash': job.get('input_hash', rtl_inputs()), 'output_hash': files_hash(rtl_outputs(output))}
            with LOCK:
                STATE['rtl'] = result
                STATE['step'] = 1
        elif kind == 'compile':
            name = payload['name']
            source = bench(name) / (name + '.c')
            original = source.read_text()
            work = directory / 'work'
            shutil.copytree(source.parent, work, ignore=shutil.ignore_patterns('adora-cc-ir', '__pycache__', '*.json', '*.dot', '*.png', '*.ll'))
            compiler = payload.get('compiler', 'llvm')
            kernel = payload.get('kernel', 'kernel')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', kernel):
                raise ValueError('Invalid kernel function name')
            if compiler == 'llvm':
                run(job, ['bash', ROOT / 'benchmarks/compile.sh', name, kernel], work, env)
                dots = list(work.glob('affine.dot'))
                if not dots:
                    dots = [p for p in work.glob('*.dot') if p.stem == kernel]
                if not dots:
                    raise RuntimeError('Compiler did not produce affine.dot or the selected kernel DFG')
                dfg = work / (name + '.json')
                metrics = graph_json(dots[0], dfg, job, env)
            elif compiler == 'mlir':
                mlir = work / (name + '.mlir')
                run(job, ['cgeist', '-O2', '-lm', '-lgcc', '--import-all-index', work / (name + '.c'), '-S', '-o', mlir], work, env)
                run(job, [sys.executable, ROOT / 'adora/tools/adoracc/adoracc.py', mlir, '--work-dir', work], ROOT / 'benchmarks', env)
                dot = work / 'adora-cc-ir/2_dfgs' / (name + '_CDFG.dot')
                dfg = work / (name + '.json')
                run(job, [sys.executable, ROOT / 'adora/scripts/cdfg_to_lingo.py', dot, '-o', dfg,
                          '--operations', Path(STATE['rtl']['dir']) / 'lingo-spec/operations.json'], work, env)
                metrics = graph_json(dot, work / 'preview.json', job, env)
            else:
                raise ValueError('Unknown compiler')
            preview = dots[0] if compiler == 'llvm' else dot
            run(job, ['dot', '-Tsvg', preview, '-o', directory / 'dfg.svg'], work, env)
            # Publish the selected program's compiler output only; keep intermediates isolated.
            shutil.copy2(dfg, source.parent / (name + '.json'))
            result = dict(metrics, job=job['id'], dfg=str(dfg), source_hash=digest(original), compiler=compiler,
                          kernel=kernel, input_hash=job.get('input_hash', compile_inputs(name, payload)),
                          dfg_hash=file_hash(dfg), rtl_hash=STATE['rtl']['hash'],
                          svg='/api/artifact?job=' + job['id'] + '&file=dfg.svg')
            with LOCK:
                STATE['compile'][name] = result
                STATE['mapping'].pop(name, None)
                STATE['step'] = 2
        elif kind == 'mapping':
            name = payload['name']
            compiled = copy.deepcopy(STATE['compile'][name])
            rtl = copy.deepcopy(STATE['rtl'])
            output_type = payload.get('backend', 'all')
            if output_type not in ('all', 'cocotb', 'sdk'):
                raise ValueError('Unknown output backend')
            dfg = directory / (name + '.json')
            shutil.copy2(compiled['dfg'], dfg)
            (directory / 'result').mkdir(exist_ok=True)
            for folder in ('CustomOP', 'Syn'):
                (directory / folder).symlink_to(ROOT / 'mapper' / folder, target_is_directory=True)
            specdir = Path(rtl['dir']) / 'lingo-spec'
            run(job, [ROOT / 'mapper/build/mapperPro', 'SPDLOG_LEVEL=off', '-c', 'true', '-m', 'true', '-o', 'true',
                      '-t', '6000000', '-i', '15', '-q', 'true', '-v', 'false', '-C', 'false', '-e', output_type,
                      '-p', specdir / 'operations.json', '-a', specdir / 'lingo_adg.json', '-d', dfg], directory, env)
            metricdir = directory / 'result'
            failure = float((metricdir / 'mappingFailureRate.txt').read_text())
            if failure != 0 or not (directory / 'mapped_adg.dot').is_file():
                raise RuntimeError('Mapper did not find a valid mapping')
            ii = float((metricdir / 'ii.txt').read_text())
            latency = float((metricdir / 'latency.txt').read_text())
            # The mapper requests sfdp/overlap removal, which some Graphviz builds lack.
            # Preserve the original DOT and use dot layout for the interactive preview.
            view_dot = directory / 'mapped_adg_view.dot'
            view_dot.write_text(re.sub(r'\b(?:layout|overlap)\s*=\s*[^;]+;', '',
                                       (directory / 'mapped_adg.dot').read_text()))
            run(job, ['dot', '-Kdot', '-Tdot_json', view_dot, '-o', directory / 'mapped_adg.json'], directory, env)
            run(job, ['dot', '-Kdot', '-Tsvg', directory / 'mapped_dfg.dot', '-o', directory / 'dfg.svg'], directory, env)
            required = ['mapped_adg.json', 'config.bit']
            if output_type in ('all', 'cocotb'):
                required.append(name + '_cocotb.py')
            if not all((directory / filename).is_file() for filename in required):
                raise RuntimeError('Mapping is missing required output files')
            output_files = sorted(p.name for p in directory.iterdir() if p.is_file() and
                                  (p.suffix in ('.bit', '.py') or p.name == 'mapped_adg.json'))
            result = {'job': job['id'], 'dir': str(directory), 'ii': ii, 'latency': latency, 'backend': output_type,
                      'input_hash': job.get('input_hash') or mapping_inputs(name, payload),
                      'output_files': output_files, 'output_hash': files_hash([directory / p for p in output_files]),
                      'compile_id': compiled['job'], 'rtl_hash': rtl['hash'],
                      'svg': '/api/artifact?job=' + job['id'] + '&file=dfg.svg'}
            with LOCK:
                STATE['mapping'][name] = result
                STATE['step'] = 3
        elif kind == 'verilator':
            env = simulation_env()
            circuits = directory / 'circuits'
            circuits.mkdir()
            (directory / 'workspace').mkdir()
            shutil.copy2(ROOT / 'simulation/Makefile', directory / 'Makefile')
            shutil.copy2(ROOT / 'simulation/circuits/test_cgra.v', circuits / 'test_cgra.v')
            rtl = Path(STATE['rtl']['dir'])
            shutil.copy2(rtl / 'clean.v', circuits / 'LinGoWithAXI.v')
            for original, target in [('axilite_spec.json', 'axilite_spec.json'), ('lingo_adg.json', 'lingo_cgra_adg.json')]:
                shutil.copy2(rtl / 'lingo-spec' / original, circuits / target)
            env.update(PWD=str(directory), PYTHONDONTWRITEBYTECODE='1')
            run(job, ['conda', 'run', '--no-capture-output', '-n', 'lingo', 'make', '-j16', 'SIM=verilator',
                'CXX=' + simulation_cxx(), 'BUILD_ARGS=OPT_FAST=-O0 OPT_SLOW=-O0', 'sim_build/Vtop'], directory, env)
            executable = directory / 'sim_build/Vtop'
            if not executable.is_file():
                raise RuntimeError('Verilator did not produce sim_build/Vtop')
            model_files = MODEL_FILES
            with LOCK:
                verification_state()['build'] = {'job': job['id'], 'input_hash': job['input_hash'],
                    'executable': str(executable), 'executable_hash': file_hash(executable),
                    'files': model_files, 'output_hash': files_hash([directory / p for p in model_files])}
        elif kind == 'verification':
            env = simulation_env()
            name = payload['name']
            build = TMP / 'verification/build'
            workspace = build / 'workspace'
            shutil.copy2(test_path(name), directory / 'test_cgra.py')
            shutil.copy2(directory / 'test_cgra.py', workspace / 'test_cgra.py')
            mapped = STATE['mapping'][name]
            mapdir = Path(mapped['dir'])
            shutil.copy2(mapdir / (name + '_cocotb.py'), directory / (name + '_cocotb.py'))
            shutil.copy2(directory / (name + '_cocotb.py'), workspace / (name + '.py'))
            runtime_hash = files_hash((ROOT / 'simulation/server').glob('*.py'))
            env.update(PWD=str(build), PYTHONDONTWRITEBYTECODE='1',
                PYTHONPATH=os.pathsep.join([str(workspace), str(ROOT / 'simulation/server'), env.get('PYTHONPATH', '')]))
            # Only execute the already built model; no implicit rebuild during Run.
            results = directory / 'results.xml'
            run(job, ['conda', 'run', '--no-capture-output', '-n', 'lingo', 'make', 'SIM=verilator',
                'MODULE=test_cgra', 'COCOTB_RESULTS_FILE=' + str(results), str(results)], build, env)
            if not results.is_file():
                raise RuntimeError('Simulation did not produce results.xml')
            report = ET.parse(results).getroot()
            tests = list(report.iter('testcase'))
            failures = list(report.iter('failure')) + list(report.iter('error'))
            if not tests or failures:
                raise RuntimeError('Simulation failed: ' + str(len(failures)) + ' failure(s), ' + str(len(tests)) + ' test(s)')
            with LOCK:
                verification_state()['runs'][name] = {'job': job['id'], 'map_job': mapped['job'],
                    'build_hash': verification_state()['build']['input_hash'], 'test_hash': file_hash(directory / 'test_cgra.py'),
                    'runtime_hash': runtime_hash, 'tests': len(tests)}
        else:
            raise ValueError('Unknown job type')
        with LOCK:
            job['status'] = 'succeeded'
            save()
    except Exception as error:
        with LOCK:
            job['status'] = 'cancelled' if job.get('cancelled') else 'failed'
            job['error'] = str(error)
            job['log'] += '\n' + str(error) + '\n'
            with (directory / 'run.log').open('a') as log:
                log.write('\n' + str(error) + '\n')
    finally:
        with LOCK:
            job['elapsed'] = round(time.monotonic() - job.pop('_started'), 2)
            atomic_json(directory / 'job.json', job)
            ACTIVE = None

# Restore job summaries after a restart; interrupted jobs cannot be considered successful.
for p in sorted(TMP.rglob('job.json'), key=lambda p: p.stat().st_mtime):
    try:
        job = json.loads(p.read_text())
        if job['status'] == 'running':
            job['status'] = 'failed'
            job['error'] = 'Server stopped before the task finished'
        job.pop('_started', None)
        JOBS[job['id']] = job
    except (ValueError, KeyError):
        pass

def migrate_outputs():
    """Move existing successful outputs without discarding previous user results."""
    old = TMP / 'runs'
    if not old.exists() and not any((TMP / name).exists() for name in ('fgra_spec.json', 'previews')):
        return
    hardware = TMP / 'hardware'
    hardware.mkdir(exist_ok=True)
    rtl = STATE.get('rtl')
    moves = []
    if rtl and Path(rtl['dir']).is_dir() and old in Path(rtl['dir']).parents:
        moves.append((Path(rtl['dir']), hardware / 'rtl', rtl['job']))
    for name, result in STATE['compile'].items():
        source = old / result['job']
        if source.is_dir():
            moves.append((source, TMP / 'benchmarks' / name / 'compile', result['job']))
    for name, result in STATE['mapping'].items():
        source = old / result['job']
        if source.is_dir():
            moves.append((source, TMP / 'benchmarks' / name / 'map', result['job']))
    for source, target, ident in moves:
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        if ident in JOBS:
            job = JOBS[ident]
            if job['kind'] == 'rtl':
                for filename in ('run.log', 'job.json'):
                    previous = Path(job['dir']) / filename
                    if previous.is_file():
                        shutil.move(str(previous), str(target / filename))
            job['dir'] = str(target)
            atomic_json(target / 'job.json', job)
        if rtl and ident == rtl['job']:
            rtl['dir'] = str(target)
        for result in STATE['compile'].values():
            if result['job'] == ident:
                result['dfg'] = str(target / Path(result['dfg']).relative_to(source))
        for result in STATE['mapping'].values():
            if result['job'] == ident:
                result['dir'] = str(target)
    for filename in ('fgra_spec.json', 'previews'):
        source = TMP / filename
        if source.exists() and not (hardware / filename).exists():
            shutil.move(str(source), str(hardware / filename))
    archive = hardware / 'legacy-runs'
    if archive.exists():
        archive = hardware / ('legacy-runs-' + uuid.uuid4().hex[:6])
    if old.exists() and any(old.iterdir()):
        shutil.move(str(old), str(archive))
        for job in JOBS.values():
            directory = Path(job['dir'])
            if old in directory.parents:
                job['dir'] = str(archive / directory.relative_to(old))
                if Path(job['dir']).is_dir():
                    atomic_json(Path(job['dir']) / 'job.json', job)
    elif old.exists():
        old.rmdir()
    verification_state()
    save()

migrate_outputs()
JOBS = dict(sorted(JOBS.items(), key=lambda item: item[1].get('created', 0)))

def initialize_output_hashes():
    changed = False
    rtl = STATE.get('rtl')
    if rtl and not rtl.get('output_hash') and all(p.is_file() for p in rtl_outputs(rtl['dir'])):
        rtl['output_hash'] = files_hash(rtl_outputs(rtl['dir']))
        changed = True
    for result in STATE['compile'].values():
        if not result.get('dfg_hash') and Path(result['dfg']).is_file():
            result['dfg_hash'] = file_hash(result['dfg'])
            changed = True
    for result in STATE['mapping'].values():
        directory = Path(result.get('dir', str(TMP / 'runs' / result['job'])))
        if directory.is_dir() and not result.get('output_hash'):
            result['output_files'] = sorted(p.name for p in directory.iterdir() if p.is_file()
                and (p.suffix in ('.bit', '.py') or p.name == 'mapped_adg.json'))
            result['output_hash'] = files_hash([directory / p for p in result['output_files']])
            changed = True
    model = verification_state().get('build')
    if model and not model.get('files'):
        directory = Path(model['executable']).parent.parent
        if all((directory / p).is_file() for p in MODEL_FILES):
            model['files'] = MODEL_FILES
            model['output_hash'] = files_hash([directory / p for p in MODEL_FILES])
            changed = True
    if changed:
        save()

initialize_output_hashes()

def start(kind, payload):
    global ACTIVE
    with LOCK:
        if kind not in ('rtl', 'compile', 'mapping', 'verilator', 'verification'):
            raise ValueError('Unknown job type')
        if ACTIVE:
            raise ValueError('Another task is running')
        state = snapshot()
        if kind in ('compile', 'mapping', 'verilator', 'verification') and (not state['rtl_current'] or state['dirty']):
            raise ValueError('Generate RTL for the current architecture first')
        if kind == 'mapping' and not state['compile'].get(payload.get('name'), {}).get('current'):
            raise ValueError('Compile the current source first')
        if kind == 'rtl' and state['dirty']:
            raise ValueError('Generate spec before generating RTL')
        name = payload.get('name')
        if kind in ('compile', 'mapping', 'verification'):
            bench(name)
        if kind == 'compile' and (payload.get('compiler', 'llvm') not in ('llvm', 'mlir')
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', payload.get('kernel', 'kernel'))):
            raise ValueError('Invalid compiler or kernel function')
        if kind == 'mapping' and payload.get('backend', 'all') not in ('all', 'cocotb', 'sdk'):
            raise ValueError('Unknown output backend')
        if kind == 'verification':
            if not state['verification']['built']:
                raise ValueError('Build Verilator for the current RTL first')
            if name not in state['verification']['benchmarks']:
                raise ValueError('Select a current mapping with a generated Cocotb Python file')
            if not test_path(name).is_file():
                raise ValueError('Save the test script before running')
            if 'test_source' in payload and payload['test_source'] != test_path(name).read_text():
                raise ValueError('The saved test script changed; reload it before running')
            ast.parse(test_path(name).read_text())
        inputs = {'rtl': rtl_inputs, 'compile': lambda: compile_inputs(name, payload),
                  'mapping': lambda: mapping_inputs(name, payload), 'verilator': build_inputs}
        input_hash = inputs[kind]() if kind in inputs else None
        cached = state['rtl'] if kind == 'rtl' else state['compile'].get(name) if kind == 'compile' else state['mapping'].get(name) if kind == 'mapping' else state['verification']['build'] if kind == 'verilator' else None
        current = state['rtl_current'] if kind == 'rtl' else state['verification']['built'] if kind == 'verilator' else cached and cached.get('current')
        if current and cached.get('input_hash') == input_hash:
            return {'id': cached['job'], 'cached': True, 'message': 'Already built' if kind == 'verilator' else 'Inputs unchanged; existing output reused'}
        ident = uuid.uuid4().hex[:12]
        directory = (TMP / 'hardware/rtl' if kind == 'rtl' else TMP / 'verification/build' if kind == 'verilator'
            else TMP / 'verification/results' / name if kind == 'verification'
            else TMP / 'benchmarks' / name / ('compile' if kind == 'compile' else 'map'))
        if directory.exists():
            shutil.rmtree(directory)
        for key, old_job in list(JOBS.items()):
            if Path(old_job['dir']) == directory:
                del JOBS[key]
        directory.mkdir(parents=True)
        job = {'id': ident, 'kind': kind, 'name': payload.get('name'), 'status': 'running', 'dir': str(directory),
               'log': '', 'input_hash': input_hash, '_started': time.monotonic(), 'created': time.time(), 'elapsed': 0}
        JOBS[ident] = job
        ACTIVE = ident
        if kind in ('rtl', 'compile', 'mapping'):
            STATE['step'] = {'rtl': 0, 'compile': 1, 'mapping': 2}[kind]
        save()
        atomic_json(directory / 'job.json', job)
        threading.Thread(target=worker, args=(job, copy.deepcopy(payload)), daemon=True).start()
        return {'id': ident}

class Handler(BaseHTTPRequestHandler):
    def respond(self, data, code=200, mime='application/json'):
        raw = json.dumps(data).encode() if mime == 'application/json' else data
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == '/api/state':
                state = snapshot()
                for job in state['jobs'].values():
                    if '_started' in job:
                        job['elapsed'] = round(time.monotonic() - job.pop('_started'), 1)
                return self.respond(state)
            if parsed.path == '/api/source':
                name = query['name'][0]
                return self.respond({'source': (bench(name) / (name + '.c')).read_text()})
            if parsed.path == '/api/verification-source':
                name = query['name'][0]
                path = test_path(name)
                return self.respond({'source': verification_source(name), 'saved': path.is_file(), 'path': str(path)})
            if parsed.path == '/api/mapping':
                job = JOBS[query['job'][0]]
                return self.respond(json.loads((Path(job['dir']) / 'mapped_adg.json').read_text()))
            if parsed.path == '/api/adg':
                return self.respond(json.loads((Path(STATE['rtl']['dir']) / 'lingo-spec/lingo_adg.json').read_text()))
            if parsed.path == '/api/artifact':
                directory = Path(JOBS[query['job'][0]]['dir'])
                path = (directory / query['file'][0]).resolve()
                if directory.resolve() not in path.parents or not path.is_file():
                    raise ValueError('Invalid artifact')
            else:
                path = (GUI / 'static' / ('index.html' if parsed.path == '/' else parsed.path.lstrip('/'))).resolve()
                if (GUI / 'static').resolve() not in path.parents:
                    raise ValueError('Invalid path')
            self.respond(path.read_bytes(), mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        except Exception as error:
            self.respond({'error': str(error)}, 404)

    def do_POST(self):
        try:
            # Local browser clients only. Reject cross-origin writes and DNS rebinding.
            host = self.headers.get('Host', '')
            if host.split(':')[0] not in ('127.0.0.1', 'localhost'):
                raise ValueError('Only localhost requests are allowed')
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + host:
                raise ValueError('Cross-origin requests are not allowed')
            length = int(self.headers.get('Content-Length', 0))
            if length > 2_000_000:
                raise ValueError('Request too large')
            payload = json.loads(self.rfile.read(length) or '{}')
            route = urlparse(self.path).path
            if route == '/api/run':
                return self.respond(start(payload['kind'], payload))
            with LOCK:
                if route == '/api/cancel':
                    if ACTIVE:
                        JOBS[ACTIVE]['cancelled'] = True
                        if PROC and PROC.poll() is None:
                            os.killpg(PROC.pid, signal.SIGTERM)
                    return self.respond({'ok': True})
                if route == '/api/ui':
                    allowed = {'program', 'mapping_program', 'compiler', 'kernel', 'backend', 'verification_program'}
                    STATE['ui'] = {key: value for key, value in payload.items()
                                   if key in allowed and isinstance(value, str) and len(value) <= 128}
                    save()
                    return self.respond({'ok': True})
                if ACTIVE:
                    raise ValueError('Wait for the running task before editing inputs')
                if route == '/api/draft':
                    STATE['draft'] = payload['spec']
                elif route == '/api/spec':
                    apply_spec(payload['spec'])
                elif route == '/api/load-spec':
                    apply_spec(load_spec_template(payload.get('name')))
                    STATE['loaded_template'] = payload['name']
                elif route == '/api/save-spec':
                    return self.respond(save_spec_template(payload.get('name'), payload['spec'], payload.get('overwrite') is True))
                elif route == '/api/verification-source':
                    save_verification_source(payload['name'], payload['source'])
                elif route == '/api/source':
                    name = payload['name']
                    (bench(name) / (name + '.c')).write_text(payload['source'])
                    STATE['step'] = min(STATE['step'], 1)
                elif route == '/api/new':
                    name = payload['name']
                    directory = bench(name)
                    directory.mkdir(exist_ok=False)
                    (directory / (name + '.c')).write_text('')
                else:
                    raise ValueError('Unknown endpoint')
                save()
            self.respond({'ok': True})
        except Exception as error:
            self.respond({'error': str(error)}, 400)

    def log_message(self, fmt, *args):
        if args and '/api/state' in str(args[0]):
            return
        super().log_message(fmt, *args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'LinGo Workbench: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if PROC and PROC.poll() is None:
            os.killpg(PROC.pid, signal.SIGTERM)
        server.server_close()
