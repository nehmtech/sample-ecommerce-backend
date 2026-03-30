FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python", "manage.py", "python manage.py migrate && gunicorn project.wsgi:application --bind 0.0.0.0:8000"]