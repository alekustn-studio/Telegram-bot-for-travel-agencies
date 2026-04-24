"""
Обработчики команд и сообщений бота
"""
import os
import re
import asyncio
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import config
from database import save_contact, save_event, get_metrics_summary

router = Router()


class ContactStates(StatesGroup):
    """Состояния для сбора контактов"""
    waiting_for_contact = State()
    waiting_for_name = State()
    waiting_for_comment = State()


def get_main_keyboard():
    """Создает главное меню с двумя кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Все о визе во Францию")],
            [KeyboardButton(text="Связаться с агентом")]
        ],
        resize_keyboard=True
    )
    return keyboard


def is_phone(text: str) -> bool:
    """Проверка, является ли текст номером телефона"""
    # Убираем все пробелы, дефисы, скобки
    cleaned = re.sub(r'[\s\-\(\)]', '', text)
    # Проверяем формат: начинается с + и содержит цифры, или только цифры
    phone_pattern = r'^(\+?\d{10,15})$'
    return bool(re.match(phone_pattern, cleaned))


def is_username(text: str) -> bool:
    """Проверка, является ли текст username"""
    return text.startswith('@') and len(text) > 1


async def track_event(user_id: int, event_type: str, details: str = None):
    """Безопасная запись события, чтобы метрики не ломали UX"""
    try:
        await save_event(user_id=user_id, event_type=event_type, details=details)
    except Exception as event_error:
        print(f"Ошибка записи события {event_type}: {event_error}")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    import time
    start_time = time.time()
    print(f"📥 Получена команда /start от {message.from_user.id}")
    
    # Сбрасываем состояние при старте (на случай если пользователь был в процессе заполнения)
    await state.clear()
    await track_event(message.from_user.id, "start_command")
    await message.answer(
        config.WELCOME_MESSAGE,
        reply_markup=get_main_keyboard()
    )
    
    duration = (time.time() - start_time) * 1000
    print(f"✅ Ответ на /start отправлен за {duration:.0f}ms")


@router.message(Command("chatid"))
async def cmd_chatid(message: Message):
    """Показывает ID текущего чата (полезно для настройки)"""
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = message.chat.title or "Личный чат"
    
    info_text = f"""📋 <b>Информация о чате:</b>

🆔 <b>ID чата:</b> <code>{chat_id}</code>
📝 <b>Название:</b> {chat_title}
🔹 <b>Тип:</b> {chat_type}

💡 <b>Скопируйте ID чата</b> и вставьте в файл <code>.env</code> в переменную <code>NOTIFICATION_CHAT_ID</code>

