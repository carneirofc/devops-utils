#!/usr/bin/env bash
# Build the Arch package from packaging/arch/PKGBUILD and print the packages' paths.
# makepkg works on a copy of packaging/arch in ~/.cache/arch-build/<repository> and
# clones this checkout's committed HEAD; the checkout itself is left untouched.
#
#   scripts/package.sh               build (an unchanged commit is not built again)
#   scripts/package.sh -si           also install missing dependencies, then the package
#   scripts/package.sh -f            build again
#   scripts/package.sh --deps        the PKGBUILD's dependencies of every kind, one per line
#   PKG_SOURCE= scripts/package.sh   build the PKGBUILD's own default source instead
#   ARCH_BUILD_DIR=DIR               where makepkg works
source "$(dirname -- "${BASH_SOURCE[0]}")/lib.sh"
help_option "$@"
if [[ ${1:-} == --deps ]]; then
  pkgbuild_packages
  exit 0
fi
package_arch "$@"
