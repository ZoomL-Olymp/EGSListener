# Epic Games Store Free Game Bot

This project is a Telegram bot that notifies you about free games available on the Epic Games Store. It scrapes the Epic Games Store website, saves the information to a SQLite database, and sends notifications to subscribed users when a new free game is released.

## Features

* Scrapes the Epic Games Store for the current free game.
* Stores game information (title, free until date) in a SQLite database.
* Sends Telegram notifications to subscribed users when a new free game is available.
* Uses Selenium and ChromeDriver for web scraping in a headless mode.
* Dockerized for easy deployment.
* Scheduled scraping and updates.
* Handles invalid date formats gracefully.

## Prerequisites

* Docker
* Docker Compose
* A Telegram Bot API Token (get it from [@BotFather](https://t.me/botfather))

## Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/epic-games-scraper.git
```

2. Create a `.env` file in the project root directory and add your Telegram Bot API Token:

```
BOT_TOKEN=<YOUR_BOT_TOKEN>
```

3. Build and run the Docker container:

```bash
docker-compose up -d
```

## Usage

1. Start the bot in Telegram by searching for its username or using the `/start` command.
2. Use the following commands:
    * `/start`: Start the bot and see available commands.
    * `/freegame`: Get information about the current free game.
    * `/subscribe`: Subscribe to free game notifications.
    * `/unsubscribe`: Unsubscribe from notifications.
3. You can also interact with the bot using inline buttons provided in the start message.



## Data Persistence

The bot stores scraped game data and subscriber information in a SQLite database (`free_games.db`) within the `data` directory, which is mounted as a volume in the Docker container.  This ensures data persistence across container restarts.

## Scheduling

The bot automatically scrapes the Epic Games Store and updates its database. The scraping schedule is dynamic:

* If a free game is found, the next scrape is scheduled for when the current free game offer expires.
* If scraping fails or no free game is found, the next scrape is scheduled for 10:00 UTC the next day.

## Error Handling

The bot includes extensive error handling and logging to ensure robustness:

* **Web Scraping Errors:** Handles potential issues during web scraping, such as element not found or network problems.
* **Database Errors:** Handles potential database connection or query errors.
* **Telegram API Errors:** Handles potential issues sending Telegram messages.
* **Invalid Date Format:** Gracefully handles invalid date formats returned by the Epic Games Store.

## Logging

All bot activity and errors are logged to a file named `epic_games_scraper_<timestamp>.log`.  This log file is also stored within the `data` directory.

## Future Improvements

* Add support for multiple languages.
* Implement a more sophisticated scraping logic to handle website changes.
* Add more detailed game information to notifications (e.g., genre, description).
* Implement a web interface for managing subscribers and viewing game history.


## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
