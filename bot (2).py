# -*- coding: utf-8 -*-
"""
Бот магазина Honest Store.
Приветствие + кнопки (Каталог, Доставка, Оплата, Размеры, Возврат, Поддержка)
+ УВЕДОМЛЕНИЯ О ЗАКАЗАХ: при новом заказе владельцу приходит сообщение
  с кнопками «✅ Оплачен» и «🗑 Убрать товар с витрины».

Запуск 24/7 на Railway. Переменные окружения (Railway -> Variables):
  BOT_TOKEN     — токен бота от @BotFather
  SUPABASE_URL  — https://wzeqohefoemixstghlfz.supabase.co
  SUPABASE_KEY  — секретный ключ Supabase (service_role / sb_secret_...)
"""

import os
import time
import threading
import requests
import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")                 # Railway -> Variables
WEBAPP_URL = "https://radiant-dango-bde1af.netlify.app"     # ссылка на приложение
SUPPORT = "Honest_KaS"                                      # username поддержки (без @)
OWNER_ID = 1925395566                                       # твой Telegram ID — сюда летят заказы

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
REST = (SUPABASE_URL + "/rest/v1") if SUPABASE_URL else ""

POLL_SECONDS = 15  # как часто проверять новые заказы

if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN. Добавь переменную окружения BOT_TOKEN с токеном бота.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# --- ТЕКСТЫ РАЗДЕЛОВ ---
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


@bot.message_handler(commands=["id"])
def cmd_id(m):
    # Удобно проверить свой Telegram ID (должен совпадать с OWNER_ID)
    bot.send_message(m.chat.id, "Ваш Telegram ID: <code>%s</code>" % m.chat.id)


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


@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(m):
    bot.send_message(m.chat.id, "Пользуйтесь кнопками ниже 👇", reply_markup=main_keyboard())


# ====================== УВЕДОМЛЕНИЯ О ЗАКАЗАХ ======================

def _supa_headers(extra=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
    if extra:
        h.update(extra)
    return h


def fetch_new_orders():
    r = requests.get(
        REST + "/orders",
        headers=_supa_headers(),
        params={"select": "*", "notified": "eq.false", "order": "id.asc"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def mark_notified(order_id):
    requests.patch(
        REST + "/orders",
        headers=_supa_headers({"Content-Type": "application/json", "Prefer": "return=minimal"}),
        params={"id": "eq." + str(order_id)},
        json={"notified": True},
        timeout=20,
    )


def mark_paid(order_id):
    requests.patch(
        REST + "/orders",
        headers=_supa_headers({"Content-Type": "application/json", "Prefer": "return=minimal"}),
        params={"id": "eq." + str(order_id)},
        json={"status": "paid"},
        timeout=20,
    )


def delete_product(product_id):
    r = requests.delete(
        REST + "/products",
        headers=_supa_headers({"Prefer": "return=minimal"}),
        params={"id": "eq." + str(product_id)},
        timeout=20,
    )
    r.raise_for_status()


def format_order(o):
    lines = ["🛒 <b>Новый заказ №%s</b>" % o.get("id"), ""]
    for it in (o.get("items") or []):
        size = (" (%s)" % it["size"]) if it.get("size") else ""
        lines.append("• %s%s — %s ₽" % (it.get("name", "?"), size, it.get("price", "?")))
    lines.append("")
    lines.append("💰 Итого: <b>%s ₽</b>" % o.get("total", "?"))
    lines.append("")
    lines.append("👤 %s" % (o.get("customer_name") or "—"))
    lines.append("📞 <code>%s</code>" % (o.get("contact") or "—"))
    lines.append("📍 %s" % (o.get("address") or "—"))
    if o.get("comment"):
        lines.append("💬 %s" % o["comment"])
    return "\n".join(lines)


def order_keyboard(o):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Оплачен", callback_data="paid:%s" % o["id"]))
    for it in (o.get("items") or []):
        if it.get("id") is not None:
            name = (it.get("name") or "товар")[:28]
            kb.add(types.InlineKeyboardButton("🗑 Убрать с витрины: %s" % name, callback_data="del:%s" % it["id"]))
    return kb


@bot.callback_query_handler(func=lambda c: True)
def on_callback(c):
    # Только владелец может отмечать оплату и убирать товары
    if c.from_user.id != OWNER_ID:
        bot.answer_callback_query(c.id, "Недоступно")
        return
    try:
        action, _, val = c.data.partition(":")
        if action == "paid":
            mark_paid(val)
            bot.answer_callback_query(c.id, "Отмечено как оплачено ✅")
            try:
                bot.edit_message_text(
                    c.message.html_text + "\n\n✅ <b>ОПЛАЧЕН</b>",
                    c.message.chat.id, c.message.message_id, reply_markup=None,
                )
            except Exception:
                pass
        elif action == "del":
            delete_product(val)
            bot.answer_callback_query(c.id, "Товар убран с витрины 🗑")
            try:
                bot.edit_message_text(
                    c.message.html_text + "\n\n🗑 <b>Товар убран с витрины</b>",
                    c.message.chat.id, c.message.message_id, reply_markup=None,
                )
            except Exception:
                pass
        else:
            bot.answer_callback_query(c.id)
    except Exception as e:
        bot.answer_callback_query(c.id, "Ошибка: %s" % e)


def order_poll_loop():
    if not (REST and SUPABASE_KEY):
        print("Supabase не настроен (SUPABASE_URL/SUPABASE_KEY) — уведомления о заказах ВЫКЛ.")
        return
    print("Уведомления о заказах: ВКЛ. Проверка каждые %s сек." % POLL_SECONDS)
    while True:
        try:
            for o in fetch_new_orders():
                try:
                    bot.send_message(OWNER_ID, format_order(o), reply_markup=order_keyboard(o))
                    mark_notified(o["id"])
                except Exception as e:
                    print("Не смог отправить заказ %s: %s" % (o.get("id"), e))
        except Exception as e:
            print("Ошибка опроса заказов: %s" % e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    print("Bot started.")
    try:
        bot.remove_webhook()
    except Exception:
        pass
    threading.Thread(target=order_poll_loop, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30)
        except Exception as e:
            print("Polling упал, перезапуск через 5 сек: %s" % e)
            time.sleep(5)
