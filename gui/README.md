# LinGo Design Workbench

Run from any directory with Python 3.10 or newer:

```bash
python3 /data/jrzhang/LinGo/gui/server.py --port 8080
```

Open **http://127.0.0.1:8080**. The application uses Python's standard library and a local HTML/CSS/JavaScript frontend; no npm install or CDN access is required. For a remote machine, forward port 8080 through SSH.

The workflow is **CGRA HW → Compile → Mapping → Verification**. Physical Design is reserved for later implementation. Generate spec, then RTL, before compiling. Select individual PEs, GIBs and IOBs to configure them. **Load spec** loads a JSON architecture from `hardware/spectemplate`. After **Generate spec**, optionally use **Save spec** directly below it to save the generated spec there under the entered name, appending `.json` when needed; an existing filename requires overwrite confirmation. Changed architecture inputs make RTL and mapping results outdated. The format brush copies a PE, IOB or GIB configuration to the same kind of resource; press Escape to stop painting. **Apply to all** copies to every resource of that kind. GIB copies CG settings and any source FG settings to existing FG GIBs, without creating new FG connections. Scroll to zoom and drag to pan each graph.

Architecture drafts, generated specifications, RTL/ADG, intermediate compilation files, mapping outputs and task logs are stored in `gui/tmp`. The repository hardware spec is imported on first launch and is not overwritten. Successful compilation publishes only the selected program's `<name>.json` into its benchmark directory. Creating and saving a program writes its C file there. RTL generation uses `LINGO_SPEC` / `LINGO_OUTPUT_DIR` and performs the same clean-Verilog operation as `hardware/genRTL.sh`, with isolated output paths.

Outputs have stable locations:

```text
gui/tmp/
  state.json
  hardware/fgra_spec.json
  hardware/rtl/                 # Verilog, hardware descriptions, run.log
  verification/build/          # Makefile, circuits, workspace, sim_build/Vtop
  verification/tests/<name>/test_cgra.py
  verification/results/<name>/ # logs, XML, executed test/kernel snapshots, job.json
  benchmarks/<name>/compile/   # compiler intermediates, DFG preview, run.log
  benchmarks/<name>/map/       # mapped graphs, config.bit, Cocotb/SDK outputs
```

Actions reuse successful outputs when their input fingerprints match and required files are intact. Changed inputs or missing/modified outputs replace the corresponding output directory on the next action. RTL checks the spec and generator sources; compilation checks C/header files, compiler, kernel and tools (plus RTL for MLIR); mapping checks DFG, RTL, backend and mapper. Model builds check actual RTL/descriptions, simulation Makefile/testbench and tools. Each simulation Run executes again and replaces that benchmark's simulation results. Existing UUID outputs migrate to these locations; older runs remain in `hardware/legacy-runs`. Saved test edits survive model rebuilds.

In **Verification**, click **Build Verilator** first. An unchanged, intact model reports **Already built**. Benchmark selection then includes only current mappings with `<name>_cocotb.py`. The editor uses `simulation/workspace/test_cgra_template.py`, replacing `example` with the benchmark name, and keeps edits in `verification/tests/<name>/test_cgra.py`. Save before Run; the generated mapping module is imported as `<name>.py`. Input generation and golden-result checks remain editable for each kernel. The right pane shows build/run output, with an inline Stop button; this page has no bottom log panel. Runs use the built model and fail on Cocotb errors or failed/empty XML reports. Simulation uses the `lingo` environment's Cocotb 1.9 runtime and the project simulation Makefile. GUI model builds prefer the existing LLVM/Clang C++ compiler, use C++17, `-O0` and four jobs to reduce initial build time; execution reuses the completed model. Benchmark names containing `-` are excluded from Python imports.

Every workflow step fits within the browser viewport. Wide, standard, compact and narrow layouts use fixed toolbar and log sizes, while the remaining space goes to the current step. Configuration panels, source code, task output and overflowing toolbars scroll internally. Narrow screens place the hardware canvas above its settings; short screens use a denser layout. Mapping places its controls and statistics on the left and a larger architecture canvas on the right. PE and IO utilization count distinct occupied resources in the mapped architecture, with used/total counts. Outside Verification, the log panel stays at the bottom and starts collapsed. **Expand** / **Collapse** shares its state across these steps, with a fixed height in each state.

The tool adapters follow `benchmarks/compile.sh`, `benchmarks/mlirCompile.sh` and `mapper/run.sh`. They convert the current LLVM DFG with Graphviz instead of running the directory-wide `dot2json.sh`; MLIR uses its dedicated `cdfg_to_lingo.py` converter. Mapping uses the selected compiled DFG and the current GUI-generated ADG, rather than `run.sh`'s hard-coded `affine.json` and hardware paths. The script files are not modified.

Required tools are the existing LinGo installation: the `lingo` Conda environment with sbt, built LLVM pass and LLVM 15 executables, Graphviz, built mapper and Yosys; MLIR additionally needs built Polygeist/Adora and its Python dependencies. Run the server from the Python environment used for Adora when using MLIR. Tasks have a one-hour timeout and can be stopped from the log panel. One task runs at a time.

Run the focused backend checks with:

```bash
python3 -m unittest discover -s gui -p 'test_*.py'
node gui/test_instance_copy.js
node gui/test_mapping_metrics.js
```
