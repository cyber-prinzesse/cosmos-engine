# Cosmos Next patch series (Wine 11.21)

Applied in file-name order with `patch -p1` on top of the source in `inputs-next.json`
(release `wine-source-11.21`: Wine 11.21 with the macOS base carried onto it).
The first number is the order, the second the Cosmos patch it ports (see `../patches/` for the 11.0 originals).
Not here, because Wine 11.21 already does the same: 0001, 0017, 0023, 0026. Not yet ported: 0021.
The Cosmos theme and icons are not a patch: the build makes them with `cosmos-theme/make-theme.py` and
`cosmos-theme/install-icons.sh` (11.21's style folder is `aero.msstyles`).
Build: Actions › build-engine › line `next`, revision N → release `cosmos-11.21-rN`.
