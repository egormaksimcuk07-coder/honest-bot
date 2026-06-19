# -*- coding: utf-8 -*-
"""
Бот магазина Honest Store.
Кнопки разделов + УВЕДОМЛЕНИЯ О ЗАКАЗАХ.
При новом заказе владельцу приходит сообщение с кнопками:
  ✅ Подтвердить        — убирает товар(ы) с витрины и ставит заказу статус "подтверждён"
  ❌ Аннулировать заказ — удаляет заявку (у клиента заказ пропадает)
"""

import os
import time
import threading
import requests
import telebot
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = "https://honeststore.netlify.app/?v=4"
SUPPORT = "Honest_KaS"
OWNER_ID = 1925395566

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
REST = (SUPABASE_URL + "/rest/v1") if SUPABASE_URL else ""
POLL_SECONDS = 15

if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

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
    bot.send_message(m.chat.id, "❓ Кнопки внизу. Связь: @" + SUPPORT, reply_markup=main_keyboard())


@bot.message_handler(commands=["id"])
def cmd_id(m):
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
    bot.send_message(m.chat.id, "Напишите нам:", reply_markup=support_inline())


@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback(m):
    bot.send_message(m.chat.id, "Пользуйтесь кнопками ниже 👇", reply_markup=main_keyboard())


# ===== УВЕДОМЛЕНИЯ О ЗАКАЗАХ =====

def _h(extra=None):
    h = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
    if extra:
        h.update(extra)
    return h


def fetch_new_orders():
    r = requests.get(REST + "/orders", headers=_h(),
                     params={"select": "*", "notified": "eq.false", "order": "id.asc"}, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_order(oid):
    r = requests.get(REST + "/orders", headers=_h(),
                     params={"select": "*", "id": "eq." + str(oid)}, timeout=20)
    r.raise_for_status()
    rows = r.json()
    return rows[0] if rows else None


def mark_notified(oid):
    requests.patch(REST + "/orders", headers=_h({"Content-Type": "application/json", "Prefer": "return=minimal"}),
                   params={"id": "eq." + str(oid)}, json={"notified": True}, timeout=20)


def set_status(oid, status):
    requests.patch(REST + "/orders", headers=_h({"Content-Type": "application/json", "Prefer": "return=minimal"}),
                   params={"id": "eq." + str(oid)}, json={"status": status}, timeout=20)


def delete_order(oid):
    r = requests.delete(REST + "/orders", headers=_h({"Prefer": "return=minimal"}),
                        params={"id": "eq." + str(oid)}, timeout=20)
    r.raise_for_status()


def delete_product(pid):
    r = requests.delete(REST + "/products", headers=_h({"Prefer": "return=minimal"}),
                        params={"id": "eq." + str(pid)}, timeout=20)
    r.raise_for_status()


def format_order(o):
    lines = ["🛒 <b>Новый заказ №%s</b>" % o.get("id"), ""]
    for it in (o.get("items") or []):
        size = (" (%s)" % it["size"]) if it.get("size") else ""
        lines.append("• %s%s — %s ₽" % (it.get("name", "?"), size, it.get("price", "?")))
    lines += ["", "💰 Итого: <b>%s ₽</b>" % o.get("total", "?"), "",
              "👤 %s" % (o.get("customer_name") or "—"),
              "📞 <code>%s</code>" % (o.get("contact") or "—"),
              "📍 %s" % (o.get("address") or "—")]
    if o.get("comment"):
        lines.append("💬 %s" % o["comment"])
    return "\n".join(lines)


def order_keyboard(o):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm:%s" % o["id"]))
    kb.add(types.InlineKeyboardButton("❌ Аннулировать заказ", callback_data="cancel:%s" % o["id"]))
    return kb


@bot.callback_query_handler(func=lambda c: True)
def on_callback(c):
    if c.from_user.id != OWNER_ID:
        bot.answer_callback_query(c.id, "Недоступно")
        return
    try:
        action, _, val = c.data.partition(":")
        if action == "confirm":
            o = fetch_order(val)
            if o:
                for it in (o.get("items") or []):
                    if it.get("id") is not None:
                        try:
                            delete_product(it["id"])
                        except Exception:
                            pass
                set_status(val, "confirmed")
            bot.answer_callback_query(c.id, "Заказ подтверждён ✅")
            try:
                bot.edit_message_text(c.message.html_text + "\n\n✅ <b>ПОДТВЕРЖДЁН</b> · товар убран с витрины",
                                      c.message.chat.id, c.message.message_id, reply_markup=None)
            except Exception:
                pass
        elif action == "cancel":
            delete_order(val)
            bot.answer_callback_query(c.id, "Заказ аннулирован ❌")
            try:
                bot.edit_message_text(c.message.html_text + "\n\n❌ <b>АННУЛИРОВАН</b>",
                                      c.message.chat.id, c.message.message_id, reply_markup=None)
            except Exception:
                pass
        else:
            bot.answer_callback_query(c.id)
    except Exception as e:
        bot.answer_callback_query(c.id, "Ошибка: %s" % e)


def order_poll_loop():
    if not (REST and SUPABASE_KEY):
        print("Supabase не настроен — уведомления ВЫКЛ.")
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
