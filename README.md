# Core Distinguishability Relativity (CDR)

**Status:**
- Phase I ✅ COMPLETE (7/7 gates PASS)
- Phase II.1A (Empirical validation – energy systems) ✅ COMPLETE
- Phase II.1B (Empirical validation – neurodynamics) 🚧 IN PROGRESS

---

## What is CDR?

**Core Distinguishability Relativity (CDR)** is a pre-registered framework designed to detect **information-driven selection bias in observed dynamics** without falling into common statistical pitfalls such as p-hacking, circular reasoning, or model over-flexibility.

The framework focuses on answering a fundamental scientific question:

> When we observe a dynamic system, how do we know whether a detected pattern is a real causal effect or merely an artifact of noise or modeling assumptions?

CDR addresses this through:

- **Pre-registered hypotheses**
- **Mandatory validation gates**
- **Adversarial and structural controls**
- **Out-of-sample generalization tests**

Instead of relying solely on p-values, CDR requires **multiple orthogonal validation gates** to pass before any claim can be considered detectable.

---

## Project Roadmap

The CDR validation program is divided into four empirical phases.

| Phase       | Objective                                             | Status         |
|-------------|-------------------------------------------------------|----------------|
| Phase I     | Toy-model validation (controlled system)              | ✅ Complete     |
| Phase II.1A | Real-world validation on physical infrastructure data | ✅ Complete     |
| Phase II.1B | Validation in complex neural systems (fMRI)           | 🚧 In progress |
| Phase II.2  | Validation in large-scale human mobility systems      | Planned        |
| Phase III   | Laboratory experiments (EEG / RNG)                    | Planned        |

---

## Phase I — Toy Model Validation (Completed)

Phase I validates the CDR framework in a **fully controlled environment** using a small enumerated system.

**Model used:**
- 2-component Ising conditional kernel
- Binary state variables
- Known ground-truth coupling parameter ε

**State space:**
```
2 components × binary states → 4 possible states
```

This allows full control of the generative process.

### Phase I Gates

Seven validation gates were defined:

| Gate | Meaning                                         |
|------|-------------------------------------------------|
| G1   | H₀ recovery (ε = 0 detected correctly)          |
| G2   | H₁ recovery (ε > 0 recovered correctly)         |
| G3   | Control collapse (time-shuffle destroys signal) |
| G4   | Parameter identifiability                       |
| G5   | Stability under configuration perturbations     |
| G6   | Adversarial baseline robustness                 |
| G7   | Out-of-sample generalization                    |

**Result:**
```
CDR Phase I+ — Gates G1–G7
────────────────────────────
G1_H0_recovery: PASS
G2_H1_recovery: PASS
G3_controls_collapse: PASS
G4_identifiability: PASS
G5_stability: PASS
G6_adversarial: PASS
G7_out_of_sample: PASS
────────────────────────────
FINAL: PASS
```

---

## Phase II — Empirical Validation

Phase II moves the framework from toy models to **real-world observational systems**.

The goal is to verify that the method:

1. Detects reweighting when it exists
2. Does not detect false positives in physical systems
3. Remains stable under realistic data conditions

---

## Phase II.1A — Energy Infrastructure Validation (Completed)

**Dataset:** Open Power System Data (OPSD)

**Variables used:**
- Electricity load
- Wind generation
- Solar generation
- Day-ahead electricity price

**Time resolution:**
```
1 hour intervals
8760 observations (1 year: 2019-01-01 to 2019-12-31)
Region: Germany/Luxembourg grid (DE_LU)
```

### Method

The system state was constructed from discretized energy variables:
```
state = (load_bin, wind_bin, solar_bin, price_bin)
```

Transitions between states were modeled using:
```
P(s_{t+1} | s_t)
```

The empirical baseline kernel:
```
P₀(s_{t+1} | s_t) ~ Dirichlet(α)
```

The CDR hypothesis introduces a reweighting parameter:
```
P(s_{t+1} | s_t) ∝ P₀(s_{t+1} | s_t) · exp(ε Φ(s_t, s_{t+1}))
```

Where:
```
ε = information-driven selection parameter
Φ = distinguishability feature function
```

