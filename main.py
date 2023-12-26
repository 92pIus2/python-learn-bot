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
        if len(result) == 0:
            result = project_strings.done
        return str(result)
    except subprocess.CalledProcessError as e:
        return "\n" + project_strings.runtime_error + "\n\n" + e.output
    except subprocess.TimeoutExpired:
        return project_strings.time_limit


class Checker:
    def __init__(self, task, code, username, id):
        self.task = task
        self.code = code
        self.username = username
        self.id = str(id)

    def check(self):
        for test in self.task.tests:
            try:
                result = run_code(folder_name=self.task.func_name, file_name=self.username,
                                  code=self.code + "\nprint(" + self.task.func_name + "(" + test.to_input() + "))")
            except:
                result = run_code(folder_name=self.task.func_name, file_name=self.id,
                                  code=self.code + "\nprint(" + self.task.func_name + "(" + test.to_input() + "))")
                if not test.check_test(result):
                    return project_strings.error_on_test + "\n" + str(
                        test.to_input()) + "\n" + project_strings.expected + \
                        str(test.answer) + "\n" + project_strings.found + str(result)
        return project_strings.all_tests_passed


bot = telebot.TeleBot(project_strings.bot_token)
tasks = database.get_tasks()


def web_app_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app = types.WebAppInfo(project_strings.web_app_keyboard_url)
    one_butt = types.KeyboardButton(text=project_strings.keyboard_button_name, web_app=web_app)
    keyboard.add(one_butt)

    return keyboard


def send_code(chat_id, code, markup=None):
    try:
        bot.send_message(chat_id, '<pre><code class="language-python">' + code +
                         '</code></pre>', parse_mode='HTML', reply_markup=markup)
    except:
        bot.send_message(chat_id, code,
                         reply_markup=markup)


def get_text(text, chat_id, username):
    global tasks
    status = database.get_user_status_by_id(chat_id)

    # Running user's code
    if status is None or status == project_strings.status_default:
        bot.send_message(chat_id, run_code(folder_name=project_strings.folder_name_default, file_name=str(username),
                                           code=text))

    # Test user's code for some task
    if status.startswith(project_strings.status_waiting_for_task):
        task_name = status[len(project_strings.status_waiting_for_task) + 1:]
        for task in tasks:
            if task.name == task_name:
                selected_task = task
        if text == project_strings.give_up:
            bot.send_message(chat_id, project_strings.message_author_solution)
            send_code(chat_id, selected_task.solution)
            return
        checker = Checker(selected_task, text, username, chat_id)
        result = checker.check()
        bot.send_message(chat_id, result)
        if result == project_strings.all_tests_passed:
            database.set_user_status_by_id(chat_id, project_strings.status_default)
        return

    # Selection task menu (user or admin)
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
                bot.send_message(chat_id, selected_task.description + "\n" + project_strings.message_use_this_example)
                markup = web_app_keyboard()
                give_up_button = types.KeyboardButton(text=project_strings.give_up)
                markup.add(give_up_button)
                send_code(chat_id, selected_task.example, markup)
                bot.send_message(chat_id, project_strings.message_after_example)
                database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task + " " +
                                               selected_task.name)
            else:
                bot.send_message(chat_id, project_strings.test_example + "\n" + selected_task.variables)
                database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_test_for + " " +
                                               selected_task.name)

    # Request admin roots
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

    # Name for new task
    if status == project_strings.status_waiting_for_task_name:
        selected_task = project_strings.no_task_name
        for task in tasks:
            if task.name == text:
                selected_task = task
                break
        if selected_task != project_strings.no_task_name:
            bot.send_message(chat_id, project_strings.message_task_already_exist)
        else:
            database.add_task(Task(text))
            database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_description + " " + text)
            bot.send_message(chat_id, project_strings.message_send_task_description)

    # Description for new task
    if status.startswith(project_strings.status_waiting_for_task_description):
        task_name = status[len(project_strings.status_waiting_for_task_description) + 1:]
        database.update_task_description(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.message_send_task_func_name)
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_func_name + " " + task_name)

    # func_name for new task
    if status.startswith(project_strings.status_waiting_for_task_func_name):
        task_name = status[len(project_strings.status_waiting_for_task_func_name) + 1:]
        database.update_task_func_name(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.message_send_task_variables)
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_variables + " " + task_name)

    # Variables for new task
    if status.startswith(project_strings.status_waiting_for_task_variables):
        task_name = status[len(project_strings.status_waiting_for_task_variables) + 1:]
        database.update_task_variables(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.message_send_task_example, reply_markup=web_app_keyboard())
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_example + " " + task_name)

    # Example for new task
    if status.startswith(project_strings.status_waiting_for_task_example):
        task_name = status[len(project_strings.status_waiting_for_task_example) + 1:]
        database.update_task_example(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.message_send_task_solution, reply_markup=web_app_keyboard())
        database.set_user_status_by_id(chat_id, project_strings.status_waiting_for_task_solution + " " + task_name)

    # Solution for new task
    if status.startswith(project_strings.status_waiting_for_task_solution):
        task_name = status[len(project_strings.status_waiting_for_task_solution) + 1:]
        database.update_task_solution(project_strings.task_prefix + task_name, text)
        bot.send_message(chat_id, project_strings.done)
        bot.send_message(project_strings.owner_id, "@" + username + " " + project_strings.message_added_task + "\n" +
                         task_name)
        database.set_user_status_by_id(chat_id, project_strings.status_default)
        tasks = database.get_tasks()

    # Adding new test
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


