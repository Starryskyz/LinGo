cmake_minimum_required(VERSION 3.1)
set(PROJECT_NAME llvm-cdfg)
project(${PROJECT_NAME} VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
# set(CMAKE_BUILD_TYPE "Release")

set(LLVM_INCLUDE_DIRS "/data/jrzhang/auforapro/llvm-project/build/include")
set(LLVM_LIBRARY_DIRS "/data/jrzhang/auforapro/llvm-project/build/lib")
list(INSERT CMAKE_PREFIX_PATH 0 "/usr/local" "/usr" "/usr/share")
#find_package(LLVM 10 REQUIRED)
# add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})



add_subdirectory(llvm-pass) 
