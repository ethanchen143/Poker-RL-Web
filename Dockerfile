# Use a Python 3.11 base image for x86_64
FROM --platform=linux/amd64 python:3.11

# Install Cython
RUN pip install cython

# Set the working directory
WORKDIR /app

# Copy source files
COPY hand_rank_monte_carlo.pyx /app/
COPY setup.py /app/

# Build the Cython extension
RUN python setup.py build_ext --inplace
