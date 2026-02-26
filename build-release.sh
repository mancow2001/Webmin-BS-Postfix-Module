#!/bin/bash
# build-release.sh
# Build a Webmin module package (.wbm.gz) for release

set -e

# Configuration
MODULE_NAME="brightspeed-postfix"
VERSION="${1:-$(grep '^version=' module.info | cut -d= -f2)}"

if [ -z "$VERSION" ]; then
    echo "Error: Version not specified and not found in module.info"
    echo "Usage: $0 [version]"
    exit 1
fi

PACKAGE="${MODULE_NAME}-${VERSION}.wbm.gz"
BUILD_DIR="/tmp/${MODULE_NAME}-build-$$"
MODULE_DIR="${BUILD_DIR}/${MODULE_NAME}"

echo "Building ${MODULE_NAME} version ${VERSION}"
echo "----------------------------------------"

# Create build directory
mkdir -p "${MODULE_DIR}"

# Copy files to build directory, excluding non-module files
echo "Copying files..."
rsync -av \
    --exclude='.git' \
    --exclude='.github' \
    --exclude='.claude' \
    --exclude='.DS_Store' \
    --exclude='.gitignore' \
    --exclude='.gitattributes' \
    --exclude='*.tar.gz' \
    --exclude='*.wbm.gz' \
    --exclude='build-release.sh' \
    --exclude='CLAUDE.md' \
    --exclude='README.md' \
    --exclude='postfix_config/' \
    --exclude='log_sample/' \
    ./ "${MODULE_DIR}/"

# Update version in module.info
echo "Updating version to ${VERSION}..."
sed -i.bak "s/^version=.*/version=${VERSION}/" "${MODULE_DIR}/module.info"
rm -f "${MODULE_DIR}/module.info.bak"

# Create .wbm.gz package
echo "Creating package..."
cd "${BUILD_DIR}"
tar -czf "${PACKAGE}" "${MODULE_NAME}"

# Move package to current directory
mv "${PACKAGE}" "${OLDPWD}/"

# Cleanup
cd "${OLDPWD}"
rm -rf "${BUILD_DIR}"

echo "----------------------------------------"
echo "Success! Created: ${PACKAGE}"
echo ""
echo "To install in Webmin:"
echo "  1. Go to Webmin -> Webmin Configuration -> Webmin Modules"
echo "  2. Click 'From uploaded file'"
echo "  3. Upload ${PACKAGE}"
echo ""
echo "File size: $(du -h ${PACKAGE} | cut -f1)"
