#!/bin/bash

set -e
base="$PWD"

for library in scikit-bio; do
    cd $library
    python3 -m build --wheel --outdir $base
    cd ..
done
