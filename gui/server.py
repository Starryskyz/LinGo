#!/usr/bin/env python3
"""Local LinGo workbench. Python standard library only."""
import argparse
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

def spec_templates():
    return sorted(p.name for p in SPEC_TEMPLATES.glob('*.json')
                  if p.is_file() and p.resolve().parent == SPEC_TEMPLATES.resolve())

def load_spec_template(name):
    if not isinstance(name, str) or name not in spec_templates():
        raise ValueError('Select a JSON spec from hardware/spectemplate')
    return checked_spec(json.loads((SPEC_TEMPLATES / name).read_text()))

def apply_spec(spec):
    spec = checked_spec(copy.deepcopy(spec))
    (TMP / 'fgra_spec.json').write_bytes(builder.render_spec(spec))
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
                and (result['compiler'] != 'mlir' or result.get('rtl_hash') == (STATE['rtl'] or {}).get('hash')))

def latest_job(kind, name=None):
    return next((j for j in reversed(list(JOBS.values())) if j['kind'] == kind and
                 (name is None or j.get('name') == name)), None)

def snapshot():
    with LOCK:
        # Detect external edits to the GUI's generated specification as well.
        cached_spec = TMP / 'fgra_spec.json'
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
                                   and Path(data['rtl']['dir']).is_dir()
                                   and (not latest or latest['id'] == data['rtl']['job'] and latest['status'] == 'succeeded'))
        for name, result in data['compile'].items():
            result['current'] = compile_current(name, result)
        for name, result in data['mapping'].items():
            compiled = data['compile'].get(name)
            latest = latest_job('mapping', name)
            result['current'] = bool(data['rtl_current'] and compiled and compiled['current']
                                     and (not latest or latest['id'] == result['job'] and latest['status'] == 'succeeded')
                                     and result['compile_id'] == compiled['job'] and result['rtl_hash'] == data['rtl']['hash'])
            directory = TMP / 'runs' / result['job']
            result['files'] = sorted(p.name for p in directory.iterdir()
                                     if p.is_file() and p.suffix in ('.bit', '.py', '.c', '.dot')
                                     and p.name != 'mapped_adg_view.dot') if directory.is_dir() else []
        return data

def run(job, args, cwd, env=None):
    global PROC
    job['log'] += '$ ' + ' '.join(map(str, args)) + '\n'
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
            specfile = directory / 'fgra_spec.json'
            specfile.write_bytes(builder.render_spec(spec))
            env.update(LINGO_SPEC=str(specfile), LINGO_OUTPUT_DIR=str(directory / 'hardware'))
            run(job, ['conda', 'run', '--no-capture-output', '-n', 'lingo', 'sbt', 'runMain fgramemfp.VerilogGen'], ROOT / 'hardware', env)
            output = directory / 'hardware'
            verilog = output / 'LinGoWithAXI.v'
            for path in (verilog, output / 'lingo-spec/lingo_adg.json', output / 'lingo-spec/operations.json'):
                if not path.is_file():
                    raise RuntimeError('Missing generated artifact: ' + path.name)
            (output / 'clean.v').write_text(re.sub(r'//\s*@[^\n]*', '', verilog.read_text()))
            result = {'hash': digest(spec), 'dir': str(output), 'job': job['id']}
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
                          rtl_hash=STATE['rtl']['hash'], svg='/api/artifact?job=' + job['id'] + '&file=dfg.svg')
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
            result = {'job': job['id'], 'ii': ii, 'latency': latency, 'backend': output_type,
                      'compile_id': compiled['job'], 'rtl_hash': rtl['hash'],
                      'svg': '/api/artifact?job=' + job['id'] + '&file=dfg.svg'}
            with LOCK:
                STATE['mapping'][name] = result
                STATE['step'] = 3
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
    finally:
        with LOCK:
            job['elapsed'] = round(time.monotonic() - job.pop('_started'), 2)
            atomic_json(directory / 'job.json', job)
            ACTIVE = None

# Restore job summaries after a restart; interrupted jobs cannot be considered successful.
for p in sorted((TMP / 'runs').glob('*/job.json'), key=lambda p: p.stat().st_mtime) if (TMP / 'runs').exists() else []:
    try:
        job = json.loads(p.read_text())
        if job['status'] == 'running':
            job['status'] = 'failed'
            job['error'] = 'Server stopped before the task finished'
        job.pop('_started', None)
        JOBS[job['id']] = job
    except (ValueError, KeyError):
        pass

def start(kind, payload):
    global ACTIVE
    with LOCK:
        if kind not in ('rtl', 'compile', 'mapping'):
            raise ValueError('Unknown job type')
        if ACTIVE:
            raise ValueError('Another task is running')
        state = snapshot()
        if kind in ('compile', 'mapping') and (not state['rtl_current'] or state['dirty']):
            raise ValueError('Generate RTL for the current architecture first')
        if kind == 'mapping' and not state['compile'].get(payload.get('name'), {}).get('current'):
            raise ValueError('Compile the current source first')
        if kind == 'rtl' and state['dirty']:
            raise ValueError('Generate spec before generating RTL')
        ident = uuid.uuid4().hex[:12]
        directory = TMP / 'runs' / ident
        directory.mkdir(parents=True)
        job = {'id': ident, 'kind': kind, 'name': payload.get('name'), 'status': 'running', 'dir': str(directory),
               'log': '', '_started': time.monotonic(), 'created': time.time(), 'elapsed': 0}
        JOBS[ident] = job
        ACTIVE = ident
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
                    allowed = {'program', 'mapping_program', 'compiler', 'kernel', 'backend'}
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
