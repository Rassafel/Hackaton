import vk_api
import random
import sys

from fuzzywuzzy import fuzz
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from geoposition import GoogleMap
from parsingVk import WallPosts
import threading
import time

user_file = r'vk_user.txt'
bot_file = r'bot_Token.txt'
GROUP_ID = 196299691

keyboard_default = VkKeyboard(one_time=True)

keyboard_default.add_button('Добавить адрес',
                            color=VkKeyboardColor.POSITIVE)
keyboard_default.add_line()
keyboard_default.add_button('Удалить адрес',
                            color=VkKeyboardColor.NEGATIVE)
keyboard_default.add_line()
keyboard_default.add_button(
    'Добавить продукт',
    color=VkKeyboardColor.POSITIVE)
keyboard_default.add_line()
keyboard_default.add_button(
    'Удалить продукт',
    color=VkKeyboardColor.NEGATIVE)

keyboard_yes_no = VkKeyboard(one_time=True)
keyboard_yes_no.add_button('Да',
                           color=VkKeyboardColor.POSITIVE)
keyboard_yes_no.add_button('Нет',
                           color=VkKeyboardColor.NEGATIVE)

users = {}
google_map = GoogleMap()
products = []

with open('data.txt', mode='r', encoding='utf-8') as f:
    for line in f:
        line = (line
                .lower()
                .replace('\n', ' ')
                .replace(',', ' ')
                .replace('.', ' ')
                .replace('\'', ' ')
                .replace('\"', ' ')
                .replace('  ', ' ')
                )
        while line[-1] == ' ':
            line = line[:-1]

        products.append(line)


def fuzzy_text(text: str):
    text = (text
            .lower()
            .replace('\n', ' ')
            .replace(',', ' ')
            .replace('.', ' ')
            .replace('\'', ' ')
            .replace('\"', ' ')
            .replace('  ', ' ')
            )
    if text[-1] == ' ':
        text = text[:-1]
    split = text.split(' ')
    RC = {
        name:
            {
                'text': '',
                'percent': 65
            }
        for name in split
    }

    for item in products:
        for text, data in RC.items():
            vrt = fuzz.ratio(text, item)
            if vrt > data['percent']:
                RC[text]['text'] = item
                RC[text]['percent'] = vrt

    result = list()
    for text, data in RC.items():
        if data['text'] != '':
            result.append(data['text'])
    return result


def randint():
    return random.randint(0, sys.maxsize)


