Проект Telegram бота (aiogram) — подготовка для деплоя на Railway

Что я сделал
- Добавил рабочий скрипт bot.py в корень репозитория.
- Добавил Procfile, requirements.txt и runtime.txt для корректной сборки на Railway.
- Добавил .env.example и .gitignore.

Важные шаги для вас
1) СРОЧНО: Отозовите скомпрометированный BOT_TOKEN в BotFather и получите новый токен.
2) В Railway -> ваш сервис -> Variables добавьте переменные окружения (Raw Editor или по одной):
   BOT_TOKEN = <новый_токен> (отметьте Secret)
   OPERATORS_GROUP_ID = -1003938799843
   CHANNEL_ID = -1003947746512
   CHANNEL_INVITE_LINK = https://telegram.me/omgbelinee
   SUPPORT_USERNAME = @offcarrera
   ADMIN_IDS = 8317579434
   BOT_LINK = https://telegram.me/omgbelinee_bot
   ENV = production
3) Убедитесь, что в настройках сервиса указан Root Directory = (корень) — сейчас файлы лежат в корне.
4) Redeploy в Railway.

Проверка
- После деплоя смотрите логи Deployments -> View Logs. В логах появится информация о том, какие переменные видны (True/False).

Если сборка снова не запускается и видите "Agent usage limit reached" — это ограничение Railway. В этом случае:
- Подождите восстановление лимитов, или
- Апгрейдните план Railway, или
- Я могу подготовить Dockerfile, чтобы вы собрали образ локально и задеплоили как image.
