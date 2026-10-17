#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
archive_path=$(mktemp "${TMPDIR:-/tmp}/vfs-shell-errors.XXXXXX")
trap 'rm -f "$archive_path"' EXIT

cd "$repo_root"
python3 "$script_dir/create_demo_vfs.py" \
    --profile nested --output "$archive_path"
python3 -m src.cli \
    --vfs "$archive_path" --script "$script_dir/demo-errors.commands"
