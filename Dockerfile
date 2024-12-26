FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y wget unzip

RUN google-chrome --version

RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb
RUN apt-get install -y -f

RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
RUN unzip chromedriver_linux64.zip -d /usr/bin

RUN chmod +x /usr/bin/chromedriver

RUN mkdir -p /app/data
RUN chown -R nobody:nogroup /app/data

RUN useradd -ms /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

COPY . /home/appuser/app/

CMD ["python", "epic_games_scraper.py"]