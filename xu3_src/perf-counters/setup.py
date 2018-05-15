from distutils.core import setup, Extension

# Define module
perf_module = Extension('perf_module', sources=['perf_module.c'])

# Run setup
setup(ext_modules=[perf_module])
