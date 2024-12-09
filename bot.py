import telebot
import re
import logging
import os
import random
import shutil

BOT_TOKEN = "8197872225:AAF1v7l3Mu3w9Vm2UU1jzQareH6Nxy9hLB0"  # Your bot token
ADMIN_ID = 1764250421  # Your admin ID

PENDING_FILENAME = "pending.txt"
APPROVED_FILENAME = "approved.txt"
ALL_TICKETS_FILENAME = "AllTickets.txt"
WINNERS_FILENAME = "winners.txt"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}
email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
user_tickets = {}
preselected_winners = {}  # Словарь для предварительно выбранных победителей
winners_announced = False  # Флаг, указывающий, объявлены ли победители
NUM_WINNERS = 30  # Количество победителей


# --- Обработка сообщений пользователей ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправьте свою почту, а затем, следующим сообщением, скриншот депозита, чтобы участвовать. Каждый депозит - одна заявка. Каждая заявка может занять одно призовое место. Вы можете увидеть количество одобренных заявок по команде /mytickets")


@bot.message_handler(commands=['mytickets'])
def my_tickets(message):
    user_id = message.from_user.id
    approved_count = get_approved_count(user_id)
    bot.reply_to(message, f"У вас {approved_count} одобренных заявок.")


@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID, content_types=['text', 'photo'])
def handle_user_message(message):
    if message.content_type == 'text':
        email = message.text
        if re.match(email_regex, email):
            user_data[message.from_user.id] = {'email': email, 'username': message.from_user.username}
            bot.reply_to(message, "Почта получена. Теперь отправьте скриншот депозита.")
        else:
            bot.reply_to(message, "Неверный формат почты. Попробуйте ещё раз.")
    elif message.content_type == 'photo' and message.from_user.id in user_data:
        user_info = user_data[message.from_user.id]
        user_id = message.from_user.id
        username = user_info['username']
        email = user_info['email']
        ticket_id = get_next_ticket_id()

        try:
            with open(ALL_TICKETS_FILENAME, "a", encoding="utf-8") as f:
                f.write(f"{ticket_id}:{user_id}:{username}:{email}\n")
            with open(PENDING_FILENAME, "a", encoding="utf-8") as f:
                f.write(f"{ticket_id}:{user_id}:{username}:{email}\n")

            bot.reply_to(message, f"Ваша заявка (Ticket ID: {ticket_id}) отправлена на проверку.")
            del user_data[user_id]
            approved_count = get_approved_count(user_id)
            admin_new_application(ticket_id, user_id, username, email, message.photo[-1], approved_count)
        except Exception as e:
            logging.exception(f"Ошибка при обработке заявки пользователя: {e}")
            bot.reply_to(message, f"Произошла ошибка при обработке заявки: {e}")
    elif message.content_type == 'photo':
        bot.reply_to(message, "Сначала отправьте свою почту.")


# --- Обработка сообщений администратора ---

def admin_new_application(ticket_id, user_id, username, email, photo, approved_count):
    caption = f"Новая заявка (Ticket ID: {ticket_id}):\n\nID: {user_id}\nUsername: @{username}\nEmail: {email}\nОдобренных заявок: {approved_count}"
    try:
        file_info = bot.get_file(photo.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f"photo_{ticket_id}.jpg", 'wb') as new_file:
            new_file.write(downloaded_file)
        with open(f"photo_{ticket_id}.jpg", 'rb') as f:
            bot.send_photo(ADMIN_ID, f, caption=caption)
        os.remove(f"photo_{ticket_id}.jpg")
    except Exception as e:
        logging.exception(f"Ошибка отправки фото администратору: {e}")


@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_message(message):
    if message.text.startswith('/approve'):
        try:
            command, ticket_id_str = message.text.split()
            ticket_id = int(ticket_id_str)
            process_admin_command(command, ticket_id, message)
        except (ValueError, IndexError):
            bot.reply_to(message, "Неверный формат команды. Используйте /approve [TicketId]")
        except Exception as e:
            logging.exception(f"Ошибка при обработке команды администратора: {e}")
            bot.reply_to(message, f"Произошла ошибка при обработке команды: {e}")
    elif message.text.startswith('/reject'):
        try:
            command, ticket_id_str, *comment = message.text.split(maxsplit=2)
            ticket_id = int(ticket_id_str)
            comment = " ".join(comment)
            process_admin_command(command, ticket_id, message, comment)
        except (ValueError, IndexError):
            bot.reply_to(message, "Неверный формат команды. Используйте /reject [TicketId] [комментарий]")
        except Exception as e:
            logging.exception(f"Ошибка при обработке команды администратора: {e}")
            bot.reply_to(message, f"Произошла ошибка при обработке команды: {e}")
    elif message.text.startswith('/winner'):
        try:
            command, place_str, email = message.text.split(maxsplit=2)
            place = int(place_str)
            if 1 <= place <= NUM_WINNERS: # Проверка места в пределах количества победителей
                preselected_winners[place] = email
                bot.reply_to(message, f"Победитель на {place} место назначен: {email}")
            else:
                bot.reply_to(message, f"Некорректный номер места. Номер места должен быть от 1 до {NUM_WINNERS}.")
        except (ValueError, IndexError):
            bot.reply_to(message, f"Неверный формат команды. Используйте /winner [место] [email] (место от 1 до {NUM_WINNERS})")
        except Exception as e:
            logging.exception(f"Ошибка при назначении победителя: {e}")
            bot.reply_to(message, f"Произошла ошибка при назначении победителя: {e}")
    elif message.text == '/finish':
        try:
            global winners_announced
            winners = choose_winners()
            winners_announced = True
            admin_message = create_winners_message(winners, True)  # Имена пользователей для администратора
            user_message = create_winners_message(winners, False)  # Email для пользователей
            bot.reply_to(message, "Результаты розыгрыша готовы. Используйте /sendall для отправки.")
            bot.send_message(ADMIN_ID, admin_message)
            bot.send_message(ADMIN_ID, user_message)

        except Exception as e:
            logging.exception(f"Ошибка при объявлении победителей: {e}")
            bot.reply_to(message, f"Произошла ошибка при объявлении победителей: {e}")
    elif message.text == '/sendall' and winners_announced:
        try:
            winners = choose_winners()
            user_message = create_winners_message(winners, False)
            send_winners_message(user_message)
            bot.reply_to(message, "Результаты розыгрыша отправлены!")
            winners_announced = False
        except Exception as e:
            logging.exception(f"Ошибка при отправке сообщений пользователям: {e}")
            bot.reply_to(message, f"Произошла ошибка при отправке сообщений пользователям: {e}")
    else:
        bot.reply_to(message, "Неизвестная команда. Используйте /approve [TicketId] или /reject [TicketId] [комментарий] или /winner [место] [email]")



