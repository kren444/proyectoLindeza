"""
Local configuration for the proyectoLindeza app.

Edit these values to point to your MySQL server. If you prefer environment
variables, they still take precedence over these values when set.

WARNING: This file may contain sensitive credentials. Do not commit real
passwords to public repositories.
"""

# Default MySQL connection (pointing to the isladigital server shown in phpMyAdmin)
MYSQL_HOST = 'isladigital.xyz'
MYSQL_PORT = 3311
MYSQL_USER = 'karen'
MYSQL_PASSWORD = 'karenc'  # your provided password
MYSQL_DB = 'f58_karen'

# You can override these by setting the environment variables:
# MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

# Email / SMTP settings (optional) - override via environment variables if needed
# Example for Gmail/SMTP: set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS
SMTP_HOST = ''
SMTP_PORT = 587
SMTP_USER = ''
SMTP_PASSWORD = ''
SMTP_USE_TLS = True
# Sender and admin recipient
EMAIL_FROM = 'no-reply@localhost'
ADMIN_EMAIL = 'admin@localhost'
