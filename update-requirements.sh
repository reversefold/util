#!/bin/bash -ex
poetry install
poetry run pip freeze | grep -v reversefold.util | tee requirements.txt