**Discretization:**
- 3 bins per variable (quantiles: 0.33, 0.66)
- Total state space: 3⁴ = 81 states
- Missing data policy: drop (final dataset: 8740 rows)

**Epsilon grid:**
```
ε ∈ [0.00, 0.01, 0.02, ..., 0.80] (81 points)
```

### Phase II.1A Gates

| Gate | Meaning                                          |
|------|--------------------------------------------------|
| F1   | Injection recovery (method recovers simulated ε) |
| F2   | Control collapse (domain-specific surrogates)    |
| F3   | Train/test generalization (75/25 split)          |
| F5   | Discretization sensitivity (bins=3 vs bins=4)    |

**Result:**
```
CDR Phase II — Gates
────────────────────────────────
F1_injection_recovery: PASS
  eps_hat: 0.30, eps_true: 0.30, error: 0.0
  
F2_controls_collapse: PASS
  Collapse controls (seasonal-aware):
    - weekly_blocks: ε = 0.00 ✅
    - seasonal_strata: ε = 0.00 ✅
  median_eps_controls: 0.00
  fraction_below_tol: 1.00 (100%)
  
  Stress controls (diagnostic):
    - rows_shuffle: ε = 0.48
    - columns_shuffle: ε = 0.32
    
F3_holdout_generalization: PASS
  eps_train: 0.00, eps_test: 0.00
  abs_delta: 0.00
  
F5_sensitivity: PASS
  eps_bins3: 0.00, eps_bins4: 0.00
  abs_delta: 0.00
────────────────────────────────
FINAL: PASS ✅
```

### Key Findings

**1. Framework Validation:**
- CDR successfully recovered injected reweighting (F1: ε_injected = 0.30, ε_recovered = 0.30, error = 0.0)
- Domain-specific negative controls collapsed appropriately (F2: 100% of collapse controls → ε ≈ 0)
- Estimator generalized across temporal holdout (F3: train/test consistency)
- Results stable under discretization changes (F5: bins=3 vs bins=4)

**2. OPSD Findings:**
- German electrical grid (2019) exhibits **ε ≈ 0.0** (no detectable structural selection)
- This is expected for highly regulated energy systems with centralized economic dispatch
- Result validates framework's ability to correctly identify **null cases**

**3. Surrogate Design:**
- Seasonal-aware surrogates (preserving hour-of-day, day-of-week structure) are essential for energy systems
- Aggressive surrogates (rows_shuffle, columns_shuffle) create non-physical regimes and should be used only as stress tests

---

## Phase II.1B — Neural Dynamics Validation (In Progress)

**Next step:** Apply the same CDR pipeline to **neural activity dynamics**.

**Dataset candidates:**
- Human Connectome Project (HCP)
- OpenNeuro fMRI datasets

**System state construction:**
```
state = (DMN, Salience, Visual, Motor, ...)
```

This domain introduces:
- Nonlinear dynamics
- Adaptive feedback
- Complex state transitions

making it an ideal testbed for the CDR framework.

---

## Phase II.2 — Large-Scale Human Systems (Planned)

Future validation will examine:
- Traffic flow systems (PeMS)
- Urban mobility networks (Citi Bike)

These systems exhibit **collective human dynamics** and may present different statistical structures than physical infrastructure.

---

## Phase III — Laboratory Experiments (Planned)

Controlled experiments combining:
- EEG recordings
- Quantum random number generators (QRNG)

**Goal:** Test whether **neural states correlate with deviations in quantum randomness** under a fully pre-registered protocol.

---

