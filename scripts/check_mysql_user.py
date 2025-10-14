"""Check MySQL connection and show user records for a given email.

Usage:
    python scripts\check_mysql_user.py valery@gmail.com

It reads MySQL connection settings from environment variables:
  MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

If not present, it prompts for them interactively.

WARNING: This prints the stored password field for debugging. Don't share it publicly.
"""
import os
import sys
import getpass
import pymysql


def get_env(name, prompt=None, secret=False):
    v = os.environ.get(name)
    if v:
        return v
    if prompt:
        if secret:
            return getpass.getpass(prompt + ': ')
        return input(prompt + ': ')
    return None


def inspect_password(pw):
    if not pw:
        return 'empty'
    if len(pw) == 32 and all(c in '0123456789abcdef' for c in pw.lower()):
        return 'md5'
    if pw.startswith('pbkdf2:') or pw.startswith('sha256') or len(pw) > 40:
        return 'werkzeug-hash'
    # fallback: if printable and short, consider plaintext
    if all(32 <= ord(c) < 127 for c in pw) and len(pw) < 40:
        return 'plaintext?'
    return 'unknown'


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts\\check_mysql_user.py email')
        sys.exit(1)
    email = sys.argv[1].strip().lower()

    host = get_env('MYSQL_HOST', 'MySQL host')
    user = get_env('MYSQL_USER', 'MySQL user')
    password = get_env('MYSQL_PASSWORD', None, secret=True)
    db = get_env('MYSQL_DB', 'MySQL database')

    if not all([host, user, password, db]):
        print('Missing DB connection info; set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB env vars or run again and answer prompts.')
        sys.exit(1)

    print(f'Connecting to {host} as {user} db={db}...')
    try:
        conn = pymysql.connect(host=host, user=user, password=password, db=db, cursorclass=pymysql.cursors.DictCursor)
    except Exception as e:
        print('Connection failed:', e)
        sys.exit(2)

    try:
        with conn.cursor() as cur:
            print('\nChecking administradores...')
            cur.execute('SELECT id,name,email,password FROM administradores WHERE LOWER(email)=%s LIMIT 1', (email,))
            admin = cur.fetchone()
            if admin:
                print('Found in administradores:')
                print(admin)
                print('password type:', inspect_password(admin.get('password')))
            else:
                print('Not found in administradores.')

            print('\nChecking usuarios...')
            cur.execute('SELECT id,name,email,password FROM usuarios WHERE LOWER(email)=%s LIMIT 1', (email,))
            user_row = cur.fetchone()
            if user_row:
                print('Found in usuarios:')
                print(user_row)
                print('password type:', inspect_password(user_row.get('password')))
            else:
                print('Not found in usuarios.')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
