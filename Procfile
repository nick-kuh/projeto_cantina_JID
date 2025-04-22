release: python manage.py migrate && python scripts/criar_superuser.py
web: gunicorn jid_cantina.wsgi
