cmake_minimum_required(VERSION 3.10)
set(CMAKE_CXX_STANDARD 17)
project(mapperPro VERSION 0.1.0 LANGUAGES C CXX)
list(INSERT CMAKE_PREFIX_PATH 0 "/usr/local" "/usr" "/usr/share")
find_package(nlohmann_json REQUIRED)
#find_package(spdlog REQUIRED)


# Main executable
set(MAIN_PATH ${PROJECT_SOURCE_DIR})
configure_file(include/dfg/python_path.h.in ../include/dfg/python_path.h)

file(GLOB_RECURSE SRCS ${CMAKE_SOURCE_DIR}/src/*.cpp)
add_executable(${PROJECT_NAME} ${CMAKE_SOURCE_DIR}/src/main.cpp ${SRCS})
target_include_directories(${PROJECT_NAME} PUBLIC ${CMAKE_SOURCE_DIR}/include)

#set(Python3_ROOT_DIR "/usr/bin")
set(Python3_ROOT_DIR "$ENV{CONDA_PREFIX}")
set(Python3_FIND_STRATEGY "LOCATION")
find_package(Python3 REQUIRED COMPONENTS Development)
target_include_directories(${PROJECT_NAME} PRIVATE ${Python3_INCLUDE_DIRS})
target_link_libraries(${PROJECT_NAME} PRIVATE ${Python3_LIBRARIES})

target_link_libraries(${PROJECT_NAME} 
    PRIVATE 
        nlohmann_json::nlohmann_json

)
