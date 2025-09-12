#!/bin/bash

# run in this directory

# update
# pyproject.toml
# setup.py

rm -rf dist/
python3 -m build
twine upload dist/*

