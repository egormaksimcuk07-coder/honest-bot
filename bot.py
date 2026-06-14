# -*- coding: utf-8 -*-
"""
Бот магазина Honest Store.
Приветствие + рабочие кнопки: Каталог, Доставка, Оплата, Размеры, Возврат, Поддержка.
Запуск 24/7 на Railway (или VPS). Токен берётся из переменной окружения BOT_TOKEN.
"""

import os
import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")               # задаётся в Railway -> Variables
WEBAPP_URL = "https://radiant-dango-bde1af.netlify.app"   # ссылка на твоё приложение
SUPPORT = "Honest_KaS"                                    # username поддержки (без @)

if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN. Добавь переменную окружения BOT_TOKEN с токеном бота.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- ТЕКСТЫ РАЗДЕЛОВ (меняй под себя) ---
TXT_DELIVERY = (
    "📦 <b>Доставка</b>\n\n"
    "Отправляем по России и СНГ в день оплаты.\n"
    "Доставка СДЭК до пункта выдачи или курьером.\n"
    "Трек-номер пришлём после отправки."
)
TXT_PAYMENT = (
    "💳 <b>Оплата</b>\n\n"
    "Перевод по СБП:\n"
    "Номер: <code>+7 953 748-64-12</code>\n"
    "Получатель: Король Александр Сергеевич\n"
    "Банк: Т-Банк\n\n"
    "Оформите заказ в приложении и пришлите чек в поддержку @" + SUPPORT + "."
)
TXT_SIZES = (
    "📏 <b>Размеры</b>\n\n"
    "Все замеры указаны в карточке каждого товара.\n"
    "Сомневаетесь в размере — напишите в поддержку, поможем подобрать."
)
TXT_RETURN = (
    "🔄 <b>Возврат / обмен</b>\n\n"
    "Все вещи в единственном экземпляре.\n"
    "По возврату или обмену напишите в поддержку — решим индивидуально."
)


def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🛍 Открыть каталог", web_app=types.WebAppInfo(WEBAPP_URL)))
    kb.add(types.KeyboardButton("📦 Доставка"), types.KeyboardButton("💳 Оплата"))
    kb.add(types.KeyboardButton("📏 Размеры"), types.KeyboardButton("🔄 Возврат/обмен"))
    kb.add(types.KeyboardButton("✍️ Поддержка"))
    return kb


def catalog_inline():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛍 Открыть каталог", web_app=types.WebAppInfo(WEBAPP_URL)))
    return kb


def support_inline():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Написать в поддержку", url="https://t.me/" + SUPPORT))
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(m):
    text = (
        "👋 Добро пожаловать в <b>Honest Store</b> — оригинальная одежда в единственном экземпляре!\n\n"
        "🛍 Нажмите кнопку ниже, чтобы открыть каталог.\n"
        "❓ Вопросы — кнопки внизу или @" + SUPPORT
    )
    bot.send_message(m.chat.id, text, reply_markup=main_keyboard())
    bot.send_message(m.chat.id, "Каталог открывается здесь 👇", reply_markup=catalog_inline())


@bot.message_handler(commands=["help"])
def cmd_help(m):
    bot.send_message(
        m.chat.id,
        "❓ <b>Помощь</b>\n\nКнопки внизу: каталог, доставка, оплата, размеры, возврат.\n"
        "Связь с нами: @" + SUPPORT,
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "📦 Доставка")
def h_delivery(m):
    bot.send_message(m.chat.id, TXT_DELIVERY)


@bot.message_handler(func=lambda m: m.text == "💳 Оплата")
def h_payment(m):
    bot.send_message(m.chat.id, TXT_PAYMENT)


@bot.message_handler(func=lambda m: m.text == "📏 Размеры")
def h_sizes(m):
    bot.send_message(m.chat.id, TXT_SIZES)


@bot.message_handler(func=lambda m: m.text == "🔄 Возврат/обмен")
def h_return(m):
    bot.send_message(m.chat.id, TXT_RETURN)


@bot.message_handler(func=lambda m: m.text == "✍️ Поддержка")
def h_support(m):
    bot.send_message(m.chat.id, "Напишите нам — ответим и поможем оформить заказ:", reply_markup=support_inline())


# Любое прочее сообщение (в т.ч. старые кнопки) — мягко направляем и обновляем меню
@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(m):
    bot.send_message(m.chat.id, "Пользуйтесь кнопками ниже 👇", reply_markup=main_keyboard())


if __name__ == "__main__":
    print("Bot started.")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True, timeout=30)