## Project Structure
```
cdr-phase1-validation/
│
├── config/
│   ├── __init__.py
│   ├── phase1_config.py
│   └── phase2_config.py
│
├── data/
│   ├── interim/
│   ├── processed/
│   └── raw/
│       └── opsp/
│           ├── datapackage.json
│           ├── README.md
│           ├── time_series.sqlite
│           └── time_series_60min_singleindex.csv
│
├── results/
│   ├── golden_run_phase1_plus_v1/
│   ├── phase2_opsp/
│   │   ├── bins_specs.json
│   │   ├── checkpoint_controls.json
│   │   ├── checkpoint_eps.json
│   │   ├── data_report.json
│   │   ├── ll_injection.png
│   │   ├── ll_test.png
│   │   ├── ll_train.png
│   │   ├── phase2_config.json
│   │   ├── phase2_results.json
│   │   ├── report.txt
│   │   └── selection.json
│   └── .gitkeep
│
├── scripts/
│   ├── __init__.py
│   ├── make_audit_bundle.py
│   └── run_phase1_plus_full.py
│
├── src/
│   ├── kernels/
│   │   ├── empirical_kernel.py
│   │   └── reweighted_kernel.py
│   ├── __init__.py
│   ├── adversarial_kernel.py
│   ├── artifacts.py
│   ├── build_states.py
│   ├── controls.py
│   ├── controls_phase2.py
│   ├── discretize.py
│   ├── estimators.py
│   ├── ising_kernel.py
│   ├── model_selection.py
│   ├── opsp_loader.py
│   ├── phase1_plus_runner.py
│   ├── phase1_runner.py
│   ├── phase2_runner.py
│   ├── statistics.py
│   ├── validators.py
│   └── validators_phase2.py
│
├── tests/
│   ├── __init__.py
│   ├── test_controls.py
│   ├── test_estimators.py
│   ├── test_ising.py
│   ├── test_phase1_plus_runner.py
│   ├── test_statistics.py
│   └── test_validators.py
│
├── venv/ (library root)
│
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

---

## Installation

**Requirements:**
```
Python 3.8+
numpy
scipy
pandas
matplotlib
```

**Setup:**
```bash
git clone https://github.com/ThiagoLuzpY/cdr-phase1-validation.git
cd cdr-phase1-validation

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Running Phase II (Energy Validation)
```bash
python src/phase2_runner.py
```

**Results are saved in:**
```
results/phase2_opsp/
```

**Key outputs:**
- `phase2_results.json` - Complete numerical results
- `report.txt` - Gate pass/fail summary
- `ll_train.png`, `ll_test.png`, `ll_injection.png` - Likelihood curves
- `checkpoint_controls.json` - Intermediate control results
- `bins_specs.json` - Discretization bin edges

---

## Reproducibility

The pipeline guarantees reproducibility through:

- Fixed random seeds (configurable in `phase2_config.py`)
- Serialized configuration artifacts
- Saved bin specifications (prevents discretization drift)
- Likelihood curve plots (visual validation)
- Checkpoint files (allows resumption after failures)

**All experiments are fully deterministic** given the same config and random seeds.

---

## Methodological Inspiration

- Popper, K.R. (1959). *The Logic of Scientific Discovery.*
- Lakatos, I. (1978). *The Methodology of Scientific Research Programmes.*
- Rosen, R. (1991). *Life Itself: A Categorical Approach to Biology.*

---

## References

Luz, T. (2026). **Core Distinguishability Relativity: Parts I–IV**. Zenodo. (DOI pending)

Petina, A. (2025). **The Minimal Architecture of Distinguishability (ANAM)**.

Open Power System Data. (2020). *Time series data for electricity systems*. https://open-power-system-data.org/

---

## Citation
```bibtex
@software{luz2026cdr,
  title={Core Distinguishability Relativity: Empirical Validation Framework},
  author={Luz, Thiago},
  year={2026},
  url={https://github.com/ThiagoLuzpY/cdr-phase1-validation},
  note={Phase I and Phase II.1A complete}
}
```

---

## License

CC0 1.0 Universal (Public Domain)

This work is dedicated to the public domain. You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission.

---

## Author

**Thiago Luz**  
Independent Researcher  
São Gonçalo, Rio de Janeiro, Brazil

**GitHub:** https://github.com/ThiagoLuzpY/  
**ORCID:** (pending registration)

---

## Acknowledgments

Special thanks to:
- Open Power System Data project for providing high-quality energy infrastructure data
- The scientific community for open-source tools (NumPy, SciPy, pandas, matplotlib)

---

**Last updated:** March 2026  
**Status:** Phase I complete ✅ | Phase II.1A complete ✅ | Phase II.1B in progress 🚧