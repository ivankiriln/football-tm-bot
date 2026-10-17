import os
import threading
import time
import requests
import telebot
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY")
YOUR_CHAT_ID = (
    "ВАШ_АЙДИ_В_ТЕЛЕГРАМ"  # Можете тоже закинуть в Environment Variables или вписать сюда
)

bot = telebot.TeleBot(BOT_TOKEN)
notified_fixtures = set()

# 1. Создаем мини-сервер для того, чтобы Render видел открытый порт и не ругался
app = Flask(__name__)


@app.route("/")
def home():
  return "Football Scanner Bot is running!"


# 2. Функция сканирования матчей (ваш основной алгоритм)
def run_scanner():
  print("Бот-сканер с оптимизацией лимитов запущен...")
  while True:
    try:
      url = "https://v3.football.api-sports.io/fixtures"
      querystring = {"live": "all"}
      headers = {
          "x-rapidapi-host": "v3.football.api-sports.io",
          "x-rapidapi-key": API_FOOTBALL_KEY,
      }

      response = requests.get(url, headers=headers, params=querystring)
      data = response.json()

      if "response" in data:
        for fixture in data["response"]:
          fixture_id = fixture["fixture"]["id"]
          elapsed = fixture["fixture"]["status"]["elapsed"]
          goals_home = fixture["goals"]["home"]
          goals_away = fixture["goals"]["away"]

          if not (14 <= elapsed <= 17):
            continue
          if goals_home != 0 or goals_away != 0:
            continue

          if fixture_id in notified_fixtures:
            continue

          stat_url = "https://v3.football.api-sports.io/fixtures/statistics"
          stat_response = requests.get(
              stat_url, headers=headers, params={"fixture": fixture_id}
          )
          stat_data = stat_response.json()

          if "response" not in stat_data:
            continue

          stats = stat_data["response"]
          if len(stats) < 2:
            continue

          shots_on_target = 0
          total_shots = 0
          yellow_cards = 0

          for team_stat in stats:
            for item in team_stat.get("statistics", []):
              typ = item.get("type")
              val = item.get("value") or 0

              if typ == "Shots on Goal":
                shots_on_target += val
              elif typ == "Total Shots":
                total_shots += val
              elif typ == "Yellow Cards":
                yellow_cards += val

          if (
              5 <= total_shots <= 10
              and shots_on_target <= 1
              and yellow_cards == 0
          ):
            home_team = fixture["teams"]["home"]["name"]
            away_team = fixture["teams"]["away"]["name"]
            league = fixture["league"]["name"]

            msg = (
                f"🎯 <b>Сигнал на ТМ 2.5 (Кэф >= 2.00)</b>\n\n"
                f"🏆 <i>Лига:</i> {league}\n"
                f"⚔️ <i>Матч:</i> {home_team} - {away_team}\n"
                f"⏱ <i>Минута:</i> {elapsed}' | <i>Счет:</i> 0:0\n"
                f"📊 <i>Статистика:</i> Всего ударов: {total_shots}, "
                f"В створ: {shots_on_target}, Карточек: {yellow_cards}\n\n"
                f"💡 <i>Рекомендация:</i> Присмотреться к ТМ 2.5"
            )

            bot.send_message(YOUR_CHAT_ID, msg, parse_mode="HTML")
            notified_fixtures.add(fixture_id)

    except Exception as e:
      print(f"Ошибка при запросе к API: {e}")

    time.sleep(60)


if __name__ == "__main__":
  # Запускаем сканер в отдельном фоновом потоке
  t = threading.Thread(target=run_scanner)
  t.daemon = True
  t.start()

  # Запускаем веб-сервер на порту 10000 (требование Render)
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
