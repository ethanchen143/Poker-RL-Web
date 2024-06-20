# Use a Python 3.11 base image
FROM python:3.11

# Install Cython
RUN pip install cython

# Set working directory
WORKDIR /app

# Copy source files
COPY hand_rank_monte_carlo.pyx /app/

# Create setup.py for building the extension
RUN echo "from setuptools import setup \nfrom Cython.Build import cythonize \nsetup(ext_modules=cythonize('hand_rank_monte_carlo.pyx'))" > setup.py

# Build the Cython extension
RUN python setup.py build_ext --inplace