def run_longpoll():
    def write_msg(user_id: int, message: str):
        vk_session.method(method='messages.send',
                          values={'user_id': user_id,
                                  'message': message,
                                  'random_id': randint()})

    def send_keyboard(user_id: int, message: str,
                      keyboard: VkKeyboard):
        vk_session.method(method='messages.send',
                          values={'user_id': user_id,
                                  'message': message,
                                  "keyboard": keyboard.get_keyboard(),
                                  'random_id': randint()})

    def new_user(user_id: int):
        return {
            user_id: {  # id
                'anchor': 'default',
                'addresses': list(),
                'products': list()
            }
        }

    def new_address(name: str, latitude: float,
                    longitude: float):
        return {
            'name': name,  # имя дома для пользователя
            'latitude': latitude,  # широта
            'longitude': longitude,  # долгота
            'distance': 2  # расстояние
        }

    def is_new_user(user_id: int):
        for id, data in users.items():
            if id == user_id:
                return False
        return True

    def add_new_user(user_id: int):
        users.update(new_user(user_id))

    def add_product_to_user(user_id: int, product: str):
        users[user_id]["products"].append(product)

    def add_address_to_user(user_id: int, name: str,
                            latitude: float,
                            longitude: float):
        users[user_id]['addresses'].append(
            new_address(name, latitude, longitude))

    def add_distance(user_id: int, distance: float):
        users[user_id]['addresses'][-1][
            'distance'] = distance

    def set_anchor(user_id: int, anchor: str):
        users[user_id]["anchor"] = anchor

    def get_all_addresses(user_id: int):
        addresses = 'Укажите номер адреса\n'
        count = 1
        for item in users[user_id]['addresses']:
            addresses += f"{count}. {item['name']} ({item['latitude']}, {item['longitude']}) радиус = {item['distance']} км.\n"
            count += 1
        return addresses

    def get_all_products(user_id: int):
        addresses = 'Укажите номер продукта\n'
        count = 1
        for item in users[user_id]['products']:
            addresses += f"{count}. {item}\n"
            count += 1
        return addresses

    def delete_address(user_id: int, id_address: int):
        users[user_id]["addresses"].pop(id_address)

    def delete_product(user_id: int, id_product: int):
        users[user_id]["products"].pop(id_product)

    def get_address_from_text(text: str):
        result, point = google_map.location_point_from_text(
            text)
        return result, point['lat'], point['lng']

    def work_with_address(event: vk_api.longpoll.Event,
                          cur_anchor: str):
        message = event.text.lower()
        user_id = event.user_id

        #  Ожидание ответа из основного диалога
        if cur_anchor == 'wait_default':
            if message == 'добавить адрес':
                set_anchor(user_id, "wait_add_address")
                write_msg(user_id,
                          'Введите адрес, например: \nг.Самара, ул.Молодогвардейская, дом 244')
                return True

            elif message == "удалить адрес":
                if len(users[user_id]['addresses']) == 0:
                    set_anchor(user_id, 'wait_default')
                    send_keyboard(user_id,
                                  "У вас нет адресов",
                                  keyboard_default)
                    return True
                set_anchor(user_id, "wait_rem_address")
                write_msg(user_id,
                          get_all_addresses(user_id))
                return True

        #  Ожидание адреса на добавление
        elif cur_anchor == "wait_add_address":
            if message is None:
                set_anchor(user_id, 'wait_default')
                send_keyboard(user_id, "Ошибка!",
                              keyboard_default)
                return True
            location, latitude, longitude = get_address_from_text(
                message)
            add_address_to_user(user_id, location, latitude,
                                longitude)
            set_anchor(user_id, "wait_address_range")
            write_msg(user_id, "Введите радиус поиска, км")
            return True

        #  Ожидание радиуса вокруг адреса
        elif cur_anchor == 'wait_address_range':
            message = message.replace(',', '.')
            distance = float(message)
            if distance is None:
                set_anchor(user_id, 'wait_default')
                send_keyboard(user_id,
                              "Указано неверно расстояние!",
                              keyboard_default)
                return True
            set_anchor(user_id, "wait_add_address_loop")
            add_distance(user_id, distance)
            send_keyboard(user_id,
                          'Хотите ввести еще адрес?',
                          keyboard_yes_no)
            return True

        #  Ожидание ответа на повторение
        elif cur_anchor == "wait_add_address_loop":
            if message == "нет":
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id, "Готово!",
                              keyboard=keyboard_default)
                return True

            elif message == 'да':
                set_anchor(user_id, "wait_add_address")
                write_msg(user_id,
                          'Введите адрес, например: \nг.Самара, ул.Молодогвардейская, дом 244')
                return True

        #  Ожидание индекста для удаления адреса
        elif cur_anchor == 'wait_rem_address':
            index = int(message)
            if not (0 < index < len(
                    users[user_id]['addresses']) + 1):
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id,
                              "Неверный индекс!",
                              keyboard=keyboard_default)
                return True
            delete_address(user_id, index - 1)
            set_anchor(user_id, "wait_rem_address_loop")
            send_keyboard(user_id,
                          'Хотите удалить еще адрес?',
                          keyboard_yes_no)
            return True

        #  Ожидание ответа на повторение
        elif cur_anchor == "wait_rem_address_loop":
            if message == "нет":
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id, "Готово!",
                              keyboard=keyboard_default)
                return True

            elif message == 'да':
                if len(users[user_id]['addresses']) == 0:
                    set_anchor(user_id, 'wait_default')
                    send_keyboard(user_id,
                                  "У вас нет адресов",
                                  keyboard_default)
                    return True
                set_anchor(user_id, "wait_rem_address")
                write_msg(user_id,
                          get_all_addresses(user_id))
                return True

        return False

    def work_with_products(event: vk_api.longpoll.Event,
                           cur_anchor: str):
        message = event.text.lower()
        user_id = event.user_id

        #  Ожидание ответа из основного диалога
        if cur_anchor == 'wait_default':
            if message == 'добавить продукт':
                set_anchor(user_id, "wait_add_product")
                write_msg(user_id,
                          'Введите продукт, например: \nяблоко')
                return True

            elif message == "удалить продукт":
                if len(users[user_id]['products']) == 0:
                    set_anchor(user_id, 'wait_default')
                    send_keyboard(user_id,
                                  "Список продуктов пуст",
                                  keyboard_default)
                    return True
                set_anchor(user_id, "wait_rem_product")
                write_msg(user_id,
                          get_all_products(user_id))
                return True

        #  Ожидание продукта на добавление
        elif cur_anchor == "wait_add_product":
            if message is None:
                set_anchor(user_id, 'wait_default')
                send_keyboard(user_id, "Ошибка!",
                              keyboard_default)
                return True

            product = fuzzy_text(message)
            if len(product) == 0 or product[0] == '':
                set_anchor(user_id, 'wait_default')
                send_keyboard(user_id, "Ошибка!",
                              keyboard_default)
                return True

            add_product_to_user(user_id, product[0])
            send_keyboard(user_id,
                          'Хотите добавить еще продукт?',
                          keyboard_yes_no)
            set_anchor(user_id, "wait_add_product_loop")
            return True

        #  Ожидание ответа на повторение
        elif cur_anchor == "wait_add_product_loop":
            if message == "нет":
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id, "Готово!",
                              keyboard=keyboard_default)
                return True

            elif message == 'да':
                set_anchor(user_id, "wait_add_product")
                write_msg(user_id,
                          'Введите продукт, например: \nяблоко')
                return True

        #  Ожидание индекста для удаления адреса
        elif cur_anchor == 'wait_rem_product':
            index = int(message)
            if not (0 < index < len(
                    users[user_id]['products']) + 1):
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id,
                              "Неверный индекс!",
                              keyboard=keyboard_default)
                return True
            delete_product(user_id, index - 1)
            set_anchor(user_id, "wait_rem_product_loop")
            send_keyboard(user_id,
                          'Хотите удалить еще продукт?',
                          keyboard_yes_no)
            return True

        #  Ожидание ответа на повторение
        elif cur_anchor == "wait_rem_product_loop":
            if message == "нет":
                set_anchor(user_id, "wait_default")
                send_keyboard(event.user_id, "Готово!",
                              keyboard=keyboard_default)
                return True

            elif message == 'да':
                if len(users[user_id]['addresses']) == 0:
                    set_anchor(user_id, 'wait_default')
                    send_keyboard(user_id,
                                  "Список продуктов пуст",
                                  keyboard_default)
                    return True
                set_anchor(user_id, "wait_rem_product")
                write_msg(user_id,
                          get_all_addresses(user_id))
                return True

        return False

    def input_message(event: vk_api.longpoll.Event):
        user_id = event.user_id
        if is_new_user(user_id):
            add_new_user(user_id)
        print(users)
        cur_anchor = users[user_id]['anchor']
        if cur_anchor == 'default':
            send_keyboard(event.user_id,
                          "Доброго времени суток!",
                          keyboard=keyboard_default)
            set_anchor(user_id, "wait_default")

        if work_with_address(event, cur_anchor):
            pass

        if work_with_products(event, cur_anchor):
            pass

        pass

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            print(event.attachments)
            input_message(event)


