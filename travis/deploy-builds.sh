if [ -n "${TRAVIS_TAG}" ]; then
    TARGET=$TRAVIS_TAG
else
    TARGET="commit ${TRAVIS_COMMIT}"
fi
if [ "${TRAVIS_BRANCH}" = "master" ]; then
    BRANCH="builds"
else
    BRANCH="builds-dev"
fi

# Set up a temporary folder to prepare distribution files.
TMP=~/tmp
mkdir $TMP
# Copy everything to the this folder first, then clean up.
cp -r . $TMP/
rm -rf $TMP/.git

git stash --include-untracked

# Specifically fetch and check out the prebuilt/module branch from origin.
git fetch origin +refs/heads/$BRANCH:refs/remotes/origin/$BRANCH
git checkout -b $BRANCH -t origin/$BRANCH
# Remove everything so we can fully replace it. Git will create the diffs.
git rm -fr *
# move in contents from build directory
mv $TMP/* .
mv $TMP/.* .

# clean out uneccessary build and cache files
make clean

git add --all *
git commit -m "Build for ${TARGET}"
git push -u origin $BRANCH
rm -rf $TMP
