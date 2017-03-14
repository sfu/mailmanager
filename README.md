Mail server Management Utility

Installation:

 1. Install on a web server that has mod_auth_cas, or some other way to protect this script from access
 2. Copy quarantine.cgi and pages subdir to a directory named 'mail'  on the web server that's configured as executable - e.g. /var/www/cgi-bin/mail. It should appear in the web hierarchy at /mail (if not, edit path in quarantine.js)
 3. Copy resources directory to 'mailmanager' sub dir in HTML root - e.g /var/www/html/mailmanager
 4. Set up a .htaccess/.htpasswd file in cgi-bin to protect access to the script or secure with directives in Apache config

Usage:

Browse to <server>/cgi-bin-path/quarantine.cgi