Пример:
<code>NOTIFICATION_CHAT_ID={chat_id}</code>"""
    
    await message.answer(info_text, parse_mode="HTML")


@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда для проверки отправки сообщений в группу"""
    from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
    
    if not config.NOTIFICATION_CHAT_ID:
        await message.answer(
            "❌ NOTIFICATION_CHAT_ID не настроен в .env файле!\n\n"
            "Используйте команду /chatid в группе, чтобы узнать ID чата."
        )
        return
    
    try:
        bot = message.bot
        test_message = "🧪 <b>Тестовое сообщение</b>\n\nЕсли вы видите это сообщение, значит бот успешно отправляет уведомления в группу!"
        
        await bot.send_message(
            chat_id=config.NOTIFICATION_CHAT_ID,
            text=test_message,
            parse_mode="HTML"
        )
        
        await message.answer(
            f"✅ Тестовое сообщение успешно отправлено в чат!\n"
            f"ID чата: <code>{config.NOTIFICATION_CHAT_ID}</code>\n\n"
            f"Проверьте группу, там должно появиться тестовое сообщение.",
            parse_mode="HTML"
        )
        
    except TelegramForbiddenError:
        await message.answer(
            f"❌ <b>Ошибка доступа!</b>\n\n"
            f"Бот не может отправить сообщение в чат <code>{config.NOTIFICATION_CHAT_ID}</code>\n\n"
            f"<b>Что сделать:</b>\n"
            f"1. Убедитесь, что бот добавлен в группу\n"
            f"2. Отправьте команду <code>/start</code> боту <b>в самой группе</b> (это активирует бота)\n"
            f"3. Убедитесь, что бот имеет права администратора или может отправлять сообщения\n"
            f"4. Проверьте, что ID чата правильный (используйте /chatid в группе)",
            parse_mode="HTML"
        )
        
    except TelegramBadRequest as e:
        await message.answer(
            f"❌ <b>Ошибка запроса!</b>\n\n"
            f"Неверный ID чата или другая проблема.\n"
            f"ID: <code>{config.NOTIFICATION_CHAT_ID}</code>\n"
            f"Ошибка: {e}\n\n"
            f"Проверьте ID чата командой /chatid в группе",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Неожиданная ошибка:</b>\n\n{type(e).__name__}: {e}",
            parse_mode="HTML"
        )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает сводные метрики бота"""
    try:
        await track_event(message.from_user.id, "stats_command")
        metrics = await get_metrics_summary()
        event_lines = []
        for event_type, count in metrics.get("events_by_type", [])[:12]:
            event_lines.append(f"• {event_type}: <b>{count}</b>")

        events_text = "\n".join(event_lines) if event_lines else "Нет данных"
        stats_text = (
            "📊 <b>Метрики бота</b>\n\n"
            f"📥 Всего заявок: <b>{metrics.get('total_applications', 0)}</b>\n"
            f"👥 Уникальных заявителей: <b>{metrics.get('unique_applicants', 0)}</b>\n"
            f"🕘 Заявок сегодня: <b>{metrics.get('applications_today', 0)}</b>\n"
            f"📆 За 7 дней: <b>{metrics.get('applications_7d', 0)}</b>\n"
            f"🗓 За 30 дней: <b>{metrics.get('applications_30d', 0)}</b>\n\n"
            f"▶️ /start: <b>{metrics.get('start_commands', 0)}</b>\n"
            f"📄 Клики по гайду: <b>{metrics.get('guide_clicks', 0)}</b>\n"
            f"🤝 Клики «Связаться с агентом»: <b>{metrics.get('agent_clicks', 0)}</b>\n"
            f"✅ Завершенных заявок: <b>{metrics.get('applications_submitted_events', 0)}</b>\n\n"
            "<b>События по типам:</b>\n"
            f"{events_text}"
        )
        await message.answer(stats_text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при формировании /stats: {e}")
        await message.answer("❌ Не удалось получить метрики. Попробуйте позже.")


@router.message(F.text == "Все о визе во Францию")
async def send_guide(message: Message):
    """Обработчик кнопки 'Все о визе во Францию'"""
    import time
    start_time = time.time()
    print(f"📥 Получена кнопка 'Все о визе во Францию' от {message.from_user.id}")
    await track_event(message.from_user.id, "guide_button_click")
    
    try:
        # НЕМЕДЛЕННО отправляем ответ, чтобы пользователь знал, что бот работает
        processing_msg = await message.answer("📄 Загружаю гайд...")
        print(f"⏱️ Сообщение 'Загружаю гайд' отправлено за {(time.time() - start_time) * 1000:.0f}ms")
        
        # Проверяем существование файла (быстрая проверка)
        if not os.path.exists(config.PDF_FILE_PATH):
            await track_event(message.from_user.id, "guide_send_error", "file_not_found")
            await processing_msg.edit_text("❌ Файл с гайдом не найден. Обратитесь к администратору.")
            return
        
        # Проверяем размер файла
        file_size = os.path.getsize(config.PDF_FILE_PATH)
        if file_size > 50 * 1024 * 1024:  # 50 МБ
            await track_event(message.from_user.id, "guide_send_error", "file_too_large")
            await processing_msg.edit_text("❌ Файл слишком большой для отправки через Telegram (максимум 50 МБ).")
            return
        
        # Отправляем PDF файл
        try:
            pdf_file = FSInputFile(config.PDF_FILE_PATH)
            # Отправляем файл с таймаутом
            await asyncio.wait_for(
                message.answer_document(pdf_file),
                timeout=30.0  # 30 секунд максимум на отправку файла
            )
            await track_event(message.from_user.id, "guide_sent")
            # Удаляем сообщение "Загружаю..."
            try:
                await processing_msg.delete()
            except:
                pass
        except asyncio.TimeoutError:
            await track_event(message.from_user.id, "guide_send_error", "timeout")
            await processing_msg.edit_text("❌ Файл слишком большой или произошла ошибка при отправке. Попробуйте позже.")
            print(f"Таймаут при отправке PDF файла (размер: {file_size / 1024 / 1024:.2f} МБ)")
            return
        except Exception as pdf_error:
            await track_event(message.from_user.id, "guide_send_error", f"send_error:{type(pdf_error).__name__}")
            await processing_msg.edit_text("❌ Произошла ошибка при отправке файла. Попробуйте позже.")
            print(f"Ошибка при отправке PDF файла: {pdf_error}")
            return
        
        # Отправляем текст после PDF (с поддержкой ссылок)
        try:
            await message.answer(
                config.AFTER_PDF_MESSAGE,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
        except Exception as msg_error:
            # Если Markdown не работает, отправляем без форматирования
            print(f"Ошибка при отправке сообщения с Markdown: {msg_error}")
            fallback_message = config.AFTER_PDF_MESSAGE.replace("[тг-каналу](https://t.me/pinkwrd)", "тг-каналу https://t.me/pinkwrd")
            await message.answer(fallback_message)
        
    except Exception as e:
        import traceback
        await track_event(message.from_user.id, "guide_send_error", f"critical:{type(e).__name__}")
        print(f"Критическая ошибка при отправке гайда: {e}\n{traceback.format_exc()}")
        try:
            await message.answer(
                "❌ Произошла ошибка при отправке файла. Попробуйте позже или используйте команду /start"
            )
        except:
            pass


@router.message(F.text == "Связаться с агентом")
async def request_contact(message: Message, state: FSMContext):
    """Обработчик кнопки 'Связаться с агентом'"""
    # Сбрасываем предыдущее состояние на всякий случай
    await state.clear()
    await track_event(message.from_user.id, "agent_button_click")
    await message.answer(config.CONTACT_REQUEST_MESSAGE)
    await state.set_state(ContactStates.waiting_for_contact)


@router.message(ContactStates.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка контактных данных от пользователя"""
    try:
        contact_text = message.text.strip()
        
        # Проверяем, является ли текст номером телефона
        if not is_phone(contact_text):
            await track_event(message.from_user.id, "contact_invalid")
            await message.answer(config.INVALID_CONTACT_MESSAGE)
            return
        
        # Сохраняем телефон во временное хранилище
        await state.update_data(
            contact=contact_text,
            contact_type="phone"
        )
        await track_event(message.from_user.id, "contact_valid")
        
        # Запрашиваем имя
        await message.answer(config.CONTACT_RECEIVED_MESSAGE)
        await state.set_state(ContactStates.waiting_for_name)
    except Exception as e:
        print(f"Ошибка при обработке контакта: {e}")
        await track_event(message.from_user.id, "contact_processing_error", type(e).__name__)
        await message.answer("❌ Произошла ошибка. Попробуйте начать заново с команды /start")
        await state.clear()


