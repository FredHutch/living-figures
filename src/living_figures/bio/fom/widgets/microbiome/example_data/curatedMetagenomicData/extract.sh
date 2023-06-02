#!/bin/bash

set -e

# Make sure that Docker is running
IMG=waldronlab/curatedmetagenomicanalyses
docker pull $IMG
docker run \
    -it \
    --rm \
    -v $PWD:/share \
    $IMG \
    /bin/bash -c "cd /share; Rscript extract.R" \
    2>&1 | tee extract.log
