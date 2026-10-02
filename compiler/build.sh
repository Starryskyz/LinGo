# set env for built LLVM
OLD_PATH="$PATH"
export LLVM_HOME="$(pwd)/llvm-project/install/bin"
export PATH=$LLVM_HOME:$PATH

# cmake & make
cmake -B build -G Ninja
cmake --build build


export PATH="$OLD_PATH"
unset OLD_PATH