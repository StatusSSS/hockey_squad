# Парсер Hockey Squad Scraper

- __Назначение__: регулярно парсит страницу “Squad” хоккейных команд  и синхронизирует составы c собственной MySQL-БД
- __Источник данных__: Flashscore.com
- __Периодичность запуска__: бесконечный цикл с паузой main_loop_delay
- __Зависимости__: `beautifulsoup4, loguru, PyMySQL, python-dotenv, Requests, tqdm`
- __Ответственный__: Нарек Бабахани
- __Примечания__: 

  - PlayersRepo перечитывает таблицу после каждой INSERT/UPDATE, исключая рассинхрон
  - набор CSS-классов NATIONAL_TEAM_FLAGS; при изменении статуса команды происходит UPDATE hockey_teams.is_national
  - любой сбой в обработке одной команды лишь логируется; цикл продолжает работу




## Как запустить на сервере:

1. Клонируем репозиторий
    ```
   
    git clone https://github.com/StatusSSS/hockey_squad.git
   
    cd hockey_squad
   ```

2. Cоздаем virtualenv внутри проекта
    ```
    python3 -m venv venv
    
    source venv/bin/activate
   ```

3. Устанавливаем зависимости
    ```
    pip install --upgrade pip
    
    pip install -r hockey_squad_scraper/deploy/requirements.txt
   ```

4. В каталоге deploy лежит .env файл, перенесите его в корень проекта и заполните его

    ```
    DB_HOST=
    DB_PORT=
    DB_USER=
    DB_PASS=
    DB_NAME=
    DB_SSL_CA= 
   ```

5. Проверяем, что скрипт запускается вручную
    ```
    python -m hockey_squad_scraper.runner
   ```

## Systemd‑служба

#### Сохраните файл hockey_squad_scraper.service у себя в systemd/system, заранее заменив поля <...>:

```angular2html
[Unit]
Description=Hockey Squad Scraper
After=network.target

[Service]
User=<SYSTEM_USER>
Group=<SYSTEM_GROUP>

WorkingDirectory=<ABSOLUTE_PATH_TO>/hockey_squad
EnvironmentFile=<ABSOLUTE_PATH_TO>/hockey_squad/.env
ExecStart=<ABSOLUTE_PATH_TO>/hockey_squad/venv/bin/python -m hockey_squad_scraper.runner

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- User/Group — системный пользователь, под которым будет крутиться сервис
- <ABSOLUTE_PATH_TO> — абсолютный путь к проекту

## Активация systemd
    
```
# Перечитываем конфигурацию systemd
sudo systemctl daemon-reload

# Включаем автозапуск при загрузке
sudo systemctl enable --now hockey_squad_scraper.service

# Проверяем статус
sudo systemctl status hockey_squad_scraper.service
```
    