# MoTR: Mouse-Tracking for Reading

This repository contains the implementation of **MoTR**, a framework designed to bridge the biomechanical gap between manual cursor movements and eye-tracking (ET) signals. The goal is to provide a scalable, low-cost proxy for cognitive reading research.

## Core Methodology

The main challenge with mouse-tracking is the motor-induced noise and the speed difference between hand and eye. MoTR solves this through three layers:

1. **The Row-Level Gatekeeper:** A constraint system that eliminates vertical drift and ensures the signal captures purely horizontal cognitive progression.
2. **Hertz-based Velocity Transformation:** Instead of raw timestamps, we project signals into the velocity domain ($Hz$). This normalizes the "mechanical inertia" of the hand relative to the eye.
3. **BERT-enhanced Fusion Model:** A multi-modal architecture that aligns hand movement speed with the semantic complexity of the text (extracted via BERT).

## Key Results (Romanian MultiplEYE Corpus)

The framework was validated on long-form Romanian text, showing that normalized mouse signals follow the same cognitive laws as gaze:

* **Word Length Effect (WLE):** Achieved $r \approx 0.95$ correlation in the velocity domain, proving that MoTR captures word-level processing effort.
* **Predictive Accuracy:** Our Fusion Model reached $\rho \approx 0.34$, approaching the empirical ceiling of human behavioral variance ($r \approx 0.46$).
* **Internal Consistency:** High stability across sessions ($\rho \approx 0.58$).
