#!/bin/bash -ex
pip-compile
pip-compile -o dev-requirements.txt dev-requirements.in requirements.txt