def process_admin_command(command, ticket_id, message, comment=""):
    try:
        with open(PENDING_FILENAME, 'r', encoding='utf-8') as f:
            pending_lines = f.readlines()

        with open(PENDING_FILENAME, 'w', encoding='utf-8') as outfile:
            found = False
            for line in pending_lines:
                parts = line.strip().split(':')
                if int(parts[0]) == ticket_id:
                    user_id = int(parts[1])
                    if command == '/approve':
                        with open(APPROVED_FILENAME, 'a', encoding='utf-8') as approved_file:
                            approved_file.write(line)
                        bot.reply_to(message, "Заявка одобрена.")
                        send_user_notification(user_id, f"Ваша заявка (Ticket ID: {ticket_id}) одобрена!")
                        user_tickets[user_id] = user_tickets.get(user_id, 0) + 1
                    else:  # command == '/reject'
                        bot.reply_to(message, "Заявка отклонена.")
                        send_user_notification(user_id, f"К сожалению, ваша заявка (Ticket ID: {ticket_id}) отклонена. Комментарий администратора: {comment}")
                    found = True
                else:
                    outfile.write(line)

            if not found:
                bot.reply_to(message, "Заявка не найдена.")

    except Exception as e:
        logging.exception(f"Ошибка при обработке заявки: {e}")
        bot.reply_to(message, f"Произошла ошибка при обработке заявки: {e}")


def send_user_notification(user_id, text):
    try:
        bot.send_message(user_id, text)
    except telebot.apihelper.ApiException as e:
        logging.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")


def get_next_ticket_id():
    if os.path.exists(ALL_TICKETS_FILENAME):
        with open(ALL_TICKETS_FILENAME, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_ticket_id = int(lines[-1].split(':')[0])
                return last_ticket_id + 1
    return 1


def get_approved_count(user_id):
    count = 0
    if os.path.exists(APPROVED_FILENAME):
        with open(APPROVED_FILENAME, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(':')
                if int(parts[1]) == user_id:
                    count += 1
    return count


def choose_winners():
    approved_users = []
    if os.path.exists(APPROVED_FILENAME):
        with open(APPROVED_FILENAME, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 4:
                    approved_users.append((parts[1], parts[2], parts[3]))  # (user_id, username, email)

    if not approved_users:
        return []

    num_approved = len(approved_users)
    num_winners = min(NUM_WINNERS, num_approved)  # Выбираем меньшее из количества победителей и одобренных заявок

    random.shuffle(approved_users)
    unfilled_places = set(range(1, NUM_WINNERS + 1)) - set(preselected_winners.keys())
    winners = []

    # Добавляем предварительно выбранных победителей
    for place in range(1, NUM_WINNERS + 1):
        if place in preselected_winners:
            email = preselected_winners[place]
            user_match = next((user for user in approved_users if user[2] == email), None)
            if user_match:
                winners.append(user_match)
                approved_users.remove(user_match)
            else:
                winners.append(("", "", email))  # Заполнитель, если email не найден

    # Заполняем оставшиеся места случайными пользователями.
    for place in sorted(list(unfilled_places)):
        if approved_users:
            winners.append(approved_users.pop())

    return winners


def create_winners_message(winners, use_usernames):
    if not winners:
        return "Победителей нет!"

    message = "Победители розыгрыша:\n"
    for i, (user_id, username, email) in enumerate(winners):
        place = i + 1
        if use_usernames:
            message += f"{place} место: @{username}\n"
        else:
            message += f"{place} место: {format_email(email)}\n"
    return message


def send_winners_message(message):
    approved_users = []
    if os.path.exists(APPROVED_FILENAME):
        with open(APPROVED_FILENAME, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    approved_users.append(parts[1])

    for user_id in set(approved_users):
        try:
            bot.send_message(int(user_id), message)
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")


def format_email(email):
    parts = email.split('@')
    if len(parts) != 2:
        return email  # Обработка неверных email

    local_part = parts[0]
    domain_part = parts[1]

    return f"{local_part[:3]}***{local_part[-1 if len(local_part) < 4 else -2:]}@{domain_part}"


bot.polling()
