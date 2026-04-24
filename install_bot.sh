#!/bin/bash

# Скрипт для установки бота как системного сервиса

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_FILE="$SCRIPT_DIR/com.visabarbi.bot.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_FILE="$LAUNCHD_DIR/com.visabarbi.bot.plist"

# Проверяем путь к python3
PYTHON3_PATH=$(which python3)
if [ -z "$PYTHON3_PATH" ]; then
    echo "❌ Python3 не найден! Установите Python3."
    exit 1
fi

echo "📍 Найден Python3: $PYTHON3_PATH"

# Создаем директорию LaunchAgents если её нет
mkdir -p "$LAUNCHD_DIR"

# Пишем plist в LaunchAgents из шаблона (файл в репо не трогаем — остаются плейсхолдеры)
sed -e "s|__PYTHON3_PATH__|$PYTHON3_PATH|g" -e "s|__BOT_DIRECTORY__|$SCRIPT_DIR|g" "$PLIST_FILE" > "$LAUNCHD_FILE"
echo "✅ Файл конфигурации записан в $LAUNCHD_FILE"

# Загружаем сервис
launchctl load "$LAUNCHD_FILE" 2>/dev/null || launchctl load -w "$LAUNCHD_FILE"
echo "✅ Бот установлен и запущен!"

echo ""
echo "📋 Управление ботом:"
echo "   Запуск:   launchctl start com.visabarbi.bot"
echo "   Остановка: launchctl stop com.visabarbi.bot"
echo "   Статус:   launchctl list | grep visabarbi"
echo "   Логи:     tail -f $SCRIPT_DIR/bot.log"
echo ""
echo "🔄 Бот будет автоматически запускаться при загрузке системы"

