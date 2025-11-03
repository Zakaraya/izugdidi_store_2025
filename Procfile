release: python src/manage.py migrate && python src/manage.py collectstatic --noinput
web: gunicorn config.wsgi:application --chdir src --bind 0.0.0.0:$PORT
