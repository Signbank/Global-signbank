source /var/www/signbank/live/sb-env/bin/activate

#Step 1: Save the current git commit message
git rev-parse HEAD >> /var/www/signbank/live/writable/commit_hash_before_latest_deploy

#Step 2: Update the repo 
git fetch #Change to pull when done

#Step 3: Backup the databse
cp /var/www/signbank/live/writable/database/signbank.db /var/www/signbank/live/writable/database/manual_backups/before_latest_deploy.db 
chmod a-w /var/www/signbank/live/writable/database/manual_backups/before_latest_deploy.db

#Step 4: install any new requirements
pip install -r /var/www/signbank/live/repo/requirements.txt

#Step 5: fix all permissions

#Step 6: backup the database
python /var/www/signbank/live/repo/bin/develop.py migrate

#Step 7: Run all unit tests
python /var/www/signbank/live/repo/bin/develop.py test -k
