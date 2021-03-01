#   Copyright 2018 Edoardo Pasca
#cmake_minimum_required (VERSION 3.0)

project(RGL_core)
#https://stackoverflow.com/questions/13298504/using-cmake-with-setup-py

# The version number.

set (CIL_VERSION $ENV{CIL_VERSION} CACHE INTERNAL "Core Imaging Library version" FORCE)

# conda orchestrated build
message("CIL_VERSION ${CIL_VERSION}")
#include (GenerateExportHeader)

## Build the regularisers package as a library
message("Creating Regularisers as a shared library")

set(CMAKE_BUILD_TYPE "Release")

set (EXTRA_LIBRARIES "")
if(WIN32)
  set (FLAGS "/DWIN32 /EHsc /DCCPiCore_EXPORTS /openmp")
  set (CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /NODEFAULTLIB:MSVCRT.lib")
  message("library lib: ${LIBRARY_LIB}")
elseif(APPLE)
  set (FLAGS "-DCCPiReconstructionIterative_EXPORTS ")
elseif(UNIX)
   set (FLAGS "-O3 -funsigned-char -Wall  -Wl,--no-undefined  -DCCPiReconstructionIterative_EXPORTS ")
   set(EXTRA_LIBRARIES "m")
endif()
  set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${FLAGS}")
  set (CMAKE_C_FLAGS "${CMAKE_CXX_FLAGS} ${FLAGS}")
message("CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS}")

## Build the regularisers package as a library
message("Adding regularisers as a shared library")

add_library(cilreg SHARED
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/FGP_TV_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/SB_TV_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/PD_TV_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/TGV_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/Diffusion_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/Diffus4th_order_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/LLT_ROF_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/ROF_TV_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/FGP_dTV_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/TNV_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/Nonlocal_TV_core.c
            ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/PatchSelect_core.c
	    ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/utils.c
	    )
target_link_libraries(cilreg ${OpenMP_EXE_LINKER_FLAGS} ${EXTRA_LIBRARIES})
include_directories(cilreg PUBLIC
                      ${LIBRARY_INC}/include
					  ${CMAKE_CURRENT_SOURCE_DIR}
		              ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_CPU/ )

## Install

if (UNIX)
message ("I'd install into ${CMAKE_INSTALL_PREFIX}/lib")
install(TARGETS cilreg
	LIBRARY DESTINATION lib
	CONFIGURATIONS ${CMAKE_BUILD_TYPE}
	)
elseif(WIN32)
message ("I'd install into ${CMAKE_INSTALL_PREFIX} lib bin")
  install(TARGETS cilreg
	RUNTIME DESTINATION bin
	ARCHIVE DESTINATION lib
	CONFIGURATIONS ${CMAKE_BUILD_TYPE}
	)
endif()



# GPU Regularisers
if (BUILD_CUDA)
    find_package(CUDA)
    if (CUDA_FOUND)
      set(CUDA_NVCC_FLAGS "-Xcompiler -fPIC -shared -D_FORCE_INLINES")
      message("CUDA FLAGS ${CUDA_NVCC_FLAGS}")
      CUDA_ADD_LIBRARY(cilregcuda SHARED
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/TV_ROF_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/TV_FGP_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/TV_PD_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/TV_SB_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/LLT_ROF_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/TGV_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/dTV_FGP_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/NonlDiff_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/Diffus_4thO_GPU_core.cu
        ${CMAKE_CURRENT_SOURCE_DIR}/regularisers_GPU/PatchSelect_GPU_core.cu
      )
      if (UNIX)
        message ("I'd install into ${CMAKE_INSTALL_PREFIX}/lib")
        install(TARGETS cilregcuda
        LIBRARY DESTINATION lib
        CONFIGURATIONS ${CMAKE_BUILD_TYPE}
        )
      elseif(WIN32)
        message ("I'd install into ${CMAKE_INSTALL_PREFIX} lib bin")
        install(TARGETS cilregcuda
        RUNTIME DESTINATION bin
        ARCHIVE DESTINATION lib
        CONFIGURATIONS ${CMAKE_BUILD_TYPE}
        )
      endif()
    else()
      message("CUDA NOT FOUND")
    endif()
endif()

if (${BUILD_MATLAB_WRAPPER})
  if (WIN32)
        install(TARGETS cilreg DESTINATION ${MATLAB_DEST})
        if (CUDA_FOUND)
            install(TARGETS cilregcuda DESTINATION ${MATLAB_DEST})
        endif()
  endif()
endif()
