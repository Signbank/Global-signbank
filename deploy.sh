ROOT=/var/www/

#Step 0: To be sure, start the env
#source "$ROOT"sb-env/bin/activate

#Step 1: Save the current git commit message
git rev-parse HEAD >> "$ROOT"writable/commit_hash_before_latest_deploy

#Step 2: Update the repo 
git fetch
git merge

#Step 3: Backup the databse
cp "$ROOT"writable/database/signbank.db "$ROOT"writable/database/manual_backups/before_latest_deploy.db 
chmod a-w "$ROOT"writable/database/manual_backups/before_latest_deploy.db

#Step 4: install any new requirements
pip install -r "$ROOT"repo/requirements.txt

#Step 5: fix all permissions
mod -R g=rw "$ROOT"signbank/live/repo
setfacl -R -m user:wapsignbank:rx "$ROOT"repo/

#Step 6: migrate the database
python "$ROOT"repo/bin/develop.py migrate

#Step 7: create a new test database that includes migrations
python "$ROOT"repo/bin/develop.py create_test_db

#Step 8: Run all unit tests
python "$ROOT"repo/bin/develop.py test -k