# Main information
@bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
    bot.reply_to(message, project_strings.start_message, reply_markup=web_app_keyboard())
    new_user = User(message.chat.id, message.chat.username)
    database.add_user(new_user)
    database.set_user_status_by_id(message.chat.id, project_strings.status_default)


# Admin panel
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if database.has_admin_roots(message.chat.id):
        bot.reply_to(message, project_strings.admin_menu)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


# Request admin roots
@bot.message_handler(commands=['request_roots'])
def request_roots(message):
    try:
        bot.send_message(project_strings.owner_id, "@" + message.chat.username + " " +
                         project_strings.message_postfix_admin_roots_request)
    except:
        bot.send_message(project_strings.owner_id, str(message.chat.id) + " " +
                         project_strings.message_postfix_admin_roots_request)
    database.set_user_status_by_id(int(project_strings.owner_id), project_strings.status_waiting_to_accept_admin_roots +
                                   " " + str(message.chat.id))


# Add new task
@bot.message_handler(commands=['add_task'])
def adding_task(message):
    if database.has_admin_roots(message.chat.id):
        bot.reply_to(message, project_strings.message_send_task_name)
        database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_task_name)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


# List of tasks to message
def tasks_to_message(message):
    ans = "<b>" + project_strings.message_chose_the_task + "</b>" + "\n"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = [types.KeyboardButton(task.name) for task in tasks]
    markup.add(*buttons)
    for task in tasks:
        ans += task.name + "\n"
    bot.send_message(message.chat.id, ans, reply_markup=markup, parse_mode='HTML')


# New test
@bot.message_handler(commands=['add_test'])
def adding_test(message):
    if database.has_admin_roots(message.chat.id):
        tasks_to_message(message)
        database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_selection_task_for_test)
    else:
        bot.reply_to(message, project_strings.no_admin_roots)


# Custom input
@bot.message_handler(content_types='web_app_data')
def answer(web_message):
    send_code(web_message.from_user.id, web_message.web_app_data.data)
    get_text(text=web_message.web_app_data.data, chat_id=web_message.from_user.id,
             username=web_message.from_user.username)


# Get list of tasks
@bot.message_handler(commands=['tasks'])
def send_tasks(message):
    tasks_to_message(message)
    database.set_user_status_by_id(message.chat.id, project_strings.status_waiting_for_selection_task)


# Some text message
@bot.message_handler(content_types=['text'])
def text_input(message):
    get_text(message.text, message.chat.id, message.chat.username)


bot.polling()
