# Cosmos

Cosmos is based on Wine. The icon (`cosmos-icon.jpg`) is Cosmopolitan's own.

Cosmos is the Wine engine of [Cosmopolitan](https://github.com/cyber-prinzesse/Cosmopolitan). It is built on the `cosmos`
branch of this fork: Highball's recipe and patch series (upstream `main` of gauthierpiarrette/highball-engine) plus
Cosmopolitan's own patches, built by `.github/workflows/build.yml` with `cosmos_revision` set.

- Tarball: `cosmos-<wine version>-r<N>.tar.gz` — Highball's layout (`engine/`, `renderers/`, `frameworks/`, `tools/`) with
  `wswine.bundle -> engine` for Cosmopolitan, and `COSMOS-BUILD.txt` naming the source pin, the patches and the commit.
- Wine source: CodeWeavers' CrossOver sources (LGPL-2.1-or-later), pinned by SHA-256 in `inputs.json`. The complete
  corresponding source of any Cosmos release is that tarball plus the `patches/` folder at the release's commit.
- Cosmopolitan's patches so far:
  - `0028`: a fault on a thread Wine didn't create ends the program instead of hanging it (also offered upstream as
    highball-engine PR #24);
  - `0029`: every program gets its own Dock name, from its Mac Driver `AppName` or its exe name;
  - `0030`: Mac Driver `NoDockIcon`, so Steam shows one Dock icon;
  - `0031`: dark title bars (Mac Driver `Appearance`), the Cosmos icon for programs without one, Cosmos in the
    bottle-update window;
  - `0032`: Dock always uses `share/wine/cosmos/exeIcon.icns` first so Cosmo corner alpha is kept (PE icons via
    DrawIconEx were flattening to a sharp black square).
- Credit: CodeWeavers, Highball (gauthierpiarrette) and everyone named in README.md's "Provenance and credit".

- Look: `cosmos-theme/make-theme.py` recolours Wine's light visual style (every dialog, button, progress bar and scroll
  bar Wine draws itself) to Cosmopolitan's black, greys and off-white, and names it Cosmos. The build runs it after the
  patches, then `cosmos-theme/install-icons.sh` puts the Cosmos icon in place of every Wine-branded `.ico` (IDI_WINLOGO,
  winecfg, winefile, winetest) and ships `exeIcon.icns` for the Dock fallback; `cosmos-theme/convert` lets Wine's
  `tools/buildimage` use ImageMagick 7.

- Host libraries: `cosmos-tools/bundle-hostlibs.py` copies every library Wine opens by name (the `SONAME_*` in the
  build's `config.h`, plus SDL3 for sdl2-compat) and everything they link to into `engine/lib/wine/x86_64-unix`,
  rewrites their links to `@loader_path` and signs them. Highball's Intel tarballs ship none and rely on the app.

Keeping up with Highball: merge `upstream/main` into `cosmos`, rebuild, bump the revision.
