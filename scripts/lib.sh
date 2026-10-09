# Shared by the scripts next to it. The same file lives in scraper, fzonetrack, seanime
# and readest: edit it in one repository and copy it to the others. What differs per
# repository is in scripts/project.sh, which this file sources.
#
# The contract every repository follows (each script answers -h/--help):
#
#   scripts/setup.sh   [--deps]          prepare the checkout for dev/build; --deps prints
#                                        the pacman packages that needs, one per line
#   scripts/dev.sh     [args...]         run from source, in development mode
#   scripts/build.sh   [args...]         build the release artifacts; prints their paths
#   scripts/install.sh [--uninstall]     install this checkout for the current user (no
#                                        sudo); run it again to update
#   scripts/package.sh [--deps] [makepkg args...]
#                                        build packaging/arch/PKGBUILD from this checkout's
#                                        committed HEAD; prints the package paths
#
# For automation (Ansible, CI): every script runs from any directory, is safe to run
# again, never prompts unless stdin is a terminal (and CI is unset), logs on stderr and
# prints only results (paths) on stdout. Exit codes: 0 done, 1 failed, 2 bad usage,
# 3 missing system packages (the message names the pacman command).

# shellcheck shell=bash
SCRIPTS_LIB_VERSION=1
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

log() { printf '==> %s\n' "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
# die MESSAGE [EXIT_CODE]
die() {
  printf 'error: %s\n' "$1" >&2
  exit "${2:-1}"
}

# The calling script's header comment, without the leading '#'.
usage() { sed -n '2,/^[^#]/{/^#/s/^# \{0,1\}//p}' "$0"; }

# Answer -h/--help for the calling script: `help_option "$@"`.
help_option() {
  case ${1:-} in -h | --help) usage; exit 0 ;; esac
}

# True when someone can answer a prompt.
interactive() { [[ -t 0 && -z ${CI:-} ]]; }

# The packages given, without version constraints, one per line, sorted.
print_packages() {
  local package
  for package in "$@"; do printf '%s\n' "${package%%[<>=]*}"; done | sort -u
}

# Stop (exit 3) with the pacman command to run when one of the packages given (version
# constraints and provides allowed, e.g. 'python>=3.14' or 'cargo') is not installed.
require_packages() {
  local missing
  missing=$(pacman -T "$@" || true)
  [[ -z $missing ]] && return 0
  # shellcheck disable=SC2086 # one package per word
  die "missing system packages: sudo pacman -S --needed $(print_packages $missing | tr '\n' ' ')" 3
}

# Stop (exit 3) unless the command is on PATH: require_command uv [pacman-package].
require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required: sudo pacman -S --needed ${2:-$1}" 3
}

# True when TARGET is missing or older than one of the SOURCES: `outdated TARGET SOURCE...`
# (e.g. installed packages against their lockfile, to set the checkout up again).
outdated() {
  local target=$1 source
  [[ -e $target ]] || return 0
  for source in "${@:2}"; do [[ $source -nt $target ]] && return 0; done
  return 1
}

# Print the paths given that exist, one per line (the results a script reports).
print_existing() {
  local path
  for path in "$@"; do [[ -e $path ]] && printf '%s\n' "$path"; done
  return 0
}

# --- Arch packaging (scripts/package.sh) --------------------------------------------

ARCH_RECIPE=$ROOT/packaging/arch

# The PKGBUILD's depends, makedepends and checkdepends, one per line.
pkgbuild_packages() {
  (
    set +eu
    CARCH=$(uname -m)
    # shellcheck disable=SC1091
    source "$ARCH_RECIPE/PKGBUILD" >/dev/null 2>&1
    print_packages "${depends[@]}" "${makedepends[@]}" "${checkdepends[@]}"
  )
}

# Build the PKGBUILD with makepkg (extra arguments go to makepkg, e.g. -s, -i, -f) and
# print the packages it made.
#
# makepkg runs on a copy of packaging/arch in $ARCH_BUILD_DIR (default
# ~/.cache/arch-build/<repository>), so the pkgver it writes back and its src/, pkg/ and
# clones stay out of the checkout, and later builds reuse the clone. The PKGBUILD clones
# $PKG_SOURCE, which defaults to this checkout (its committed HEAD); set PKG_SOURCE=
# (empty) to build the PKGBUILD's own default source instead.
package_arch() {
  [[ -f $ARCH_RECIPE/PKGBUILD ]] || die "no packaging/arch/PKGBUILD in $ROOT"
  require_command makepkg pacman
  local stage=${ARCH_BUILD_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/arch-build/${ROOT##*/}}
  local source=${PKG_SOURCE-file://$ROOT}
  if [[ $source == "file://$ROOT" && -n $(git -C "$ROOT" status --porcelain) ]]; then
    warn "uncommitted changes are not packaged: makepkg builds the committed HEAD"
  fi

  log "packaging/arch -> $stage"
  mkdir -p "$stage"
  # The recipe's tracked and new files, never the build leftovers beside them.
  git -C "$ROOT" ls-files -z --cached --others --exclude-standard -- packaging/arch |
    (cd "$ROOT" && tar --null --files-from=- -cf -) |
    tar -C "$stage" --strip-components=2 -xf -

  local flags=(--noprogressbar)
  interactive || flags+=(--noconfirm)
  local status=0
  (cd "$stage" && PKG_SOURCE=$source makepkg "${flags[@]}" "$@" >&2) || status=$?
  # 13: this version is already built, which is what was asked for.
  case $status in
    0) ;;
    13) log "already built" ;;
    *) die "makepkg failed (exit $status)" ;;
  esac
  local packages
  mapfile -t packages < <(cd "$stage" && PKG_SOURCE=$source makepkg --packagelist 2>/dev/null)
  print_existing "${packages[@]}"
}

# shellcheck source=project.sh
source "$ROOT/scripts/project.sh"
