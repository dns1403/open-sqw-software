# Navigation and onboarding audit

## Before implementation (6 November 2026)

Inspected `App.tsx`, graph/matrix/file editors, research/stationary/statistics panels, architecture, and the running application at desktop and 390 × 844. Baseline: 418 Python tests and 77 frontend tests pass.

The landing page exposed configuration before explaining the workflow. On mobile the entire configuration column preceded the graph and results. Advanced research tools appeared below the fold only after switching from Unitary; there was no feature directory, analysis navigation, or onboarding. Matrix editing and graph selection were related visually, but file management, initial preparation and analysis had competing priorities. Scientific qualifications were present and must remain.

## Feature inventory and proposed destinations

| Destination | Existing functionality retained |
| --- | --- |
| Overview | New workflow entry points, live readiness, complete feature directory |
| Graph & Matrices | Path/cycle/complete/star presets; independent custom copy; vertex/edge add, connect, select, delete, clear; labels/layout; graph validity; local/global DFT, Grover, identity, Hadamard, random and permutation matrices; cells/JSON editing and unitary validation; retained-port review; copy same-degree matrices; omega/beta; validated experiment JSON import/export |
| Simulation | All four walk modes; basis/uniform/maximally mixed/custom pure/custom density preparation; explicit basis; strategy; vertex mean/trajectory; steps/scattering seed; run/reset; probability distribution, graph colors, purity, time evolution; play/pause, single step and timeline |
| Quantum Trajectories | Recorded outcomes and probabilities; conditional state and atom stage; independent ensembles, empirical versus exact Born laws, atom counts, heatmap and sampled histories |
| Analysis → Inspector | Atom selection/ket; reduced M/P and transition probabilities; current density and post-measurement density |
| Analysis → Long-time | Support selection and qualifications; communicating/closed classes, periods, stationary class laws, absorption, initial-dependent mixture, density reconstruction, finite-time and Cesàro curves |
| Analysis → Statistics | Real label/outcome/Born/coherence observables; Poisson solutions, class means/variances and residuals; trajectory seed, warm-up, initialization, confidence; class-conditional sampling and uncertainty plots |
| Learn & Help | Optional restartable main tour and contextual tutorials; basis/matrix/trajectory/stationary/Cesàro/variance explanations; theoretical reference |

## State and interaction design

Navigation is presentation state, separate from the scientific experiment. Editor and analysis components stay mounted while hidden; navigation and language changes do not change API inputs or discard local drafts/results. Scientific input changes retain the existing invalidation rules. Analysis remains discoverable with an explanation of prerequisites in Unitary mode or while inputs require review.

The six destinations use a persistent desktop navigation rail and compact mobile navigation. Graph and matrix editing share a workspace. Initial preparation and execution are grouped in Simulation, while a freely navigable five-step workflow and live experiment summary remain available. Advanced raw representations use native disclosure controls. English and German use the existing six translation namespaces.

Driver.js supplies highlighting and keyboard/popover behavior ([official API](https://driverjs.com/docs/api)). A small React adapter handles section activation and translated steps. Tours are explicitly started, can be skipped/restarted, never mutate experiment inputs, and fall back to a prerequisite explanation when a target is unavailable. An example opens in an independent tab so unfinished work stays intact.