@router.message(ContactStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка имени пользователя"""
    try:
        name = message.text.strip()
        
        if not name:
            await track_event(message.from_user.id, "name_invalid")
            await message.answer("Пожалуйста, отправьте ваше имя")
            return
        
        # Сохраняем имя во временное хранилище
        await state.update_data(name=name)
        await track_event(message.from_user.id, "name_received")
        
        # Запрашиваем комментарий
        await message.answer(config.NAME_RECEIVED_MESSAGE)
        await state.set_state(ContactStates.waiting_for_comment)
    except Exception as e:
        print(f"Ошибка при обработке имени: {e}")
        await track_event(message.from_user.id, "name_processing_error", type(e).__name__)
        await message.answer("❌ Произошла ошибка. Попробуйте начать заново с команды /start")
        await state.clear()


@router.message(ContactStates.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработка комментария пользователя"""
    try:
        comment = message.text.strip()
        
        # Получаем все сохраненные данные
        data = await state.get_data()
        contact = data.get("contact")
        contact_type = data.get("contact_type")
        name = data.get("name")
        
        # Проверяем наличие обязательных данных
        if not contact or not name:
            await track_event(message.from_user.id, "application_data_error")
            await message.answer("❌ Произошла ошибка при обработке данных. Попробуйте начать заново с команды /start")
            await state.clear()
            return
        
        # Сохраняем все данные в БД (в фоновом режиме, не блокируем ответ пользователю)
        username = message.from_user.username or message.from_user.first_name or "Без имени"
        
        # СНАЧАЛА отправляем ответ пользователю - это приоритет!
        try:
            await message.answer(
                config.ALL_DATA_RECEIVED_MESSAGE,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
        except Exception as msg_error:
            # Если Markdown не работает, отправляем без форматирования
            print(f"Ошибка при отправке сообщения с Markdown: {msg_error}")
            await message.answer(config.ALL_DATA_RECEIVED_MESSAGE.replace("[telegram-каналу](https://t.me/pinkwrd)", "telegram-каналу https://t.me/pinkwrd"))
        
        # Сбрасываем состояние сразу после ответа пользователю
        await state.clear()
        await track_event(message.from_user.id, "application_submitted")
        
        # Теперь сохраняем в БД и отправляем уведомление в фоне (не блокируем)
        async def save_and_notify():
            try:
                await save_contact(
                    user_id=message.from_user.id,
                    username=username,
                    contact=contact,
                    contact_type=contact_type,
                    name=name,
                    comment=comment
                )
            except Exception as db_error:
                print(f"Ошибка при сохранении в БД: {db_error}")
                await track_event(message.from_user.id, "application_save_error", type(db_error).__name__)
            
            try:
                await send_notification_to_chat(message, contact, contact_type, name, comment)
            except Exception as notify_error:
                print(f"Ошибка при отправке уведомления: {notify_error}")
                await track_event(message.from_user.id, "notification_error", type(notify_error).__name__)
        
        # Запускаем в фоне
        asyncio.create_task(save_and_notify())
    except Exception as e:
        print(f"Ошибка при обработке комментария: {e}")
        import traceback
        print(traceback.format_exc())
        await track_event(message.from_user.id, "comment_processing_error", type(e).__name__)
        await message.answer("❌ Произошла ошибка. Попробуйте начать заново с команды /start")
        await state.clear()


async def send_notification_to_chat(message: Message, contact: str, contact_type: str, name: str = None, comment: str = None):
    """Отправка уведомления о новой заявке в чат"""
    from datetime import datetime
    
    if not config.NOTIFICATION_CHAT_ID:
        print("⚠️ NOTIFICATION_CHAT_ID не настроен, уведомление не отправлено")
        return
    
    try:
        # Используем бота из сообщения
        bot = message.bot
        username = message.from_user.username or message.from_user.first_name or "Без имени"
        user_id = message.from_user.id
        
        print(f"📤 Отправка уведомления в чат {config.NOTIFICATION_CHAT_ID}")
        print(f"   Пользователь: {username} (ID: {user_id})")
        print(f"   Контакт: {contact}")
        print(f"   Имя: {name or 'Не указано'}")
        print(f"   Комментарий: {comment or 'Не указано'}")
        
        notification_text = config.NOTIFICATION_MESSAGE_TEMPLATE.format(
            username=username,
            user_id=user_id,
            contact=contact,
            name=name or "Не указано",
            comment=comment or "Не указано",
            date=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
        result = await bot.send_message(
            chat_id=config.NOTIFICATION_CHAT_ID,
            text=notification_text,
            parse_mode="HTML"
        )
        await track_event(user_id, "notification_sent")
        print(f"✅ Уведомление успешно отправлено в чат {config.NOTIFICATION_CHAT_ID} (message_id: {result.message_id})")
        
    except TelegramForbiddenError as e:
        await track_event(message.from_user.id, "notification_forbidden")
        error_msg = (
            f"❌ Ошибка: Бот не может отправить сообщение в чат {config.NOTIFICATION_CHAT_ID}\n"
            f"Возможные причины:\n"
            f"1. Бот не был активирован в группе (отправьте /start боту в группе)\n"
            f"2. Бот удален из группы\n"
            f"3. У бота нет прав на отправку сообщений\n"
            f"Детали: {e}"
        )
        print(error_msg)
        
    except TelegramBadRequest as e:
        await track_event(message.from_user.id, "notification_bad_request")
        error_msg = (
            f"❌ Ошибка: Неверный ID чата или другие проблемы с запросом\n"
            f"ID чата: {config.NOTIFICATION_CHAT_ID}\n"
            f"Детали: {e}"
        )
        print(error_msg)
        
    except Exception as e:
        import traceback
        await track_event(message.from_user.id, "notification_unexpected_error", type(e).__name__)
        error_msg = f"❌ Неожиданная ошибка при отправке уведомления: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(error_msg)


# Обработчик для всех остальных сообщений (чтобы бот всегда отвечал)
@router.message()
async def handle_other_messages(message: Message, state: FSMContext):
    """Обработчик для всех остальных сообщений"""
    try:
        # Проверяем, есть ли активное состояние
        current_state = await state.get_state()
        
        if current_state:
            # Если есть состояние, но сообщение не обработано - возможно пользователь отправил что-то неожиданное
            state_name = str(current_state).split(":")[-1] if ":" in str(current_state) else str(current_state)
            
            if "waiting_for_contact" in state_name:
                await message.answer(config.INVALID_CONTACT_MESSAGE)
            elif "waiting_for_name" in state_name:
                await message.answer("Пожалуйста, отправьте ваше имя")
            elif "waiting_for_comment" in state_name:
                await message.answer("Пожалуйста, отправьте комментарий или поставьте «–»")
            else:
                await message.answer("Пожалуйста, используйте кнопки меню или команду /start", reply_markup=get_main_keyboard())
        else:
            # Если нет состояния - просто показываем меню
            await message.answer(
                "Используйте кнопки меню для навигации ⬇️",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        print(f"Ошибка в handle_other_messages: {e}")
        await message.answer("Пожалуйста, используйте кнопки меню или команду /start", reply_markup=get_main_keyboard())

