#!/bin/bash

prepare() {
    echo "Preparing the environment..."
    # Updating apt package database
    apt-get -y update
    
    # Installing required packages
    apt-get -y install git python-pip
}

install_p4_dependencies() {
    # Installing P4 HLIR support library
    pip install git+https://github.com/p4lang/p4-hlir.git@4ad9d236aba95800c0ea08c30b36ff831e932dd2
    
    # Installing BMV 2.0 P4 compiler
    pip install git+https://github.com/p4lang/p4c-bm.git@6482e34e524e208bd4ccd9af832bf9032c9ad9f8
}

install_behavioral_model() {
    behavioral_model_dir=$(mktemp -d)

    if [ ! -d "$behavioral_model_dir" ]; then
        # Prepare repository
        git clone https://github.com/p4lang/behavioral-model.git "$behavioral_model_dir"
        cd "$behavioral_model_dir"
        git checkout e182c0f1876541221fdeb27c596cc95d054b391f
    fi
    cd "$behavioral_model_dir"

    # Install dependencies
    ./install_deps.sh

    # Configure project
    ./autogen.sh
    ./configure ${BEHAVIORAL_MODEL_CONFIGURE_FLAGS}

    # Compile
    make

    # Install
    make install

    # Cleanup
    rm -rf "$behavioral_model_dir"
}

install_p4t_dependencies() {
    apt-get -y install libboost-python1.58-dev
}

if (( $# == 0 )); then
   phases=(prepare install_p4_dependencies install_behavioral_model install_p4t_dependencies)
else
   phases=("$@")
fi

for phase in ${phases[@]}; do
    $phase
done
