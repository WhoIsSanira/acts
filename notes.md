#source /cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-ubuntu2204-gcc11-opt/setup.sh



cmake -S . -B build -GNinja -DACTS_BUILD_PLUGIN_DD4HEP=ON -DACTS_BUILD_EXAMPLES_PYTHON_BINDINGS=ON -DACTS_BUILD_EXAMPLES_DD4HEP=ON -DACTS_BUILD_FATRAS=ON -DACTS_BUILD_ODD=ON


cmake --build build

