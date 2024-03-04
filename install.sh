#!/bin/sh
# This script is the standard entrypoint for the package manager to generate
# the three agent metadata files: agent.json, commands.json, and protocols.json.
# 
# This script should be run immediately after the server decompresses the package,
# after which it can be assumed that all relevant metadata files are available
# (and future metadata files, if any) and can be used to generate the relevant
# models for the Django backend.
pip3 install -r requirements.txt -U
python3 -m src.meta.generate_metadata