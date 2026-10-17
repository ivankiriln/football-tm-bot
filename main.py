import time
import requests
import telebot

BOT_TOKEN = "8650310728:AAHIzpkMPMhGowNy75z0t0LUiN6OIBt57aE"
API_FOOTBALL_KEY = "f95358a2ff2959314d353d610a94500a"
YOUR_CHAT_ID = "8650310728"

bot = telebot.TeleBot(BOT_TOKEN)

# Словарь, чтобы не спамить повторно по одному и тому же матчу
notified_fixtures = set()


def check_live_matches():
  url = "https://v3.football.api-sports.io/fixtures"
  querystring = {"live": "all"}  # 1 запрос на получение всех матчей мира
  headers = {
      "x-rapidapi-host": "v3.football.api-sports.io",
      "x-rapidapi-key": API_FOOTBALL_KEY,
  }

  try:
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    if "response" not in data:
      return

    # Перебираем все матчи, которые сейчас идут в лайве
    for fixture in data["response"]:
      fixture_id = fixture["fixture"]["id"]
      elapsed = fixture["fixture"]["status"]["elapsed"]
      goals_home = fixture["goals"]["home"]
      goals_away = fixture["goals"]["away"]

      # ЭТАП 1: Грубый фильтр по времени и счету (тратит 0 дополнительных запросов)
      if not (14 <= elapsed <= 17):
        continue
      if goals_home != 0 or goals_away != 0:
        continue

      if fixture_id in notified_fixtures:
        continue

      # ЭТАП 2: Запрашиваем статистику ТОЛЬКО для тех матчей, которые прошли Первый этап
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

          if typ == "Shshots on Goal":
            shots_on_target += val
          elif typ == "Total Shots":
            total_shots += val
          elif typ == "Yellow Cards":
            yellow_cards += val

      # ЭТАП 3: Финальный фильтр (ударов 5-10, в створ <= 1, карточек 0)
      if 5 <= total_shots <= 10 and shots_on_target <= 1 and yellow_cards == 0:
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


if __name__ == "__main__":
  print("Бот-сканер с оптимизацией лимитов запущен...")
  while True:
    check_live_matches()
    # Проверяем каждые 60 секунд. За сутки это сделает ~1440 общих запросов к списку,
    # но детальные запросы будут уходить только на подходящие матчи (их будет не больше 20-30 в день)!
    time.sleep(60)
