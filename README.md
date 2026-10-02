# LinGo

## Preparation

1. Install LLVM 15.0.6

```
cd LinGo

curl -L -O https://github.com/llvm/llvm-project/releases/download/llvmorg-15.0.6/llvm-project-15.0.6.src.tar.xz

mkdir -p llvm-project
tar -xf llvm-project-15.0.6.src.tar.xz \
    -C llvm-project \
    --strip-components=1

cmake -G Ninja \
    -S llvm-project/llvm \
    -B llvm-project/build \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_DUMP=ON \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DCMAKE_INSTALL_PREFIX="$(pwd)/llvm-project/install" \
    -DLLVM_ENABLE_PROJECTS="clang"

ninja -C llvm-project/build -j 16
ninja -C llvm-project/build install
```

2. Conda env

```
conda create -n lingo python=3.12
conda activate lingo
conda install -c conda-forge openjdk=8 --no-update-deps
conda install -c conda-forge sbt --no-update-deps
pip install "cocotb~=1.9.2"
pip install cocotbext-axi
pip install numpy
```


3. Yosys download

```
curl -L -O https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-10-02/oss-cad-suite-linux-x64-20261002.tgz

mkdir -p oss-cad-suite

tar -xf oss-cad-suite-linux-x64-20261002.tgz \
    -C oss-cad-suite \
    --strip-components=1
```

4. Install Verilator 5.044, and add to bashrc

```
git clone https://github.com/verilator/verilator.git
cd verilator
git checkout v5.044
autoconf
./configure
make -j8
export PATH=xxx/verilator/bin:$PATH
```

## Build 

1. Build compiler

```
cd ./compiler
bash build.sh
```

2. Build mapper

```
cd ./mapper
bash build.sh
```

## Run

1. RTL hardware generate

```
cd ./hardware
bash genRTL.sh
bash export-cocotb.sh
```

2. Compile app

```
cd ./benchmarks
cd [example]
../compile.sh [example] [kernel]
cd .. && ./dot2json.sh
```

3. Mapping

```
cd ./mapper
../run.sh [example] cocotb
cp ../benchmarks/[example]/xxx_cocotb.py ../simulation/workspace/[example].py
```

4. Verfication

```
cd simulation
export PYTHONPATH=$(pwd)/server:$PYTHONPATH
export PYTHONPATH=$(pwd)/workspace:$PYTHONPATH
make [-j8]
```