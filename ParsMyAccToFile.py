import asyncio
import os
import re
from datetime import datetime
from tqdm import tqdm
from telethon import TelegramClient, events, utils
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
import random

#реклама - https://t.me/+Gf1TENQ5DAIyYmUy (канал создателя парсера)
# Замените на ваши данные
api_id = input("Введите api_id: ")
api_hash = input("Введите api_hash: ")

async def main():

    
    async with TelegramClient('my_session', api_id, api_hash) as client:
        # Получение списка чатов и их ID
        dialogs = await client.get_dialogs()
        print("Список чатов:")
        for i, dialog in enumerate(dialogs):
            print(f"{i+1}. {dialog.name} - (ID: {dialog.id})")

        # Запрос ID чата для парсинга
        chat_id_input = input("Введите ID чата для парсинга (Enter для всех чатов): ")
        if chat_id_input:
            # Преобразуем строку в число, сохраняя знак
            chat_ids = [int(chat_id_input)]
            if chat_ids[0] < 0:
                # Для каналов с отрицательным ID добавляем -100 перед ID
                chat_ids = [int(f"-100{abs(chat_ids[0])}")] if not str(chat_ids[0]).startswith('-100') else chat_ids
        else:
            chat_ids = [dialog.id for dialog in dialogs]

        # Выбор варианта парсинга
        print("\nВыберите вариант парсинга:")
        print("1. Все сообщения (стандартный)")
        print("2. Количество сообщений")
        print("3. По дате")
        variant = int(input("Введите номер варианта: "))

        if variant == 2:
            limit = int(input("Введите количество сообщений для обработки: ") or 0)
        elif variant == 3:
            date_str = input("Введите дату в формате ГГГГ-ММ-ДД: ")
            date = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            limit = 0
            date = None

        # Выбор режима парсинга
        print("\nВыберите режим парсинга:")
        print("1. Сообщения")
        print("2. Фото и видео")
        print("3. Музыка")
        print("4. Файлы")
        print("5. Все")
        print("реклама - https://t.me/+Gf1TENQ5DAIyYmUy (канал создателя парсера)")
        mode = int(input("Введите номер режима: "))

        for chat_id in chat_ids:
            try:
                await parse_chat(client, chat_id, mode, limit, date)
            except Exception as e:
                print(f"Ошибка при парсинге чата {chat_id}: {e}")

async def parse_chat(client, chat_id, mode, limit=0, date=None):
    try:
        # Пытаемся получить сущность канала/чата
        entity = await client.get_entity(chat_id)
        print(f"Успешно получен доступ к чату {chat_id}")
        
        offset_id = 0
        all_messages = []
        total_count = 0
        
        with tqdm(desc=f"Загрузка сообщений из чата {chat_id}") as pbar:
            while True:
                try:
                    # Используем get_messages вместо GetHistoryRequest
                    messages = await client.get_messages(
                        entity,
                        limit=100,
                        offset_id=offset_id,
                        reverse=True
                    )
                    
                    if not messages:
                        break
                    
                    message_count = len(messages)
                    all_messages.extend(messages)
                    total_count += message_count
                    pbar.update(message_count)
                    
                    if limit and total_count >= limit:
                        all_messages = all_messages[:limit]
                        break
                    
                    if date and messages[-1].date < date:
                        all_messages = [msg for msg in all_messages if msg.date >= date]
                        break
                    
                    offset_id = messages[-1].id
                    
                except Exception as e:
                    print(f"Ошибка при получении сообщений: {e}")
                    break

        if all_messages:
            print(f"Получено {len(all_messages)} сообщений из чата {chat_id}")
            await process_messages(all_messages, mode, chat_id)
        else:
            print(f"Не удалось получить сообщения из чата {chat_id}")
            
    except Exception as e:
        print(f"Ошибка при доступе к чату {chat_id}: {e}")

