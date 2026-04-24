"""
Модуль для работы с базой данных
Использует SQLite для хранения данных пользователей
"""
import aiosqlite
from datetime import datetime
import os

DB_NAME = "bot_database.db"


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                contact TEXT NOT NULL,
                contact_type TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Добавляем колонку name если её нет (для существующих БД)
        try:
            await db.execute("ALTER TABLE contacts ADD COLUMN name TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            # Колонка уже существует
            pass
        # Добавляем колонку comment если её нет (для существующих БД)
        try:
            await db.execute("ALTER TABLE contacts ADD COLUMN comment TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            # Колонка уже существует
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_at
            ON events(created_at)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(event_type)
        """)
        await db.commit()


async def save_contact(user_id: int, username: str, contact: str, contact_type: str, name: str = None, comment: str = None):
    """
    Сохранение контакта пользователя в БД
    
    Args:
        user_id: ID пользователя Telegram
        username: Имя пользователя (может быть None)
        contact: Контактные данные (телефон или username)
        contact_type: Тип контакта ('phone' или 'username')
        name: Имя пользователя для обращения (может быть None)
        comment: Комментарий/ситуация пользователя (может быть None)
    """
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO contacts (user_id, username, contact, contact_type, name, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, contact, contact_type, name, comment))
        await db.commit()


async def get_all_contacts():
    """Получить все сохраненные контакты"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT user_id, username, contact, contact_type, name, comment, created_at
            FROM contacts
            ORDER BY created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return rows


async def save_event(user_id: int, event_type: str, details: str = None):
    """Сохранить событие пользователя для метрик"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO events (user_id, event_type, details)
            VALUES (?, ?, ?)
        """, (user_id, event_type, details))
        await db.commit()


async def get_metrics_summary():
    """Получить сводку метрик по заявкам и событиям"""
    async with aiosqlite.connect(DB_NAME) as db:
        metrics = {}

        async with db.execute("SELECT COUNT(*) FROM contacts") as cursor:
            metrics["total_applications"] = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM contacts") as cursor:
            metrics["unique_applicants"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM contacts
            WHERE DATE(created_at) = DATE('now', 'localtime')
        """) as cursor:
            metrics["applications_today"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM contacts
            WHERE datetime(created_at) >= datetime('now', 'localtime', '-7 days')
        """) as cursor:
            metrics["applications_7d"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM contacts
            WHERE datetime(created_at) >= datetime('now', 'localtime', '-30 days')
        """) as cursor:
            metrics["applications_30d"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT event_type, COUNT(*)
            FROM events
            GROUP BY event_type
            ORDER BY COUNT(*) DESC
        """) as cursor:
            metrics["events_by_type"] = await cursor.fetchall()

        async with db.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE event_type = 'start_command'
        """) as cursor:
            metrics["start_commands"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE event_type = 'guide_button_click'
        """) as cursor:
            metrics["guide_clicks"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE event_type = 'agent_button_click'
        """) as cursor:
            metrics["agent_clicks"] = (await cursor.fetchone())[0]

        async with db.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE event_type = 'application_submitted'
        """) as cursor:
            metrics["applications_submitted_events"] = (await cursor.fetchone())[0]

        return metrics

