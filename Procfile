web: gunicorn andrea_project.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --log-file -
release: python manage.py collectstatic --noinput

