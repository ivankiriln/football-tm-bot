import os
import threading
import time
import requests
import telebot
from flask import Flask

# ВПИШИТЕ СВОИ ДАННЫЕ СЮДА НАПРЯМУЮ:
BOT_TOKEN = "8650310728:AAHIzpkMPMhGowNy75z0t0LUiN6OIBt57aE"
API_FOOTBALL_KEY = "f95358a2ff2959314d353d610a94500a"
YOUR_CHAT_ID = "775785461"  # Ваш ID из Telegram[span_0](start_span)[span_0](end_span)

bot = telebot.TeleBot(BOT_TOKEN)
notified_fixtures = set()

app = Flask(__name__)


@app.route("/")
def home():
  return "Football Scanner Bot is running!"


def run_scanner():
  print("🚀 Бот-сканер запущен!")

  try:
    bot.send_message(
        YOUR_CHAT_ID,
        "🤖 Бот успешно запущен и начал сканирование матчей!",
        parse_mode="HTML",
    )
  except Exception as e:
    print(f"Ошибка отправки тестового сообщения: {e}")

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
        live_matches = data["response"]
        print(f"🔍 Найдено лайв-матчей: {len(live_matches)}")

        for fixture in live_matches:
          fixture_id = fixture["fixture"]["id"]
          elapsed = fixture["fixture"]["status"]["elapsed"]
          goals_home = fixture["goals"]["home"]
          goals_away = fixture["goals"]["away"]

          if not (10 <= elapsed <= 25):
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

          if 2 <= total_shots <= 12 and shots_on_target <= 2 and yellow_cards <= 2:
            home_team = fixture["teams"]["home"]["name"]
            away_team = fixture["teams"]["away"]["name"]
            league = fixture["league"]["name"]

            msg = (
                f"🎯 <b>Сигнал на ТМ 2.5</b>\n\n"
                f"🏆 <i>Лига:</i> {league}\n"
                f"⚔️ <i>Матч:</i> {home_team} - {away_team}\n"
                f"⏱ <i>Минута:</i> {elapsed}' | <i>Счет:</i> 0:0\n"
                f"📊 <i>Статистика:</i> Всего ударов: {total_shots}, В створ: {shots_on_target}, ЖК: {yellow_cards}"
            )

            bot.send_message(YOUR_CHAT_ID, msg, parse_mode="HTML")
            notified_fixtures.add(fixture_id)

    except Exception as e:
      print(f"Ошибка: {e}")

    time.sleep(60)


if __name__ == "__main__":
  t = threading.Thread(target=run_scanner)
  t.daemon = True
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
