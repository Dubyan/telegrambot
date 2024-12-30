import telebot
import logging
import os

BOT_TOKEN = "YOUR_BOT_TOKEN"  # Замени на свой токен
ALL_TICKETS_FILENAME = "AllTickets.txt"
ADMIN_ID = YOUR_ADMIN_ID # ID администратора

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['sendall'])
def send_message_to_all(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open(ALL_TICKETS_FILENAME, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    user_id = int(parts[1])
                    try:
                        bot.send_message(user_id, "Ваше сообщение здесь")
                    except Exception as e:
                        logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        bot.reply_to(message, "Сообщения отправлены.")

    except FileNotFoundError:
        bot.reply_to(message, f"Файл {ALL_TICKETS_FILENAME} не найден.")
    except Exception as e:
        logging.exception(f"Ошибка при отправке сообщений: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")



@bot.message_handler(commands=['delete_all'])
def delete_last_message_for_all(message):
    """Удаляет последнее сообщение бота у всех пользователей из AllTickets.txt."""
    if message.from_user.id != ADMIN_ID:
        return

    try:
        with open(ALL_TICKETS_FILENAME, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    user_id = int(parts[1])
                    try:
                        chat_history = bot.get_chat_history(user_id, limit=100)
                        last_bot_message_id = None
                        for msg in chat_history:
                            if msg.from_user.id == bot.get_me().id:
                                last_bot_message_id = msg.message_id
                                break 
                        if last_bot_message_id:
                            bot.delete_message(user_id, last_bot_message_id)

                    except telebot.apihelper.ApiException as e:
                        logging.error(f"Ошибка удаления сообщения у пользователя {user_id}: {e}")


        bot.reply_to(message, "Последние сообщения бота удалены (где это было возможно).")

    except FileNotFoundError:
        bot.reply_to(message, f"Файл {ALL_TICKETS_FILENAME} не найден.")
    except Exception as e:
        logging.exception(f"Ошибка при удалении сообщений: {e}")
        bot.reply_to(message, f"Произошла ошибка: {e}")


bot.polling()
