#!/bin/bash
set -euo pipefail

# =============================================================================
# copy.sh — Bootstrap a new project from the cosmo-template
# =============================================================================
#
# Usage:
#   ./copy.sh <new_project_name> <destination_directory>
#
# Example:
#   ./copy.sh my_awesome_app /home/user/projects/my-awesome-app
#
# The project name must be a valid Python identifier (lowercase, underscores).
# A hyphenated variant is derived automatically for Docker service names.

if [ $# -ne 2 ]; then
    echo "Usage: $0 <new_project_name> <destination_directory>"
    echo "Example: $0 my_awesome_app /home/user/projects/my-awesome-app"
    exit 1
fi

NEW_NAME="$1"
DEST="$2"

# Validate project name is a valid Python identifier
if ! echo "$NEW_NAME" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "Error: project name must be a valid Python identifier (lowercase, underscores only)."
    echo "Got: $NEW_NAME"
    exit 1
fi

if [ -e "$DEST" ]; then
    echo "Error: destination already exists: $DEST"
    exit 1
fi

# Derive name variants
NEW_APP="${NEW_NAME}_app"
NEW_UPPER=$(echo "$NEW_NAME" | tr '[:lower:]' '[:upper:]')
NEW_HYPHEN=$(echo "$NEW_NAME" | tr '_' '-')

echo "Creating new project:"
echo "  Name:        $NEW_NAME"
echo "  App module:  $NEW_APP"
echo "  Upper:       $NEW_UPPER"
echo "  Docker:      $NEW_HYPHEN"
echo "  Destination: $DEST"
echo

# Step 1: Copy files, excluding what we don't want
echo "Copying files..."
rsync -a --exclude='.git/' \
         --exclude='copy.sh' \
         --exclude='cosmo_template_plan.md' \
         --exclude='SOUL.md' \
         --exclude='USER.md' \
         --exclude='.claude/' \
         --exclude='__pycache__/' \
         --exclude='.pytest_cache/' \
         --exclude='.ruff_cache/' \
         --exclude='*.pyc' \
         --exclude='.venv/' \
         --exclude='.env' \
         --exclude='.docker_build_hash' \
         --exclude='cosmo_template_app/work_dir/*' \
         --exclude='celerybeat-schedule*' \
         --exclude='test/artifacts/' \
         --exclude='uv.lock' \
         ./ "$DEST/"

# Step 2: Rename directories
echo "Renaming directories..."
if [ -d "$DEST/cosmo_template_app" ]; then
    mv "$DEST/cosmo_template_app" "$DEST/$NEW_APP"
fi

# Step 3: Global rename in file contents
echo "Renaming references in files..."

# Order matters: longer strings first to avoid partial replacements
find "$DEST" -type f -not -path '*/\.git/*' -not -name '*.png' -not -name '*.jpg' \
    -not -name '*.ico' -not -name '*.svg' -not -name '*.woff*' -not -name '*.ttf' \
    -print0 | xargs -0 sed -i \
    -e "s/cosmo_template_app/${NEW_APP}/g" \
    -e "s/cosmo_template/${NEW_NAME}/g" \
    -e "s/COSMO_TEMPLATE/${NEW_UPPER}/g" \
    -e "s/cosmo-template/${NEW_HYPHEN}/g"

# Step 4: Print branded files to customize
echo
echo "Done! New project created at: $DEST"
echo
echo "Files to customize with your branding:"
echo "  $NEW_APP/static/start_banner.png  — Main banner image"
echo "  $NEW_APP/static/icon.svg          — App icon (navbar, favicon)"
echo "  $NEW_APP/static/icon_white.svg    — White variant of icon"
echo "  $NEW_APP/static/small_icon.png    — Small icon variant"
echo "  $NEW_APP/assets/favicon.ico       — Browser favicon"
echo "  $NEW_APP/pages/home.py            — Home page welcome text"
echo "  README.md                         — Project description"
echo
echo "Next steps:"
echo "  cd $DEST"
echo "  git init"
echo "  uv lock"
echo "  ./dev_up.sh"