async def process_messages(messages, mode, chat_id):
    chat_folder = str(chat_id)
    try:
        if mode == 5:
            os.makedirs(chat_folder, exist_ok=True)

        tasks = []

        if mode in [1, 5]:
            if mode == 1:
                os.makedirs(chat_folder, exist_ok=True)
            tasks.append(save_messages(messages, chat_folder))

        if mode in [2, 5]:
            if mode == 2:
                os.makedirs(chat_folder, exist_ok=True)
            photo_folder = os.path.join(chat_folder, "photos")
            video_folder = os.path.join(chat_folder, "videos")
            os.makedirs(photo_folder, exist_ok=True)
            os.makedirs(video_folder, exist_ok=True)
            
            media_messages = [m for m in messages if m.media is not None]
            
            # Обработка фото
            photo_messages = [m for m in media_messages if isinstance(m.media, MessageMediaPhoto)]
            if photo_messages:
                tasks.append(download_media(photo_messages, photo_folder, [MessageMediaPhoto]))
            
            # Обработка видео
            video_messages = [m for m in media_messages if isinstance(m.media, MessageMediaDocument) 
                            and hasattr(m.media, 'document') 
                            and m.media.document.mime_type 
                            and m.media.document.mime_type.startswith('video/')]
            if video_messages:
                tasks.append(download_media(video_messages, video_folder, [MessageMediaDocument]))

#реклама - https://t.me/+Gf1TENQ5DAIyYmUy (канал создателя парсера)
        if mode in [3, 5]:
            if mode == 3:
                os.makedirs(chat_folder, exist_ok=True)
            music_folder = os.path.join(chat_folder, "music")
            os.makedirs(music_folder, exist_ok=True)
            tasks.append(download_media(messages, music_folder, [MessageMediaDocument], 
                               filter_func=lambda m: m.media.document.mime_type.startswith('audio/')))

        if mode in [4, 5]:
            if mode == 4:
                os.makedirs(chat_folder, exist_ok=True)
            files_folder = os.path.join(chat_folder, "files")
            os.makedirs(files_folder, exist_ok=True)
            tasks.append(download_media(messages, files_folder, [MessageMediaDocument]))

        await asyncio.gather(*tasks)

    except Exception as e:
        print(f"Ошибка при обработке чата {chat_id}: {e}")

async def save_messages(messages, chat_folder):
    with open(os.path.join(chat_folder, "messages.txt"), "w", encoding="utf-8") as f:
        for message in tqdm(messages, desc="Сохранение сообщений"):
            try:
                if message.message:
                    f.write(f"Время: {message.date}\nID: {message.id}\nТекст: {message.message}\n\n")
                # Добавляем случайную задержку от 1 до 3 секунд
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                print(f"Ошибка при сохранении сообщения {message.id}: {e}")

async def download_media(messages, folder, media_types, filter_func=None):
    tasks = []
    semaphore = asyncio.Semaphore(5)

    async def download_with_progress(message, folder):
        async with semaphore:
            try:
                if filter_func and not filter_func(message):
                    return

                # Добавляем случайную задержку от 1 до 3 секунд
                await asyncio.sleep(random.uniform(1, 3))

                if isinstance(message.media, MessageMediaDocument):
                    try:
                        original_name = message.media.document.attributes[0].file_name
                        # Очистка имени файла от недопустимых символов
                        safe_name = re.sub(r'[<>:"/\\|?*]', '_', original_name)
                        file_name = f"{message.id}_{safe_name}"
                    except:
                        file_name = f"{message.id}_document_{message.date.strftime('%Y%m%d_%H%M%S')}"
                else:
                    file_name = f"{message.id}_photo_{message.date.strftime('%Y%m%d_%H%M%S')}.jpg"
                
                file_path = os.path.join(folder, file_name)
                
                if not os.path.exists(file_path):
                    try:
                        await message.download_media(file=file_path)
                    except Exception as e:
                        print(f"Ошибка при скачивании {file_name}: {e}")
                        return False
                return True
            except Exception as e:
                print(f"Ошибка при обработке медиа: {e}")
                return False

    for message in messages:
        if message.media and isinstance(message.media, tuple(media_types)):
            tasks.append(asyncio.create_task(download_with_progress(message, folder)))

    if tasks:
        completed = []
        with tqdm(total=len(tasks), desc="Загрузка медиафайлов") as pbar:
            for task in asyncio.as_completed(tasks):
                result = await task
                if result:
                    completed.append(result)
                pbar.update(1)
        
        print(f"Успешно загружено {len(completed)} из {len(tasks)} файлов")

#реклама - https://t.me/+Gf1TENQ5DAIyYmUy (канал создателя парсера)
if __name__ == "__main__":
    try:
        asyncio.run(main()) 
    except KeyboardInterrupt:
        print("exid")