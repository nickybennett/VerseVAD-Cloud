#!/bin/bash

set -u

if [ "$(uname -s)" != "Darwin" ]; then
  echo "This helper is for macOS. On Windows, use update_versemap_reference.bat."
  exit 1
fi

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
UV_EXECUTABLE="$PROJECT_ROOT/.tools/uv/uv"
RUNTIME_DIRECTORY="$PROJECT_ROOT/.runtime"

if [ ! -x "$UV_EXECUTABLE" ]; then
  echo "VerseVAD has not been set up in this folder."
  echo "Open Terminal in this folder and run: bash setup_macos.command"
  echo
  read -r -p "Press Return to close this window." _
  exit 1
fi

export UV_CACHE_DIR="$RUNTIME_DIRECTORY/uv-cache"
export UV_PYTHON_INSTALL_DIR="$RUNTIME_DIRECTORY/python"
export UV_NO_MODIFY_PATH=1
export UV_PYTHON_PREFERENCE=only-managed

cd "$PROJECT_ROOT"
echo "Updating the VerseMap reference corpus and analytical index..."
"$UV_EXECUTABLE" run --frozen --offline versevad-update-versemap
STATUS=$?
echo
if [ "$STATUS" -eq 0 ]; then
  echo "The reference release and analytical index are ready for review and source control."
else
  echo "The updater found a problem. Review the messages above."
fi
echo
read -r -p "Press Return to close this window." _
exit "$STATUS"
