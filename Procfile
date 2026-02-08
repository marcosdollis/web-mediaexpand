release: python manage.py migrate --noinput && python manage.py create_owner && python manage.py collectstatic --noinput
web: gunicorn mediaexpand.wsgi --log-file -
