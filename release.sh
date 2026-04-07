#!/usr/bin/env bash
set -Eeuo pipefail

# release.sh
#
# Usage:
#   ./release.sh 1.2.3
#   ./release.sh v1.2.3
#
# Behavior:
#   1. Verifies we're inside a git repo
#   2. Verifies working tree is clean
#   3. Checks whether the tag already exists locally or on either remote
#   4. Checks whether debian/changelog contains the release version
#   5. If all checks pass, performs:
#        git push github
#        git push origin
#        git tag <version>
#        git push github <version>
#        git push origin <version>

die() {
    echo "ERROR: $*" >&2
    exit 1
}

info() {
    echo "==> $*"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

normalize_version() {
    local raw="$1"
    # Strip one leading "v" for changelog matching, because Debian changelog
    # versions are usually like 1.2.3, not v1.2.3.
    printf '%s\n' "${raw#v}"
}

tag_exists_local() {
    local tag="$1"
    git rev-parse -q --verify "refs/tags/$tag" >/dev/null 2>&1
}

tag_exists_remote() {
    local remote="$1"
    local tag="$2"
    git ls-remote --exit-code --tags "$remote" "refs/tags/$tag" >/dev/null 2>&1
}

version_in_changelog() {
    local version="$1"
    # Debian changelog entries look like:
    # package-name (1.2.3) unstable; urgency=medium
    grep -Eq "^[[:alnum:].+:-]+[[:space:]]+\(${version//./\\.}\)[[:space:]]" debian/changelog
}

main() {
    require_cmd git
    require_cmd grep

    [[ $# -eq 1 ]] || die "Usage: $0 <version|tag>"

    local tag="$1"
    local changelog_version
    changelog_version="$(normalize_version "$tag")"

    git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
        || die "This is not a git repository."

    [[ -f debian/changelog ]] || die "debian/changelog not found."

    # Clean tree check: fail if there are staged, unstaged, or untracked changes
    if [[ -n "$(git status --porcelain)" ]]; then
        die "Working tree is not clean. Commit or stash your changes first."
    fi

    # Check remotes exist
    git remote get-url github >/dev/null 2>&1 || die "Remote 'github' does not exist."
    git remote get-url origin >/dev/null 2>&1 || die "Remote 'origin' does not exist."

    info "Checking whether tag '$tag' already exists..."
    if tag_exists_local "$tag"; then
        die "Tag '$tag' already exists locally."
    fi

    if tag_exists_remote github "$tag"; then
        die "Tag '$tag' already exists on remote 'github'."
    fi

    if tag_exists_remote origin "$tag"; then
        die "Tag '$tag' already exists on remote 'origin'."
    fi

    info "Checking debian/changelog for version '$changelog_version'..."
    if ! version_in_changelog "$changelog_version"; then
        die "Version '$changelog_version' was not found in debian/changelog.
Update debian/changelog first, then re-run this release script."
    fi

    info "All checks passed."
    info "Pushing branches to github and origin..."
    git push github
    git push origin

    info "Creating tag '$tag'..."
    git tag "$tag"

    info "Pushing tag '$tag' to github..."
    git push github "$tag"

    info "Pushing tag '$tag' to origin..."
    git push origin "$tag"

    info "Release flow completed successfully."
}

main "$@"