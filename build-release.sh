#!/bin/bash
# build-release.sh
# Build a Webmin module tarball for release

set -e

# Configuration
MODULE_NAME="brightspeed-postfix"
VERSION="${1:-$(grep '^version=' module.info | cut -d= -f2)}"

if [ -z "$VERSION" ]; then
    echo "Error: Version not specified and not found in module.info"
    echo "Usage: $0 [version]"
    exit 1
fi

TARBALL="${MODULE_NAME}-${VERSION}.tar.gz"
BUILD_DIR="/tmp/${MODULE_NAME}-build-$$"
MODULE_DIR="${BUILD_DIR}/${MODULE_NAME}"

echo "Building ${MODULE_NAME} version ${VERSION}"
echo "----------------------------------------"

# Create build directory
mkdir -p "${MODULE_DIR}"

# Copy files to build directory
echo "Copying files..."
rsync -av \
    --exclude='.git' \
    --exclude='.github' \
    --exclude='*.tar.gz' \
    --exclude='.gitignore' \
    --exclude='.gitattributes' \
    --exclude='build-release.sh' \
    ./ "${MODULE_DIR}/"

# Update version in module.info
echo "Updating version to ${VERSION}..."
sed -i.bak "s/^version=.*/version=${VERSION}/" "${MODULE_DIR}/module.info"
rm -f "${MODULE_DIR}/module.info.bak"

# Create tarball
echo "Creating tarball..."
cd "${BUILD_DIR}"
tar -czf "${TARBALL}" "${MODULE_NAME}"

# Move tarball to current directory
mv "${TARBALL}" "${OLDPWD}/"

# Cleanup
cd "${OLDPWD}"
rm -rf "${BUILD_DIR}"

echo "----------------------------------------"
echo "Success! Created: ${TARBALL}"
echo ""
echo "To install in Webmin:"
echo "  1. Go to Webmin -> Webmin Configuration -> Webmin Modules"
echo "  2. Click 'From uploaded file'"
echo "  3. Upload ${TARBALL}"
echo ""
echo "File size: $(du -h ${TARBALL} | cut -f1)"
