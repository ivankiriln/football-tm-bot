import os
import threading
import time
import requests
import telebot
from flask import Flask

# Получаем ключи из настроек Render (Environment Variables)
BOT_TOKEN = os.getenv("8650310728:AAHIzpkMPMhGowNy75z0t0LUiN6OIBt57aE")
API_FOOTBALL_KEY = os.getenv("f95358a2ff2959314d353d610a94500a")

# ВАЖНО: Укажите ваш ID в Telegram (в кавычках)
YOUR_CHAT_ID = "8650310728"  # <-- ВСТАВЬТЕ СВОЙ ID СЮДА

bot = telebot.TeleBot(BOT_TOKEN)
notified_fixtures = set()

# Веб-сервер для удержания порта на Render
app = Flask(__name__)


@app.route("/")
def home():
  return "Football Scanner Bot is running!"


def run_scanner():
  print("🚀 Бот-сканер запущен и готов к поиску матчей...")

  # 1. Отправляем тестовое сообщение в Telegram при запуске
  try:
    bot.send_message(
        YOUR_CHAT_ID,
        "🤖 <b>Бот-сканер успешно запущен!</b>\n\n"
        "Система подключена и опрашивает лайв-матчи. Как только появится подходящая игра, вы получите сигнал.",
        parse_mode="HTML",
    )
  except Exception as e:
    print(f"Ошибка отправки тестового сообщения: {e}")

  # 2. Основной цикл сканирования
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

          # РАСШИРЕННЫЙ ФИЛЬТР (чтобы сигналы приходить чаще):
          # Сканируем диапазон с 10 по 25 минуту со счетом 0:0
          if not (10 <= elapsed <= 25):
            continue
          if goals_home != 0 or goals_away != 0:
            continue

          # Пропускаем матч, если по нему уже отправляли сигнал
          if fixture_id in notified_fixtures:
            continue

          # Запрашиваем статистику по матчу
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

          # МЯГКИЕ КРИТЕРИИ ДЛЯ ВАЛУЙНЫХ СИГНАЛОВ:
          # Ударов от 2 до 12, в створ <= 2, желтых карточек <= 2
          if 2 <= total_shots <= 12 and shots_on_target <= 2 and yellow_cards <= 2:
            home_team = fixture["teams"]["home"]["name"]
            away_team = fixture["teams"]["away"]["name"]
            league = fixture["league"]["name"]

            msg = (
                f"🎯 <b>Сигнал на ТМ 2.5 (Кэф ~2.00+)</b>\n\n"
                f"🏆 <i>Лига:</i> {league}\n"
                f"⚔️ <i>Матч:</i> {home_team} - {away_team}\n"
                f"⏱ <i>Минута:</i> {elapsed}' | <i>Счет:</i> 0:0\n"
                f"📊 <i>Статистика:</i> Всего ударов: {total_shots}, В створ: {shots_on_target}, ЖК: {yellow_cards}\n\n"
                f"💡 <i>Рекомендация:</i> Низкая динамика, подходит для ТМ 2.5"
            )

            bot.send_message(YOUR_CHAT_ID, msg, parse_mode="HTML")
            notified_fixtures.add(fixture_id)

    except Exception as e:
      print(f"Ошибка при работе сканера: {e}")

    # Интервал проверки — 60 секунд
    time.sleep(60)


if __name__ == "__main__":
  t = threading.Thread(target=run_scanner)
  t.daemon = True
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
