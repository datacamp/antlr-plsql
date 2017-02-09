git config user.name "Sqlwhat Bot"
git config user.email "michael@datacamp.com"
git config credential.helper "store --file=.git/credentials"
echo "https://${GH_TOKEN}:@github.com" > .git/credentials

# It took ages to figures this one out:
# Travis CI sets up the origin to only fetch the specific branch, e.g.:
#     fetch = +refs/heads/develop:refs/remotes/origin/develop
# Since we want to deploy to prebuilt/module also, we need to change that:
#     fetch = +refs/heads/*:refs/remotes/origin/*
# We can change the fetch setting by removing and adding the origin again:
git remote remove origin
git remote add origin https://github.com/datacamp/sqlwhat.git

# Avoid detached head...
git checkout $TRAVIS_BRANCH
