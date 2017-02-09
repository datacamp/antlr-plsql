if [ -n "${TRAVIS_TAG}" ]; then
    TARGET=$TRAVIS_TAG
else
    TARGET="commit ${TRAVIS_COMMIT}"
fi

# Set up a temporary folder to prepare distribution files.
TMP=~/tmp
mkdir $TMP
# Copy everything to the this folder first, then clean up.
cp -r . $TMP/
rm -rf $TMP/.git

# Specifically fetch and check out the prebuilt/module branch from origin.
git fetch origin +refs/heads/builds:refs/remotes/origin/builds
git checkout -b builds -t origin/builds
# Remove everything so we can fully replace it. Git will create the diffs.
rm -fr *
mv $TMP/* .
git add --all *
git commit -m "Prebuilt module for ${TARGET}"
git push -u origin builds
rmdir $TMP
