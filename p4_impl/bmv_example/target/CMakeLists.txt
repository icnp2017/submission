project(simple_router)
cmake_minimum_required(VERSION 3.0)

set(CMAKE_EXPORT_COMPILE_COMMANDS 1)
set(CMAKE_CXX_FLAGS "--std=c++1z -ggdb -O0 ${CMAKE_CXX_FLAGS}")
set(CMAKE_CXX_FLAGS_DEBUG "-DBMDEBUG_ON ${CMAKE_CXX_FLAGS_DEBUG}")

if (NOT SET_MAX_FIELD_NUM_SOURCES)
    set(SET_MAX_FIELD_NUM_SOURCES 10)
endif()
if (NOT COMPRESS_NUM_SOURCES)
    set(COMPRESS_NUM_SOURCES 10)
endif()

add_definitions(-DSET_MAX_FIELD_NUM_SOURCES=${SET_MAX_FIELD_NUM_SOURCES} -DCOMPRESS_NUM_SOURCES=${COMPRESS_NUM_SOURCES})

find_package(Boost REQUIRED thread system)
find_library(GMP_LIBRARIES gmp)
find_path(GMP_INCLUDES NAMES gmp.h)
find_path(BM_INCLUDES NAMES bm/bm_runtime/bm_runtime.h)
find_library(BM_LIBRARIES bmall)

include_directories(SYSTEM
  ${Boost_INCLUDE_DIRS}
  ${GMP_INCLUDES}
  ${BM_INCLUDES}
)

add_custom_target(primitives ALL
    python ${CMAKE_SOURCE_DIR}/generate_primitives.py ${SET_MAX_FIELD_NUM_SOURCES} ${COMPRESS_NUM_SOURCES} -o ${CMAKE_BINARY_DIR}/primitives.json)

add_executable(simple_router simple_router.cpp primitives.cpp)
target_link_libraries(simple_router ${GMP_LIBRARIES} ${Boost_LIBRARIES} ${BM_LIBRARIES})
