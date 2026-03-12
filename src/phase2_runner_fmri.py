from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from config.phase2_config_fmri import load_phase2_fmri_config
from src.fmri_loader import load_subject_timeseries
from src.discretize import fit_and_discretize
from src.build_states import make_encoding, encode_states, build_transitions
from src.kernels.empirical_kernel import EmpiricalKernel
from src.kernels.reweighted_kernel import ReweightedKernel
from src.validators_phase2 import (
    gate_F1_injection_recovery,
    gate_F2_controls_collapse,
    gate_F3_holdout_generalization,
    gate_F5_sensitivity,
    summarize,
)

# estimador já existente na trilha A
from src.phase2_runner import _estimate_epsilon_grid, _simulate_trajectory


def run_phase2_fmri():
    print("\n==============================")
    print("CDR Phase II.1B — fMRI Domain")
    print("==============================\n")

    # -------------------------------------------------
    # Config
    # -------------------------------------------------

    cfg = load_phase2_fmri_config()
    cfg.ensure_paths()

    print("[Phase2-fMRI] Configuration loaded")
    print("Dataset root:", cfg.dataset_root)
    print("Subject:", cfg.subject)
    print("Task:", cfg.task)

    # -------------------------------------------------
    # Load fMRI data
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Loading fMRI dataset...")

    result = load_subject_timeseries(
        dataset_root=cfg.dataset_root,
        subject=cfg.subject,
        task=cfg.task,
        atlas_name=cfg.atlas_name,
        atlas_data_dir=cfg.atlas_cache_dir,
        default_tr=cfg.default_tr,
        standardize=cfg.standardize,
        detrend=cfg.detrend,
        smoothing_fwhm=cfg.smoothing_fwhm,
        low_pass=cfg.low_pass,
        high_pass=cfg.high_pass,
        verbose=cfg.verbose,
    )

    df = result.dataframe.drop(columns=["time_seconds"])

    print("[Phase2-fMRI] fMRI loaded")
    print("Scans:", result.n_scans)
    print("ROIs:", result.n_rois)

    # -------------------------------------------------
    # Train/Test split
    # -------------------------------------------------

    n = len(df)
    split = int(0.75 * n)

    idx_train = np.arange(0, split, dtype=int)
    idx_test = np.arange(split, n, dtype=int)

    print("\n[Phase2-fMRI] Train/Test split")
    print("Train samples:", len(idx_train))
    print("Test samples:", len(idx_test))

    # -------------------------------------------------
    # Discretization
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Discretizing ROI signals...")

    df_disc, specs = fit_and_discretize(
        df,
        n_bins=cfg.n_bins,
        quantiles=cfg.quantiles,
        fit_on_index=idx_train,
    )

    print("[Phase2-fMRI] Discretization completed")

    # -------------------------------------------------
    # Build states and transitions
    # -------------------------------------------------

    # Criar encoding
    n_components = df_disc.shape[1]
    enc = make_encoding(n_components=n_components, n_bins=cfg.n_bins)
    n_states = cfg.n_bins ** n_components

    print(f"[Phase2-fMRI] State space: {n_components} ROIs x {cfg.n_bins} bins = {n_states} states")

    # Encode states
    components = df_disc.to_numpy(dtype=int)
    state_ids = encode_states(components, enc)

    # Build transitions
    curr_all, nxt_all = build_transitions(state_ids)

    # Split transitions
    curr_train = curr_all[:split - 1]
    nxt_train = nxt_all[:split - 1]
    curr_test = curr_all[split - 1:]
    nxt_test = nxt_all[split - 1:]

    print(f"[Phase2-fMRI] Transitions: train={len(curr_train)} | test={len(curr_test)}")

    # -------------------------------------------------
    # Build empirical kernel P0
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Building empirical baseline kernel P0...")

    P0 = EmpiricalKernel.from_transitions(
        curr_train,
        nxt_train,
        n_states=n_states,
        enc=enc,
        alpha=cfg.dirichlet_alpha,
    )

    print("[Phase2-fMRI] P0 built.")

    # Epsilon grid
    eps_grid = np.array(cfg.eps_grid, dtype=float)

    # -------------------------------------------------
    # Estimate epsilon (train)
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Estimating epsilon (train)...")

    eps_train, ll_train = _estimate_epsilon_grid(
        curr_train,
        nxt_train,
        P0,
        eps_grid,
        cfg.min_prob,
        label="fmri_train",
        progress_every=10,
    )

    print(f"[Phase2-fMRI] epsilon_train = {eps_train:.4f}")

    # -------------------------------------------------
    # Estimate epsilon (test)
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Estimating epsilon (test)...")

    eps_test, ll_test = _estimate_epsilon_grid(
        curr_test,
        nxt_test,
        P0,
        eps_grid,
        cfg.min_prob,
        label="fmri_test",
        progress_every=10,
    )

    print(f"[Phase2-fMRI] epsilon_test = {eps_test:.4f}")

    # -------------------------------------------------
    # Gate F1 — Injection recovery
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Running Gate F1 (injection recovery)...")

    eps_true = cfg.inj_eps_true

    # Simular trajetória com epsilon injetado
    sim_traj = _simulate_trajectory(
        P0,
        eps=eps_true,
        n_steps=len(curr_train),
        seed=cfg.random_seed,
    )

    sim_curr, sim_nxt = build_transitions(sim_traj)

    eps_injected, ll_inj = _estimate_epsilon_grid(
        sim_curr,
        sim_nxt,
        P0,
        eps_grid,
        cfg.min_prob,
        label="injection",
        progress_every=10,
    )

    gate1 = gate_F1_injection_recovery(
        eps_hat=eps_injected,
        eps_true=eps_true,
        tol_abs=cfg.gate_tol_abs,
    )

    print(f"[Phase2-fMRI] F1: eps_injected={eps_injected:.4f} vs eps_true={eps_true:.4f}")

    # -------------------------------------------------
    # Gate F2 — Controls collapse
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Running Gate F2 (controls collapse)...")

    eps_controls = []
    rng = np.random.default_rng(cfg.random_seed)

    for i in range(cfg.n_controls):
        # Shuffle state IDs
        shuffled_ids = state_ids.copy()
        rng.shuffle(shuffled_ids)

        # Build transitions
        c_ctrl, n_ctrl = build_transitions(shuffled_ids)
        c_ctrl_train = c_ctrl[:split - 1]
        n_ctrl_train = n_ctrl[:split - 1]

        # Estimate epsilon
        eps_c, _ = _estimate_epsilon_grid(
            c_ctrl_train,
            n_ctrl_train,
            P0,
            eps_grid,
            cfg.min_prob,
            label=f"control_{i + 1}",
            progress_every=20,
        )

        eps_controls.append(eps_c)
        print(f"  Control {i + 1}/{cfg.n_controls}: eps={eps_c:.4f}")

    gate2 = gate_F2_controls_collapse(
        eps_controls=eps_controls,
        tol=cfg.control_tol,
        required_fraction=cfg.control_fraction,
    )

    # -------------------------------------------------
    # Gate F3 — Holdout generalization
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Running Gate F3 (holdout generalization)...")

    gate3 = gate_F3_holdout_generalization(
        eps_train=eps_train,
        eps_test=eps_test,
        max_delta=cfg.holdout_delta,
    )

    # -------------------------------------------------
    # Gate F5 — Sensitivity
    # -------------------------------------------------

    print("\n[Phase2-fMRI] Running Gate F5 (sensitivity)...")

    df_disc2, _ = fit_and_discretize(
        df,
        n_bins=4,
        quantiles=(0.25, 0.75),
        fit_on_index=idx_train,
    )

    comps4 = df_disc2.to_numpy(dtype=int)
    enc4 = make_encoding(n_components=n_components, n_bins=4)
    n_states4 = 4 ** n_components
    ids4 = encode_states(comps4, enc4)
    c4, n4 = build_transitions(ids4)
    c4_train = c4[:split - 1]
    n4_train = n4[:split - 1]

    P0_4 = EmpiricalKernel.from_transitions(
        c4_train,
        n4_train,
        n_states=n_states4,
        enc=enc4,
        alpha=cfg.dirichlet_alpha,
    )

    eps_bins4, _ = _estimate_epsilon_grid(
        c4_train,
        n4_train,
        P0_4,
        eps_grid,
        cfg.min_prob,
        label="bins4",
        progress_every=10,
    )

    gate5 = gate_F5_sensitivity(
        eps_binsA=eps_train,
        eps_binsB=eps_bins4,
        max_delta=cfg.sensitivity_delta,
    )

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------

    gates = [gate1, gate2, gate3, gate5]

    summary = summarize(gates)

    print("\n==============================")
    print("CDR Phase II.1B (fMRI) — Gates")
    print("==============================")

    for g in gates:
        status = "PASS" if g.passed else "FAIL"
        print(f"{g.name}: {status} | metrics={g.metrics}")

    print("==============================")
    final_status = "PASS ✅" if summary["passed_all"] else "FAIL ❌"
    print(f"FINAL: {final_status}")

    # -------------------------------------------------
    # Save results
    # -------------------------------------------------

    results = {
        "eps_hat_train": eps_train,
        "eps_hat_test": eps_test,
        "eps_hat_injection": eps_injected,
        "eps_controls": eps_controls,
        "eps_hat_bins4": eps_bins4,
        "gates": summary,
    }

    results_path = cfg.results_dir / "phase2_fmri_results.json"

    with open(results_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"\nResults saved to: {results_path}")


if __name__ == "__main__":
    run_phase2_fmri()