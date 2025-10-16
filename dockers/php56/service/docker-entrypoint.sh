#!/bin/sh

# Configure Nginx
mkdir /run/nginx
touch /run/nginx/nginx.pid

# Get the user
user=$(ls /home)

php-fpm & nginx &

echo "Running..."

tail -F /var/log/nginx/access.log /var/log/nginx/error.log
