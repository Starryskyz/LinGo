# LinGo Design Workbench

Run from any directory with Python 3.10 or newer:

```bash
python3 /data/jrzhang/LinGo/gui/server.py --port 8080
```

Open **http://127.0.0.1:8080**. The application uses Python's standard library and a local HTML/CSS/JavaScript frontend; no npm install or CDN access is required. For a remote machine, forward port 8080 through SSH.

The workflow is **CGRA HW → Compile → Mapping**. Verification and Physical Design are reserved for later implementation. Generate spec, then RTL, before compiling. Select individual PEs, GIBs and IOBs to configure them. Use **Load spec** to select a JSON architecture from `hardware/spectemplate`; loading replaces the current draft and cached spec, while the template remains unchanged. Changed architecture inputs make RTL and mapping results outdated. The format brush copies a PE, IOB or GIB configuration to the same kind of resource; press Escape to stop painting. **Apply to all** copies to every resource of that kind. GIB copies CG settings and any source FG settings to existing FG GIBs, without creating new FG connections. Scroll to zoom and drag to pan each graph.

Architecture drafts, generated specifications, RTL/ADG, intermediate compilation files, mapping outputs and task logs are stored in `gui/tmp`. The repository hardware spec is imported on first launch and is not overwritten. Successful compilation publishes only the selected program's `<name>.json` into its benchmark directory. Creating and saving a program writes its C file there. RTL generation uses `LINGO_SPEC` / `LINGO_OUTPUT_DIR` and performs the same clean-Verilog operation as `hardware/genRTL.sh`, with isolated output paths.

The tool adapters follow `benchmarks/compile.sh`, `benchmarks/mlirCompile.sh` and `mapper/run.sh`. They convert the current LLVM DFG with Graphviz instead of running the directory-wide `dot2json.sh`; MLIR uses its dedicated `cdfg_to_lingo.py` converter. Mapping uses the selected compiled DFG and the current GUI-generated ADG, rather than `run.sh`'s hard-coded `affine.json` and hardware paths. The script files are not modified.

Required tools are the existing LinGo installation: the `lingo` Conda environment with sbt, built LLVM pass and LLVM 15 executables, Graphviz, built mapper and Yosys; MLIR additionally needs built Polygeist/Adora and its Python dependencies. Run the server from the Python environment used for Adora when using MLIR. Tasks have a one-hour timeout and can be stopped from the log panel. One task runs at a time.

Run the focused backend checks with:

```bash
python3 -m unittest discover -s gui -p 'test_*.py'
node gui/test_instance_copy.js
```
