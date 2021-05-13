import time

import threading

import telebot
import schedule
from prettytable import PrettyTable
import datetime

TOKEN = '1784529913:AAFdsmkfLgd_0_PknR0Hv8tmZRskpkt32Sk'
BASE_DATE = datetime.datetime(year=2000, month=1, day=1)


class Timetable:
    def __init__(self):
        self.__actions = []

    @property
    def actions(self):
        return self.__actions

    def current(self):
        cur_time = datetime.datetime.now().time()
        ind = 0
        ans = []
        while ind < len(self.actions) and self.actions[ind][0] < cur_time:
            ind += 1
        for i in self.actions:
            if i[0] == self.actions[max(ind - 1, 0)][0]:
                ans.append(i)
        return ans

    def set(self, text: str):
        self.actions.clear()
        text = text.split(';')
        for i in text:
            i = i.strip()
            if not i:
                continue
            t, action = i.split()[0], ' '.join(i.split()[1:])
            if not action:
                raise ValueError
            t = datetime.datetime.strptime(t, '%H:%M').time()
            self.actions.append((t, action))
        self.__actions.sort()

    def make_table(self, cur=False):
        res = PrettyTable(["Время", "Событие"])
        if not cur:
            for i in self.actions:
                res.add_row([str(i[0])[:-3], i[1]])
        else:
            for i in self.current():
                res.add_row([str(i[0])[:-3], i[1]])
        return res.get_string()


class Bot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        msg_handler = dict(
            function=lambda msg, obj=self: obj.get_text_msg(msg),
            filters=dict(
                content_types=["text"],
            )
        )
        query_handler = dict(
            function=lambda call, obj=self: obj.query_handler(call),
            filters=dict()
        )
        self.bot.add_message_handler(msg_handler)
        self.bot.add_callback_query_handler(query_handler)
        self.tt = Timetable()
        self.users = set()

    def sub(self, user):
        self.users.add(user)

    def unsub(self, user):
        if user in self.users:
            self.users.remove(user)

    def query_handler(self, call: telebot.types.CallbackQuery):
        self.bot.answer_callback_query(callback_query_id=call.id, text='Как скажете')
        answer = ''
        if call.data == '1':
            answer = 'Подписал на уведомления'
            self.sub(call.from_user.id)
        elif call.data == '2':
            answer = 'Отписал от уведомлений'
            self.unsub(call.from_user.id)
        self.bot.send_message(call.message.chat.id, answer)
        self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

    # @self.bot.message_handler(content_types=['text'])
    def get_text_msg(self, message: telebot.types.Message):
        from_id = message.from_user.id
        # print(message.text, from_id)
        reply_markup = telebot.types.ReplyKeyboardMarkup(True)
        reply_markup.row('/help', '/timetable', '/now')
        reply_markup.row('/sub', '/issub', '/unsub')
        if message.text.startswith('/set'):
            # gelya sets timetable
            try:
                self.tt.set(' '.join(message.text.split()[1:]))
                self.bot.send_message(from_id, 'Запомнил новое расписание')
                self.set_tt()
            except Exception as e:
                print(e, e.__class__.__name__)
                self.bot.send_message(from_id, 'Ошибка в формате. Правильный **time1 task1; time2 task2;...**\n'
                                               'Время в формате HH:MM.',
                                      parse_mode='Markdown')
        elif message.text.startswith('/help'):
            self.bot.send_message(from_id,
                                  '**/help** Выводит это сообщение\n'
                                  '**/sub** Подписывает на уведомления\n'
                                  '**/issub** Пишет, подписаны ли вы, на уведомления\n'
                                  '**/unsub** Отписывает от уведомлений\n'
                                  '**/timetable** Выводит расписание\n'
                                  '**/now** Выводит текущее мероприятие\n',
                                  reply_markup=reply_markup,
                                  parse_mode='Markdown')
        elif message.text.startswith('/timetable'):
            # print timetable
            self.bot.send_message(from_id, f'```\n{self.tt.make_table()}\n```', parse_mode='Markdown',
                                  reply_markup=reply_markup)
        elif message.text.startswith('/now'):
            # print current action
            self.bot.send_message(from_id, f'```\n{self.tt.make_table(cur=True)}\n```', parse_mode='Markdown',
                                  reply_markup=reply_markup)
        elif message.text == '/sub':
            self.bot.send_message(from_id, 'Подписал на уведомления о событиях', reply_markup=reply_markup)
            self.sub(from_id)
        elif message.text == '/unsub':
            try:
                self.users.remove(from_id)
                self.bot.send_message(from_id, 'Отписал от уведомлений о событиях', reply_markup=reply_markup)
            except KeyError:
                self.bot.send_message(from_id, 'Вы не были подписаны на уведомления', reply_markup=reply_markup)
            except Exception as e:
                self.bot.send_message(from_id, f'Тут ошибка, чтобы я завтра ее пофиксил (бот теперь не работает лол): '
                                               f'{e} {e.__class__.__name__}')
                print(e, e.__class__.__name__)
        elif message.text == '/issub':
            markup = telebot.types.InlineKeyboardMarkup()
            if from_id in self.users:
                markup.add(telebot.types.InlineKeyboardButton(text='Отписаться', callback_data=2))
                self.bot.send_message(from_id, 'Вы подписаны на уведомления', reply_markup=markup)
            else:
                markup.add(telebot.types.InlineKeyboardButton(text='Подписаться', callback_data=1))
                self.bot.send_message(from_id, 'Вы не подписаны на уведомления', reply_markup=markup)

    def send_action(self, user, text):
        self.bot.send_message(user, text)

    def send_actions(self, text):
        for i in self.users:
            self.send_action(i, text)

    def set_tt(self):
        schedule.jobs.clear()
        for i, txt in self.tt.actions:
            date1 = (datetime.datetime.combine(BASE_DATE, i) - datetime.timedelta(minutes=30)).time()
            schedule.every().day.at(str(i)[:-3]).do(self.send_actions, f'Начинается {txt}!')
            schedule.every().day.at(str(date1)[:-3]).do(self.send_actions, f'{txt} начнется через 30 минут!')

    @staticmethod
    def notifications():
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        t1 = threading.Thread(target=self.bot.polling)
        t2 = threading.Thread(target=self.notifications)
        t1.start()
        t2.start()
        t1.join()
        t2.join()


def main():
    bot = Bot(TOKEN)
    bot.start()


if __name__ == '__main__':
    main()
