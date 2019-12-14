#!/bin/bash -ex
poetry install
poetry export -f requirements.txt --without-hashes -o requirements.txt
