#!/bin/bash

# Скрипт для удаления бота из системных сервисов

LAUNCHD_FILE="$HOME/Library/LaunchAgents/com.visabarbi.bot.plist"

# Останавливаем и выгружаем сервис
if [ -f "$LAUNCHD_FILE" ]; then
    launchctl unload "$LAUNCHD_FILE" 2>/dev/null
    rm "$LAUNCHD_FILE"
    echo "✅ Бот удален из системных сервисов"
else
    echo "ℹ️  Бот не был установлен как сервис"
fi

