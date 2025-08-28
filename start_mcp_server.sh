#!/bin/bash

# Permanent fix for macOS ARM64 mutex lock issues
# Must be set BEFORE Python starts

echo "🔧 Setting up environment for macOS ARM64 mutex lock fix..."

# Force single-threaded BLAS operations
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# macOS specific fixes
export SKLEARN_ENABLE_X64_BINARY_COMPATIBILITY=0
export OPENBLAS_CORETYPE=ARMV8
export NPY_NUM_BUILD_JOBS=1

# TensorFlow/PyTorch fixes
export TF_CPP_MIN_LOG_LEVEL=3
export PYTORCH_ENABLE_MPS_FALLBACK=1
export CUDA_VISIBLE_DEVICES=""

# Limit thread usage globally
export PYTHONTHREADS=1

echo "✅ Environment configured for mutex lock prevention"
echo "🚀 Starting MCP server..."

# Start the server
python smart_mcp_server.py --port 8081