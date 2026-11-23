# battery_type — асинхронное вращение модели

Python 3.11+; зависимости только стандартной библиотеки. Запуск: `python battery_type_async.py`.
Главный API по умолчанию `http://127.0.0.1:53000/api`; порт этого сервиса 53002.

Один метод: `POST /battery_type/rotation`, JSON `{"batteryTypeId":1}`. Ответ 202 означает принятие задачи, а не завершение.
Через 7 секунд: x'=(x+π/6) mod 2π; y'=(y+π/4) mod 2π. Предыдущее положение читается HTTP GET, новое передаётся HTTP PUT с `X-Battery-Type-Key: battery8`. Прямого доступа к PostgreSQL нет. Главный API применяет compare-and-set по previousX/previousY, предотвращая перезапись более нового результата.

Переменные: BATTERY_TYPE_API_URL, BATTERY_TYPE_ASYNC_KEY, BATTERY_TYPE_ROTATION_DELAY (5–10), HOST, PORT.
Задачи хранятся в памяти; при остановке процесса незавершённые задачи теряются. Повторный запрос для уже ожидающего типа не создаёт вторую задачу. Логи содержат результат callback или ошибку.
