release: python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py create_owner --noinput
web: gunicorn mediaexpand.wsgi --log-file -
