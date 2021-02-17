#Step 1: Save the current git commit message
git rev-parse HEAD >> /var/www/signbank/live/writable/commit_hash_before_latest_deploy

#Step 2: Update the repo 
git fetch #Change to pull when done

#Step 3: Backup the databse
cp /var/www/signbank/live/writable/database/signbank.db /var/www/signbank/live/writable/database/manual_backups/before_latest_deploy.db 
chmod a-w /var/www/signbank/live/writable/database/manual_backups/before_latest_deploy.db
