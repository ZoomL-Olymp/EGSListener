FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN mkdir -p /app/data

RUN chown -R nobody:nogroup /app/data

RUN useradd -ms /bin/bash appuser
USER appuser

WORKDIR /home/appuser/app

CMD ["python", "epic_games_scraper.py"]