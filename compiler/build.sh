# set env for built LLVM
export LLVM_HOME=/data/jrzhang/auforapro/llvm-project/build/bin
export PATH=$LLVM_HOME:$PATH

# cmake & make
cmake -B build -G Ninja
cmake --build build
