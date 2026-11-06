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

## Implemented behavior

The proposed six sections and all inventory destinations are implemented. The
desktop rail becomes an expandable two-column menu on small screens. The live
experiment summary stays visible while scrolling; its mobile strip and the
workflow strip can scroll independently without widening the page. Analysis
tabs explain purpose and prerequisites even when the current mode is Unitary.

The main introduction has seven steps. The first-walk and trajectory tutorials
each have six; long-time behavior has five. All use actual controls/results,
including class tables and Cesàro charts. No tour changes a model or runs an
experiment automatically. Next/Back, completion, skip, Escape, restart, missing
targets and language switching use the real Driver.js implementation in tests.

Accessibility includes semantic navigation/current-page indicators, a skip
link, visible focus, keyboard-operable controls/disclosures, labeled tour
dialogs, focus return, and a tour focus loop that includes numeric inputs,
sliders and summaries. Arrow keys inside inputs retain their native behavior.
Reduced-motion preference disables transitions. The probability graph in
Simulation also offers keyboard-operable vertex selection. Context help covers
basis direction, port orientation, trajectories, conditional atoms, stationary
laws, Cesàro averages and asymptotic variance, without removing qualifications.

## Changed files

| Area | Files |
| --- | --- |
| Shell, directory, help, probability view | `frontend/src/App.tsx`, `Workspace.tsx`, `StateGraph.tsx`, `workspace.css`, `main.tsx` |
| Tours and locked dependency | `frontend/src/onboarding.ts`, `frontend/package.json`, `frontend/pnpm-lock.yaml` |
| Mounted research sections and tour anchors | `frontend/src/ResearchPanels.tsx`, `StationaryPanel.tsx`, `StatisticsPanel.tsx` |
| Complete bilingual copy | `frontend/src/i18n/locales/en/app.json`, `de/app.json` |
| Regressions and shared existing fixtures | `frontend/src/__tests__/interface.test.tsx`, `customWorkflow.test.tsx`, `research.test.tsx`, `stationary.test.tsx`, `statistics.test.tsx`, `workspaceActions.ts`, `workspaceFixtures.ts` |
| Documentation and visual evidence | `README.md`, `docs/architecture.md`, this audit, `docs/screenshots/ui-overview.png`, `ui-mobile-de.png` |

## Validation

Automated regression: 418 Python tests; 85 frontend tests; TypeScript and Vite
production build. New regressions cover every directory destination, default
Overview, invisible controls, navigation with pending work, matrix/seed drafts,
ensemble/inspector/stationary/statistics result and selection retention, language
changes, real tour lifecycle/fallbacks, and independent practice-tab links.
Existing graph/port/import/scientific tests remain in place.

Actual browser checks (desktop and 390 × 844, English and German):

1. Opened the default Overview and inspected workflow/summary/directory.
2. Completed the seven-step introduction, including a mid-tour EN/DE switch.
3. Opened Graph & Matrices; selected a three-vertex path preset.
4. Created an independent custom copy; applied `i` at an endpoint and Hadamard
   scattering at the degree-two vertex.
5. Prepared a uniform input; ran eight steps; inspected playback and graph/plots.
6. Switched explicitly to Trajectory; ran and inspected the observation record.
7. Ran a 200-path ensemble; inspected the atom ket and reduced-state inspector.
8. Computed long-time classes, periods, mixture and Cesàro results.
9. Computed 2,000-observation trajectory statistics and its qualified interval.
10. Returned to Graph; verified the endpoint matrix still contained `i`.
11. Changed to German, restarted and skipped the introduction; analysis results
    remained available after returning to English.
12. Exported the custom experiment; reimported the downloaded JSON using the
    existing explicit replacement confirmation and verified success.
13. Tested the German mobile menu, overview and tour through its simulation step;
    document width stayed within the viewport. ArrowRight in the steps field
    kept the current tour step. Completed the other contextual tours on desktop,
    including prerequisite fallback and backward recovery.
14. Opened the practice link in another tab, verified a fresh three-vertex cycle,
    then returned to the original tab with its analysis results intact.

The development console contained one transient Vite reload error while a newly
imported stylesheet was still being created. Completed flows had no application
errors. A fresh page completed a 12-step Open run, long-time analysis and return
to Overview with zero console errors; the German mobile document width was
375 pixels inside the 390-pixel viewport. Screenshots record the final layout. No backend
operators, experiment schema, API field conventions or Material files changed.

## Remaining limits and follow-up

Navigation is session state, not URL routing; browser reload starts at Overview
and restores only explicit language/onboarding preferences. Scientific work is
saved by JSON export/import. Tours advance manually so users choose when a
calculation is ready; unavailable targets explain prerequisites instead of
inventing results. Large matrices and tables retain local scrolling. Scientific
plot bundles still trigger Vite's chunk-size warning. All retained result panels
consume memory until scientific invalidation or reload.

A useful next iteration is lazy loading of chart/tour bundles and user testing
with keyboard and screen-reader users. Full assistive-technology certification
and cross-browser/mobile-device coverage were not performed. No new mathematical
claims or numerical reductions were introduced.
