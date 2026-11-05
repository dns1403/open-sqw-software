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
