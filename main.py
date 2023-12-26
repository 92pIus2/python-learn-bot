import telebot
import subprocess
from telebot import types
from model import User, Task, Test
import database
import os
import project_strings


def run_code(folder_name, file_name, code=""):
    if not os.path.exists(os.path.join(os.getcwd(), folder_name)):
        os.makedirs(os.path.join(os.getcwd(), folder_name))
    with open(folder_name + "/" + file_name + '.py', 'w') as file:
        file.write(code)
    try:
        result = subprocess.check_output(['python3', folder_name + "/" + file_name + '.py'],
                                         stderr=subprocess.STDOUT, timeout=10, universal_newlines=True)
        return str(result)
    except subprocess.CalledProcessError as e:
        return project_strings.runtime_error + e.output
    except subprocess.TimeoutExpired:
        return project_strings.time_limit


class Checker:
    def __init__(self, task, code, username):
        self.task = task
        self.code = code
        self.username = username

    def check(self):
        for test in self.task.tests:
            result = run_code(folder_name=self.task.name, file_name=self.username,
                              code=self.code + "\nprint(" + self.task.name + "(" + test.to_input() + "))")
            if not test.check_test(result):
                return project_strings.error_on_test + str(test.to_input()) + project_strings.expected + \
                    str(test.answer) + project_strings.found + str(result)
        return project_strings.all_tests_passed


bot = telebot.TeleBot(project_strings.bot_token)
tasks = database.get_tasks()


def web_app_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    web_app = types.WebAppInfo(project_strings.web_app_keyboard_url)
    one_butt = types.KeyboardButton(text=project_strings.keyboard_button_name, web_app=web_app)
    keyboard.add(one_butt)

    return keyboard


def get_text(text, chat_id, username):
    global tasks
    status = database.get_user_status_by_id(chat_id)
    if status is None or status == project_strings.status_default:
        bot.send_message(chat_id, run_code(folder_name=project_strings.folder_name_default, file_name=str(username),
                                           code=text))

    if status.startswith(project_strings.status_waiting_for_task):
        task_name = status[len(project_strings.status_waiting_for_task) + 1:]
        for task in tasks:
            if task.name == task_name:
                selected_task = task
        checker = Checker(selected_task, text, username)
        result = checker.check()
        bot.send_message(chat_id, result)
        if result == project_strings.all_tests_passed:
            database.set_user_status_by_id(chat_id, project_strings.status_default)
        return

    if status.startswith(project_strings.status_waiting_for_selection_task):
        selected_task = project_strings.no_task_name
        for task in tasks:
            if task.name == text:
                selected_task = task
                break
        if selected_task == project_strings.no_task_name:
            bot.send_message(chat_id, project_strings.message_no_task_found)
        else:
            if status == project_strings.status_waiting_for_selection_task:
                bot.send_message(chat_id, selected_task.description + "\nUse this example")
                try:
                    bot.send_message(chat_id, '<pre><code class="language-python">' + selected_task.example +
                                     '</code></pre>', parse_mode='HTML', reply_markup=web_app_keyboard())
                except:
                    bot.send_message(chat_id, selected_task.example,
                                     reply_markup=web_app_keyboard())

                database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task + " " +
                                               selected_task.name)
            else:
                bot.send_message(chat_id, project_strings.test_example)
                database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_test_for + " " +
                                               selected_task.name)

    if status.startswith(project_strings.status_waiting_to_accept_admin_roots):
        request_id = status[len(project_strings.status_waiting_to_accept_admin_roots) + 1:]
        if text == "Y":
            database.give_admin_roots(request_id)
            bot.send_message(request_id, project_strings.message_admin_request_accepted)
            database.set_user_status_by_id(chat_id, project_strings.status_default)
            return
        if text == "N":
            bot.send_message(request_id, project_strings.message_admin_request_declined)
            database.set_user_status_by_id(chat_id, project_strings.status_default)
            return
        bot.send_message(chat_id, project_strings.message_expected_yer_or_no)

    if status == project_strings.status_waiting_for_task_name:
        database.add_task(Task(text))
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_description + " " + text)
        bot.send_message(chat_id, project_strings.message_send_task_description)

    if status.startswith(project_strings.status_waiting_for_task_description):
        task_name = status[len(project_strings.status_waiting_for_task_description) + 1:]
        database.update_task_description(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.message_send_task_example, reply_markup=web_app_keyboard())
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_example + " " + task_name)

    if status.startswith(project_strings.status_waiting_for_task_example):
        task_name = status[len(project_strings.status_waiting_for_task_example) + 1:]
        database.update_task_example(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.done)
        bot.send_message(project_strings.owner_id, "@" + username + " " + project_strings.message_added_task + "\n" +
                         task_name)
        database.set_user_status_by_id(chat_id, project_strings.status_default)
        tasks = database.get_tasks()

    if status.startswith(project_strings.status_waiting_for_test_for):
        task_name = status[len(project_strings.status_waiting_for_test_for) + 1:]
        lines = text.split("\n")[:-1]
        expected_answer = [text.split("\n")[-1]]
        database.add_test_to_task(project_strings.task_prefix + task_name, Test(lines, expected_answer))
        bot.send_message(chat_id, project_strings.done)
        bot.send_message(project_strings.owner_id,
                         "@" + username + " " + project_strings.message_added_test + "\n" + text + "\n" +
                         project_strings.message_to + " " + task_name)
        tasks = database.get_tasks()
        database.set_user_status_by_id(chat_id, project_strings.status_default)


@bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
    bot.reply_to(message, project_strings.start_message, reply_markup=web_app_keyboard())
    new_user = User(message.chat.username, message.chat.id)
    database.add_user(new_user)
    database.set_user_status_by_id(message.chat.id, project_strings.status_default)


@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if database.has_admin_roots(message.chat.id):
        bot.reply_to(message, project_strings.admin_menu)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


@bot.message_handler(commands=['request_roots'])
def request_roots(message):
    bot.send_message(project_strings.owner_id, "@" + message.chat.username + " " +
                     project_strings.message_postfix_admin_roots_request)
    database.set_user_status_by_id(int(project_strings.owner_id), project_strings.status_waiting_to_accept_admin_roots +
                                   " " + str(message.chat.id))


@bot.message_handler(commands=['add_task'])
def adding_task(message):
    if database.has_admin_roots(message.chat.id):
        bot.reply_to(message, project_strings.message_send_task_name)
        database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_task_name)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


def tasks_to_message(message):
    ans = project_strings.message_chose_the_task
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = [types.KeyboardButton(task.name) for task in tasks]
    markup.add(*buttons)
    for task in tasks:
        ans += task.name + "\n"
    bot.reply_to(message, ans, reply_markup=markup)


@bot.message_handler(commands=['add_test'])
def adding_test(message):
    if database.has_admin_roots(message.chat.id):
        tasks_to_message(message)
        database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_selection_task_for_test)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


@bot.message_handler(content_types='web_app_data')
def answer(web_message):
    bot.send_message(web_message.from_user.id, web_message.web_app_data.data)
    get_text(text=web_message.web_app_data.data, chat_id=web_message.from_user.id,
             username=web_message.from_user.username)


@bot.message_handler(commands=['tasks'])
def send_tasks(message):
    tasks_to_message(message)
    database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_selection_task)


@bot.message_handler(content_types=['text'])
def text_input(message):
    get_text(message.text, message.chat.id, message.chat.username)


bot.polling()
