import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
import config
import time

bot = telebot.TeleBot(config.token)

# Initially, scraping process is inactive, IDs and domain are not set
is_scraping = False
start_id = None
end_id = None
selected_domain = None

def fetch_casting_info(casting_id):
    """
    Extracts information from a casting page of the specified domain.
    """
    url = f"https://{selected_domain}/a_{casting_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    elements = soup.find_all("div", class_="col-7 table_value")
    if elements:
        link = url
        name = elements[1].get_text()
        age = elements[2].get_text()
        sex = elements[4].get_text()
        country = elements[9].get_text()
        city = elements[10].get_text()
        return f"Link: {link}\nName: {name}\nAge: {age}\nGender: {sex}\nCountry: {country}\nCity: {city}"
    return None

def is_authorized(message):
    """
    Checks if the user is authorized to use the bot.
    """
    return message.from_user.id == config.authorized_user_id

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Handles the /start command, sending country selection options to the user.
    """
    if not is_authorized(message):
        bot.reply_to(message, "Sorry, you are not authorized to use this bot.")
        return

    send_country_selection(message)

def send_country_selection(message):
    """
    Sends country selection options to the user for domain selection.
    """
    markup = types.InlineKeyboardMarkup()
    ru_button = types.InlineKeyboardButton('Russia', callback_data='select_ru')
    ua_button = types.InlineKeyboardButton('Ukraine', callback_data='select_ua')
    com_button = types.InlineKeyboardButton('International', callback_data='select_com')
    markup.add(ru_button, ua_button, com_button)
    bot.send_message(message.chat.id, "Please select your country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    """
    Handles callback queries from inline buttons for country and control selections.
    """
    global is_scraping, start_id, end_id, selected_domain
    if call.data.startswith('select_'):
        if is_scraping:
            bot.answer_callback_query(call.id, "Cannot change country during active scraping.")
            return
        domain_map = {
            'select_ru': 'acmodasi.ru',
            'select_ua': 'acmodasi.com.ua',
            'select_com': 'www.acmodasi.com'
        }
        selected_domain = domain_map[call.data]
        send_control_buttons(call.message, f"Selected domain: {selected_domain}")
    elif call.data == 'set_start' or call.data == 'set_end':
        if is_scraping:
            bot.answer_callback_query(call.id, "Cannot change ID during active scraping.")
            return
        process_control_buttons(call)
    elif call.data == 'start_scraping':
        if is_scraping:
            bot.answer_callback_query(call.id, "Scraping is already in progress.")
            return
        if start_id is None or end_id is None:
            send_control_buttons(call.message, "Please set both Start and End IDs first.")
        else:
            is_scraping = True
            bot.answer_callback_query(call.id, "Scraping started")
            start_scraping(call.message)
    elif call.data == 'stop_scraping':
        is_scraping = False
        bot.send_message(call.message.chat.id, "Scraping stopped")

def process_control_buttons(call):
    """
    Processes control buttons for setting start and end IDs and starting scraping.
    """
    if call.data == 'set_start':
        msg = bot.send_message(call.message.chat.id, "Please enter the Start ID:")
        bot.register_next_step_handler(msg, process_start_id)
    elif call.data == 'set_end':
        msg = bot.send_message(call.message.chat.id, "Please enter the End ID:")
        bot.register_next_step_handler(msg, process_end_id)
    elif call.data == 'start_scraping':
        if is_scraping:
            bot.send_message(call.message.chat.id, "Scraping is already in progress.")
            return
        if start_id is None or end_id is None:
            send_control_buttons(call.message, "Please set both Start and End IDs first.")
        else:
            is_scraping = True
            bot.answer_callback_query(call.id, "Scraping started")
            start_scraping(call.message)

def send_control_buttons(message, text):
    """
    Sends control buttons to the user for setting IDs and starting scraping.
    """
    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton('Set Start ID', callback_data='set_start')
    end_button = types.InlineKeyboardButton('Set End ID', callback_data='set_end')
    scrape_button = types.InlineKeyboardButton('Start Scraping', callback_data='start_scraping')
    markup.add(start_button, end_button, scrape_button)
    bot.send_message(message.chat.id, text, reply_markup=markup)

def process_id_input(message, setting_id):
    """
    Processes user input for start or end ID and handles invalid input.
    """
    global start_id, end_id
    try:
        id_value = int(message.text)
        if setting_id == 'start':
            start_id = id_value
            bot.send_message(message.chat.id, f"Start ID set to: {start_id}")
        elif setting_id == 'end':
            end_id = id_value
            bot.send_message(message.chat.id, f"End ID set to: {end_id}")
    except ValueError:
        send_control_buttons(message, "Please enter a valid number for ID.")

def process_start_id(message):
    process_id_input(message, 'start')

def process_end_id(message):
    process_id_input(message, 'end')

def start_scraping(message):
    """
    Starts the scraping process and sends the results to the user.
    """
    global is_scraping, start_id, end_id
    casting_id = start_id
    nothing_found = True
    while casting_id <= end_id and is_scraping:
        info = fetch_casting_info(casting_id)
        if info:
            nothing_found = False
            send_scraping_result(message, info)
        time.sleep(1)
        casting_id += 1
    if nothing_found:
        bot.send_message(message.chat.id, "No results found in the specified ID range.")
    is_scraping = False

def send_scraping_result(message, info):
    """
    Sends scraping results with a stop button to the user.
    """
    markup = types.InlineKeyboardMarkup()
    stop_button = types.InlineKeyboardButton('Stop Scraping', callback_data='stop_scraping')
    markup.add(stop_button)
    bot.send_message(message.chat.id, info, reply_markup=markup)

print('Bot successfully launched!')
bot.polling()
