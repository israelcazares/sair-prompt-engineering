# Prompt variant inventory

`MANIFEST.csv` inventories the 76 `cheat_sheet_variant_*` files from the author's
research repository. There are 72 files in this directory. The other four
(`AN3c`, `AN19c`, `AN38`, `AN45c`) remain in `cheatsheets/`; their bytes and
SHA-256 hashes match the private sources, so they are referenced rather than
duplicated. All `file` and `screening_result_file` paths are repository-relative.

Each manifest row records the source filename's variant identifier, byte count,
SHA-256, and source modification time in UTC. Modification time is filesystem
metadata, not a verified experiment date. Files with `_playground`, `_agnostic`,
or similar suffixes retain those identifiers.

`appears_in_paper` is `sí` when that exact variant identifier occurs in
`papers/paper-sair-v16.tex`, otherwise `no`. A mention does not establish that
the current file's exact bytes were used in an experiment.

`screening_result_file` lists released result files associated by variant name,
separated by semicolons; an empty field means that no corresponding result is
included in this release. See `results/screening/MANIFEST.csv`. These are filename
associations: historical JSON files do not preserve a cheatsheet hash, and some
record a different `metrics.size_bytes` from the base variant. Exact historical
file-to-run identity in those cases is **NO VERIFICADO**.

The submitted prompt reconstructed for `EQT01-T00458` is a separate 2,242-byte
artifact in `results/nov2026/T00458_cheatsheet.txt`. It is not counted as a 77th
private `cheat_sheet_variant_*` file.
