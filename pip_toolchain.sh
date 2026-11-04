#!/bin/bash
# pip_toolchain.sh -- release the eventdispatch pip package.
#
# The version lives in two files, pyproject.toml and setup.py;
# they must agree. This script bumps both, builds, checks the
# artifacts with twine, and uploads.
#
# Usage:
#   ./pip_toolchain.sh [--bump patch|minor|major | --version X.Y.Z]
#                      [--target pypi|testpypi] [--dry-run]
#                      [--commit] [--tag] [--allow-dirty] [--yes]
#
# Defaults: --bump patch, --target testpypi (a deliberate
# upload still asks for confirmation unless --yes).
#
# A real release:
#   ./pip_toolchain.sh --bump patch --target pypi --commit --tag

set -euo pipefail
cd "$(dirname "$0")"

BUMP=patch
VERSION=""
TARGET=testpypi
DRY_RUN=0
DO_COMMIT=0
DO_TAG=0
ALLOW_DIRTY=0
ASSUME_YES=0

usage() {
    sed -n '2,20p' "$0"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bump)       BUMP="$2"; shift 2 ;;
        --version)    VERSION="$2"; shift 2 ;;
        --target)     TARGET="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=1; shift ;;
        --commit)     DO_COMMIT=1; shift ;;
        --tag)        DO_TAG=1; shift ;;
        --allow-dirty) ALLOW_DIRTY=1; shift ;;
        --yes)        ASSUME_YES=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

die() { echo "error: $*" >&2; exit 1; }

# ---- validate options -------------------------------------------------
case "$BUMP" in major|minor|patch) ;; *) die "--bump must be major|minor|patch" ;; esac
case "$TARGET" in pypi|testpypi) ;; *) die "--target must be pypi|testpypi" ;; esac
if [[ -n "$VERSION" && ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    die "--version must be X.Y.Z, got: $VERSION"
fi

# ---- preflight: tools --------------------------------------------------
python3 -m build --version >/dev/null 2>&1 || die "pypa/build missing (pip install build)"
python3 -m twine --version >/dev/null 2>&1 || die "twine missing (pip install twine)"

# ---- preflight: clean tree (the bump itself is the only dirt allowed) --
if [[ $ALLOW_DIRTY -eq 0 ]] && git rev-parse --git-dir >/dev/null 2>&1; then
    [[ -z "$(git status --porcelain)" ]] || \
        die "working tree is dirty -- commit/stash first, or pass --allow-dirty"
fi

# ---- current version: the two files must agree -------------------------
version_in() { # file -> X.Y.Z
    case "$1" in
        pyproject.toml) sed -n -E 's/^version = "([0-9]+\.[0-9]+\.[0-9]+)"/\1/p' "$1" ;;
        setup.py)       sed -n -E "s/.*version='([0-9]+\.[0-9]+\.[0-9]+)'.*/\\1/p" "$1" ;;
    esac
}
CUR_PY=$(version_in pyproject.toml)
CUR_SETUP=$(version_in setup.py)
[[ -n "$CUR_PY" ]] || die "no version found in pyproject.toml"
[[ "$CUR_PY" == "$CUR_SETUP" ]] || \
    die "version drift: pyproject.toml=$CUR_PY setup.py=$CUR_SETUP -- fix by hand first"

# ---- compute the new version -------------------------------------------
if [[ -n "$VERSION" ]]; then
    NEW="$VERSION"
else
    IFS='.' read -r MAJ MIN PAT <<< "$CUR_PY"
    case "$BUMP" in
        major) MAJ=$((MAJ + 1)); MIN=0; PAT=0 ;;
        minor) MIN=$((MIN + 1)); PAT=0 ;;
        patch) PAT=$((PAT + 1)) ;;
    esac
    NEW="$MAJ.$MIN.$PAT"
fi
[[ "$NEW" != "$CUR_PY" ]] || die "new version equals current version ($CUR_PY)"
echo "release: eventdispatch $CUR_PY -> $NEW (target: $TARGET)"

# ---- bump both files, then verify they agree ---------------------------
sed -i -E "s/^version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NEW\"/" pyproject.toml
sed -i -E "s/version='[0-9]+\.[0-9]+\.[0-9]+'/version='$NEW'/" setup.py
[[ "$(version_in pyproject.toml)" == "$NEW" && "$(version_in setup.py)" == "$NEW" ]] || \
    die "bump failed to land in both files"

if [[ $DO_COMMIT -eq 1 ]]; then
    git add pyproject.toml setup.py
    git commit -m "release v$NEW" >/dev/null
    echo "committed: release v$NEW"
fi

# ---- build + check ------------------------------------------------------
rm -rf dist/ build/ ./*.egg-info
python3 -m build
python3 -m twine check dist/*

if [[ $DRY_RUN -eq 1 ]]; then
    echo "dry run: built and checked $NEW, not uploading."
    echo "artifacts in dist/ -- version files left bumped at $NEW."
    exit 0
fi

# ---- upload --------------------------------------------------------------
if [[ $ASSUME_YES -eq 0 ]]; then
    read -r -p "upload eventdispatch $NEW to $TARGET? [y/N] " REPLY
    [[ "$REPLY" =~ ^[Yy]$ ]] || { echo "aborted -- nothing uploaded."; exit 1; }
fi
if [[ "$TARGET" == "testpypi" ]]; then
    python3 -m twine upload --repository testpypi dist/*
else
    python3 -m twine upload dist/*
fi

# ---- tag (only after a successful upload) --------------------------------
if [[ $DO_TAG -eq 1 ]]; then
    git tag "v$NEW"
    echo "tagged v$NEW (push it with: git push origin v$NEW)"
fi

echo "done: eventdispatch $NEW on $TARGET"
if [[ $DO_COMMIT -eq 0 ]]; then
    echo "note: pyproject.toml + setup.py are bumped but uncommitted."
fi
