Mail server Management Utility

Installation:

 1. Install on a web server that has mod_auth_cas, or some other way to protect this script from access
 2. Copy quarantine.cgi and pages subdir to a directory on the web server that's configured as executable - e.g. /var/www/cgi-bin
 3. Copy resources directory to 'mail' sub dir in HTML root - e.g /var/www/html/mail
 4. Set up a .htaccess/.htpasswd file in cgi-bin to protect access to the script or secure with directives in Apache config

Usage:

Browse to <server>/cgi-bin-path/quarantine.cgi

