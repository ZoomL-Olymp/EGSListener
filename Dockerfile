FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
# Установка зависимостей, включая curl и unzip для скачивания ChromeDriver
RUN apt-get update && \
    apt-get install -y wget gnupg2 ca-certificates curl unzip && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable

ARG CHROME_VERSION=113.0.5672.63

# Установка ChromeDriver
RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/bin/ && \
    chmod +x /usr/bin/chromedriver

    RUN rm /tmp/chromedriver.zip

RUN mkdir -p /app/data
RUN chown -R nobody:nogroup /app/data

RUN useradd -ms /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

COPY . /home/appuser/app/

CMD ["python", "epic_games_scraper.py"]