def run_parsing():
    groups = []

    def request_new_posts():
        """
        Запрос на проверку ленты.
        :return:
        """
        posts = list()
        for group in groups:
            for post in group.get_wall_post():
                posts.append(post)
        return posts

    def write_mailing(user_id, message):
        """
        Рассылка новых постов.
        :param user_id:
        :param message:
        :return:
        """
        vk_session.method(method='messages.send',
                          values={
                              'user_id': user_id,
                              'attachment': message,
                              'random_id': randint()
                          }
                          )

    def condatins_in_list(list1: list, list2: list):
        for item in list1:
            if item in list2:
                return True
        return False

    def extract_list_products(text: str):
        return fuzzy_text(text)

    def get_point(var1: float, var2: float):
        return {
            'lat': var1,
            'lng': var2
        }

    with open(file=user_file, mode='r', encoding='utf-8') as f:
        login = f.readline().replace("\n", '')
        password = f.readline().replace("\n", '')
    user_vk = vk_api.VkApi(login=login, password=password)
    user_vk.auth()

    with open(r'group_id.txt', 'r', encoding='utf-8') as f:
        for line in f:
            groups.append(WallPosts(int(line), user_vk))
    while True:
        time.sleep(30)
        list_posts = request_new_posts()
        if list_posts is None:
            continue
        for post in list_posts:
            print(post)
            list_products = extract_list_products(post['text'])
            post_point = google_map.location_to_point(post['text'])

            for user, data in users.items():
                if condatins_in_list(data['products'], list_products):
                    for location in data['addresses']:
                        user_point = (location['latitude'], location['longitude'])
                        if google_map.distance(post_point, user_point) < \
                                location['distance']:
                            write_mailing(user,
                                          f'wall{post["owner_id"]}_{post["id"]}')
                            break


if __name__ == '__main__':
    with open(file=bot_file, mode='r', encoding='utf-8') as f:
        TOKEN = f.readline()


    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()

    longpoll = VkLongPoll(vk_session, group_id=GROUP_ID)
    run1 = threading.Thread(target=run_longpoll)

    run2 = threading.Thread(target=run_parsing)

    run1.start()
    run2.start()
