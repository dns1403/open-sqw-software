# Custom graphs and versioned experiments

The existing quantum engines accept finite, connected, simple, loopless
undirected graphs with at least two vertices. Custom browser/API experiments
use stable nonnegative integer IDs, at most 32 vertices and 128 undirected edges.
Each undirected edge produces both directed arcs; `(x,y)` still means y to x.
IDs and neighbor lists are sorted numerically, independently of labels/layout.
Matrices use that explicit order for outgoing rows z and incoming columns y.
The core operators and their mathematical assumptions are unchanged.

`graph.kind='custom'` requires `size`, `vertices`, `edges`, and `neighbors`.
The API validates edges via the existing GraphModel and requires the supplied
neighbor lists to equal the canonical sorted lists. A noncanonical port order
is rejected, never silently used to reinterpret matrices or omega. Preset
requests remain compatible. All simulation and research endpoints use this
same graph contract and existing numerical engines/caches.

The version-one saved format is `{format:'sqw-experiment', version:1,
experiment:SimulationRequest, vertices:[{id,label,position:[x,y]}],
matrix_presets:{id:preset_or_null}}` (valid JSON uses double quotes).
`experiment.graph` is explicit/custom; `experiment.scattering` contains every
matrix in complex `[real,imaginary]` pairs. Initial pure/mixed states, omega,
beta, mode, strategy, vertex dynamics, seed and steps use existing API fields.
Positions and display labels are presentation metadata and never enter operators.
Matrix-preset tags are informational; stored matrix entries are authoritative.

`POST /api/experiments/validate` validates the entire document, including saved
Vertex parameters even in an Edge mode, and returns the validated document and
graph. Unknown versions, malformed graph/ports, nonunitary matrices, invalid
states and mismatched metadata are rejected before replacing browser state.
No physical repair, normalization or unitary projection is automatic.

Permutation scattering is a seeded permutation of Identity columns. All five
existing families remain available; arbitrary degree-one U(1) phases use the
same complex matrix validator. Unitarity uses max-entry absolute residual
`max(abs(S†S-I)) <= 1e-10`, matching the existing core tolerance.

The browser draft stores stable IDs, labels/positions, undirected edges and
each accepted matrix together with the exact ports it was entered for.
Structural edits retain surviving matrix records. A different neighbor set,
even of the same degree, marks the matrix incompatible until explicitly
reinitialized/applied. Renaming and dragging do not change scientific bindings.
Manual omega vectors likewise retain their original ports. Initial vectors and
densities bind to the full ordered physical basis; surviving basis-state labels
remain well-defined. Invalid/unapplied matrix drafts block custom simulation.
Deleted vertices remove their own records through an explicit delete action;
IDs are not reused while editing. Preset copies are independent deep copies.

## Browser workflow

1. Choose **Custom Graph**, then **Add Vertex** and click three blank canvas
   locations. The fresh stable IDs 0, 1, 2 have display labels A, B, C.
2. Choose **Add Edge**. Click A then B, then B then C. The first endpoint is
   highlighted and named while a connection is pending. Self-loops and duplicate
   undirected connections are rejected. Use **Select / Move** to stop editing.
   **Connect and select using lists** is the keyboard/mobile alternative.
3. Select B and choose Hadamard. Set A/C via an applicable preset or edit a cell;
   for example `i` at A and `1` at C are valid U(1) matrices. Rows/columns name
   current stable neighbor IDs, not movable display labels. Small matrices have
   cell controls; every degree also has the full JSON editor.
4. Choose an initial basis edge or a preset preparation. Custom pure/mixed
   inputs use finite `[real, imaginary]` pairs in the displayed ordered basis.
   **Validate & use initial state** checks normalization and, for mixed states,
   Hermiticity/positivity. The explicit template button replaces only the draft.
5. Run any existing mode and research panel. For a separate Vertex initial
   space, select/validate the vertex preparation. Manual omega/beta live under
   Vertex parameters; review old/current omega ports after structural changes.
6. Export a valid experiment; import it later and confirm replacement of an
   existing custom draft. Malformed files keep the existing experiment intact.
   The example `examples/custom_path_phase.json` was exported by this workflow.

Renaming or moving does not clear simulation results. Structure, matrices,
initial-state or active parameter changes invalidate results and dependent
analysis. A pending edited matrix cannot be bypassed by pressing Run. Unapplied
complex matrix, initial-state and manual parameter text survive language changes;
custom scientific drafts also survive model/preset navigation. Applied initial
states for Edge and Vertex are kept separately while editing.

Matrix utilities copy only between equal degrees, in each destination's explicit
port order. Copy/replace operations require confirmation where they overwrite
multiple matrices or an existing graph draft. Identity, Grover, degree-2
Hadamard, DFT and random unitary presets remain available, plus permutation.
Selected-node random/permutation generation uses the displayed seed. Applying
one family to all custom vertices uses `(seed + sorted_vertex_index) mod 2^32`;
this is reproducible but is not the single-generator preset-graph construction
sequence. Saved numerical matrices, rather than regeneration from tags, define
reloaded experiments. Generation and simulation each create their own NumPy
RNG; statistics retains its separate trajectory-seed control.

`POST /api/scattering/validate` takes `{degree, matrix}` with complex pairs and
returns the validated matrix and max-entry residual. It does not require other
vertices to be finished, so a disconnected draft can be completed one matrix at
a time. Final simulations still validate the complete graph and experiment.

## Limits and persistence scope

- At most 32 nonnegative integer IDs (0..2^31-1), 128 undirected edges, and a
  connected loopless simple final graph. Existing simulation work budgets and
  dense-inspection dimension limits continue to apply.
- JSON v1 accepts only canonical ascending-ID neighbor order. Arbitrary port
  permutations are rejected; no automatic simultaneous basis permutation is
  implemented. Layout and labels never define ordering.
- Browser imports are capped at 2,000,000 bytes. Only validated complete custom
  experiments can be exported; incomplete drafts have no separate file format.
- Files store the active model's initial state and main simulation controls
  (mode, steps, strategy, vertex dynamics, seed), plus omega/beta. They do not
  save playback frames, secondary research-panel controls/results, unapplied
  text, or the inactive model's alternate initial state. Rerun after import.
- The in-memory custom draft survives switching to presets, but not page reload
  or closing. There is no autosave, undo/redo, cloud, account or database.
- Node selection uses display label plus stable ID. Scientific matrices, atom
  labels and probability axes retain numeric IDs to keep port/basis references
  unambiguous.

The next useful editor increment is draft autosave plus undo/redo, preserving
these physical bindings rather than merely restoring shapes. Further research
priorities remain support sensitivity, finite-atomic MMD and sparse Vertex
construction, under the existing mathematical contracts.
