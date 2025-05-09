#!/bin/bash

# Create a new conda environment with Python 3.9
conda create -y -n search_comparisons python=3.9

# Activate the new environment
eval "$(conda shell.bash hook)"
conda activate search_comparisons

# Upgrade pip
pip install --upgrade pip

# Install uv for faster package installation
pip install uv

# Install dependencies using uv
uv pip install -r requirements.txt

# Install development dependencies
uv pip install -e .

# Create necessary directories if they don't exist
mkdir -p src/search_comparisons tests
touch src/search_comparisons/__init__.py tests/__init__.py

# Initialize git if not already initialized
if [ ! -d .git ]; then
    git init
    git add .
    git commit -m "Initial commit"
fi

echo "Development environment setup complete!"
echo "To activate the environment, run: conda activate search_comparisons" 