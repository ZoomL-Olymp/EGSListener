FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y wget unzip
RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
RUN unzip chromedriver_linux64.zip -d /usr/local/bin
RUN chmod +x /usr/local/bin/chromedriver

RUN mkdir -p /app/data
RUN chown -R nobody:nogroup /app/data

RUN useradd -ms /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

COPY . /home/appuser/app/
RUN rm -rf /home/appuser/.cache/selenium /home/appuser/.config/google-chrome

CMD ["python", "epic_games_scraper.py"]