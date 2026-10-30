#!/usr/bin/env python3
"""Bundles the host libraries a Cosmos engine opens by name into the engine itself.

Usage: bundle-hostlibs.py <engine dir> <wine build dir> [--search DIR ...]

Wine's Unix side dlopen()s FreeType, GnuTLS, SDL, MoltenVK and others by the names configure recorded (SONAME_* in the
build's include/config.h). macOS finds a library opened by bare name next to the module that opens it, so each one, and
everything it links to outside macOS itself, is copied into <engine>/lib/wine/x86_64-unix. References between the copies
are rewritten to @loader_path/<name>, so nothing points back into Homebrew, and each copy is signed ad hoc (rewriting
invalidates the signature, and macOS refuses an invalid one).

Libraries are looked up in the --search directories first, then /usr/local/lib and /usr/local/opt/*/lib (Homebrew on Intel).
SDL3 is added too, also as libSDL3.dylib: sdl2-compat, Homebrew's SDL2, opens it by that name at run time.
"""
import glob, os, re, shutil, subprocess, sys

SYSTEM = ("/usr/lib/", "/System/")
EXTRA = ["libSDL3.0.dylib"]
# Other names a bundled library is opened by. sdl2-compat dlopen()s "libSDL3.dylib" (@loader_path first): without that
# name next to it, Wine's controller service (winebus) crashed at start.
ALIASES = {"libSDL3.dylib": "libSDL3.0.dylib"}
# Wine uses these when present and works without them (ODBC drivers): not bundled, not an error.
OPTIONAL = {"libodbc.dylib", "libodbc.2.dylib"}


def otool(args, path):
    return subprocess.run(["otool", "-arch", "x86_64", *args, path], capture_output=True, text=True, check=True).stdout


def deps(path):
    """Install names this library links to (not its own id)."""
    lines = [l for l in otool(["-L"], path).splitlines() if l.startswith(("\t", " "))]
    own = [l.strip() for l in otool(["-D"], path).splitlines() if not l.endswith(":")]
    out = [l.strip().split(" (")[0] for l in lines]
    return [d for d in out if d and d not in own]


def rpaths(path):
    text, out = otool(["-l"], path), []
    for m in re.finditer(r"cmd LC_RPATH\n\s+cmdsize \d+\n\s+path (\S+)", text):
        out.append(m.group(1))
    return out


def find(name, search, origin=None):
    """Resolves an install name (absolute, @rpath/, @loader_path/ or bare) to a file."""
    leaf = os.path.basename(name)
    if name.startswith("/") and os.path.exists(name):
        return os.path.realpath(name)
    cands = []
    if origin:
        here = os.path.dirname(origin)
        if name.startswith("@loader_path/"):
            cands.append(os.path.join(here, name[len("@loader_path/"):]))
        for rp in rpaths(origin):
            cands.append(os.path.join(rp.replace("@loader_path", here), leaf))
    cands += [os.path.join(d, leaf) for d in search + ["/usr/local/lib"]]
    cands += glob.glob("/usr/local/opt/*/lib/" + leaf)
    for c in cands:
        if os.path.exists(c):
            return os.path.realpath(c)
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    engine, build = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    search = [os.path.abspath(sys.argv[i + 1]) for i, a in enumerate(sys.argv) if a == "--search"]
    dest = os.path.join(engine, "lib", "wine", "x86_64-unix")
    config = open(os.path.join(build, "include", "config.h"), encoding="utf-8").read()
    roots = sorted((set(re.findall(r'#define SONAME_\w+ "([^"]+\.dylib)"', config)) | set(EXTRA)) - OPTIONAL)
    print("bundle: wanted by name:", " ".join(roots))

    copied, missing, queue = {}, [], [(r, None) for r in roots]
    while queue:
        name, origin = queue.pop(0)
        leaf = os.path.basename(name)
        if leaf in copied:
            continue
        src = find(name, search, origin)
        if not src:
            (missing.append(leaf) if origin is None else missing.append(f"{leaf} (needed by {os.path.basename(origin)})"))
            continue
        out = os.path.join(dest, leaf)
        shutil.copy2(src, out)
        os.chmod(out, 0o755)
        archs = subprocess.run(["lipo", "-archs", out], capture_output=True, text=True).stdout.split()
        if len(archs) > 1:  # universal: keep the Intel slice only (the engine's Unix side is x86_64)
            subprocess.run(["lipo", out, "-thin", "x86_64", "-output", out], check=True, capture_output=True)
        copied[leaf] = src
        for d in deps(src):
            if not d.startswith(SYSTEM):
                queue.append((d, src))

    for leaf in copied:
        out = os.path.join(dest, leaf)
        cmd = ["install_name_tool", "-id", "@loader_path/" + leaf]
        for d in deps(out):
            if not d.startswith(SYSTEM) and os.path.basename(d) in copied:
                cmd += ["-change", d, "@loader_path/" + os.path.basename(d)]
        subprocess.run(cmd + [out], check=True, capture_output=True)
        for rp in rpaths(out):
            subprocess.run(["install_name_tool", "-delete_rpath", rp, out], capture_output=True)
        subprocess.run(["codesign", "--force", "-s", "-", out], check=True, capture_output=True)

    for alias, target in ALIASES.items():
        if target in copied:
            link = os.path.join(dest, alias)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)

    # Every copy must now load with nothing outside the engine and macOS.
    bad = []
    for leaf in copied:
        for d in deps(os.path.join(dest, leaf)):
            if not d.startswith(SYSTEM) and not (d.startswith("@loader_path/") and os.path.basename(d) in copied):
                bad.append(f"{leaf} -> {d}")
    print(f"bundle: {len(copied)} libraries into {dest}")
    if missing:
        print("bundle: NOT FOUND:", ", ".join(missing))
    if bad:
        print("bundle: UNRESOLVED:", ", ".join(bad))
    sys.exit(1 if missing or bad else 0)


if __name__ == "__main__":
    main()
