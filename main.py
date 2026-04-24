"""
Основной файл для запуска Telegram бота
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

import config
from database import init_db
from handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Проверка наличия токена
    if not config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден! Проверьте файл .env")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN, 
        parse_mode=ParseMode.HTML
    )
    dp = Dispatcher()
    
    # Подключаем роутер с обработчиками
    dp.include_router(router)
    
    # Инициализация базы данных
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Проверка настроек
    if not config.NOTIFICATION_CHAT_ID:
        logger.warning("⚠️ NOTIFICATION_CHAT_ID не настроен! Уведомления не будут отправляться")
    
    logger.info("🚀 Бот запущен и готов к работе!")
    
    try:
        # Запуск бота с улучшенной обработкой ошибок сети
        await dp.start_polling(
            bot, 
            allowed_updates=["message", "callback_query"],
            # Увеличиваем таймауты для стабильности при проблемах с сетью
            close_bot_session=False
        )
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при работе бота: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        try:
            await bot.session.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())

