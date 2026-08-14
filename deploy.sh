ROOT=/var/www/

#Step 0: To be sure, start the env
#source "$ROOT"sb-env/bin/activate

#Step 1: Save the current git commit message
git rev-parse HEAD >> "$ROOT"writable/commit_hash_before_latest_deploy

#Step 2: Update the repo 
STASHED=$(git stash push -u -m "pre-deploy autostash")

git fetch
if ! git merge; then
    echo "Merge failed — not popping stash. Resolve manually, then run: git stash pop"
    exit 1
fi

if [[ "$STASHED" != *"No local changes to save"* ]]; then
    git stash pop
fi

#Step 3: Backup the databse
cp "$ROOT"writable/database/signbank.db "$ROOT"writable/database/manual_backups/before_latest_deploy.db 
chmod a-w "$ROOT"writable/database/manual_backups/before_latest_deploy.db

#Step 4: install any new requirements
pip install -r "$ROOT"repo/requirements.txt

#Step 5: fix all permissions
chmod -R g=rw "$ROOT"signbank/live/repo

#Step 6: migrate the database
python "$ROOT"repo/bin/develop.py migrate

#Step 7: create a new test database that includes migrations
#python "$ROOT"repo/bin/develop.py create_test_db

#Step 8: Run all unit tests
#python "$ROOT"repo/bin/develop.py test --keepdb
