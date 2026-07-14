# belinee4-main

Это пример простого Telegram-бота на aiogram, подготовленный для деплоя на Railway.

Важные шаги перед деплоем

1) НЕ коммитьте реальный .env с секретами в репозиторий.
2) В Railway откройте проект → вкладка Variables и задайте переменные окружения (вставьте реальные значения):
   - BOT_TOKEN
   - OPERATORS_GROUP_ID
   - CHANNEL_ID
   - CHANNEL_INVITE_LINK
   - SUPPORT_USERNAME
   - ADMIN_IDS
   - BOT_LINK
   - ENV (можно оставить "production")

3) Убедитесь, что Procfile находится в корне директории проекта (в этом репозитории он лежит в belinee4-main/Procfile).
   Railway использует Procfile для запуска процесса. Для Telegram-бота лучше использовать worker: python bot.py

4) После добавления переменных в Railway — перезапустите деплой (Redeploy). Если сборка падает — откройте полные логи сборки и отправьте их сюда.

Запуск локально

1) Скопируйте .env.example в .env и заполните значения (только локально!).
2) pip install -r requirements.txt
3) python bot.py

Если нужно — могу сам добавить дополнительные обработчики, healthcheck web-сервер или webhook поддержку. Но секреты и переменные окружения добавлять в Railway должен владелец проекта.
