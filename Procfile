release: python src/manage.py migrate
web: gunicorn config.wsgi:application --chdir src --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --access-logfile - --error-logfile - --log-level debug
