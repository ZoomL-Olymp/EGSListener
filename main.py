import requests
from bs4 import BeautifulSoup

def get_free_games():
    url = "https://store.epicgames.com/en-US/free-games"  # URL страницы с раздачами
    response = requests.get(url)
    response.raise_for_status()  # Проверка на ошибки HTTP

    soup = BeautifulSoup(response.content, "html.parser")

    free_games = []
    for game in soup.find_all("div", class_="css-1h2ruwl"): # Замените на актуальный класс
        title = game.find("h2").text # Замените на актуальный тег и класс
        free_games.append(title)
    return free_games


if __name__ == "__main__":
    try:
      free_games = get_free_games()
      if free_games:
          message = "\n".join(free_games)
          print(message)  # Вывод в консоль
          # Уведомление (опционально)
          notification.notify(
              title="Free Games on EGS",
              message=message,
              app_icon=None,  # Путь к иконке (опционально)
              timeout=10  # Время отображения уведомления
          )
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")