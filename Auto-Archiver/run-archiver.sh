#!/bin/bash
# Usage: ./run_archiver.sh <URL>

# Activate the virtual environment
source AA-ENV/bin/activate

# Run the Python script with the provided URL
python Auto_Archiver.py "$1"

# Deactivate the virtual environment (optional)
deactivate