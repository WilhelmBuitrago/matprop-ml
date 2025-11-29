# matprop-ml

A reproducible pipeline for predicting standard material properties using graph neural networks.

This repository provides an end-to-end system for machine-learning-based prediction of standard properties of crystalline materials, including:

- Band gap
- Formation energy per atom
- VBM / CBM positions
- (Optionally) E-above-hull and stability metrics

The project implements a complete workflow:

1. Dataset acquisition and cleaning using the Materials Project API.
2. Graph construction from CIF structures (MEGNet baseline, ALIGNN optional).
3. Training and validation pipelines for each property.
4. Model export and inference from a unified API.
5. Minimal user interface for submitting structures and visualizing predictions.

The primary goal is to deliver a functional MVP for materials property prediction, with emphasis on clarity, reproducibility and modular design. Future extensions include ALIGNN+ (with global-state support), spectral-property prediction, RAG-assisted querying, and structure generation.
