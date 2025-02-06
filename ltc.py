import asyncio
import json
import requests
from bitcoinlib.keys import Key
from sqlalchemy.future import select
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bitcoinlib.transactions import Transaction
from bitcoinlib.networks import Network
from database import PrivateKeyAddress, session_factory, create_tables
from messages import telegram_message, address_not_found_message
import time
from requests.auth import HTTPBasicAuth

# Загружаем конфигурацию
with open("config.json", "r") as config_file:
    config = json.load(config_file)

BOT_TOKEN = config["bot"]["token"]
CHAT_IDS = config["bot"]["chat_id"]

FEE_PROCENT = config["transaction"]["fee_procent"]
SEND_AMOUNT_PROCENT = config["transaction"]["send_amount_procent"]

TO_ADDRESS = config["address"]["to_address"]
RPC_URL = config["rpc"]["url"]
CLEAR_INTERVAL_HOURS = config["scheduler"]["clear_interval_hours"]

# Хранилище данных в памяти
private_key_address_map = {}
processed_tx_hashes = set()

RPC_USER = "rpcuser"
RPC_PASSWORD = "rpcpassword"


# Загрузка адресов и приватных ключей из бд в память (из памяти данные получать быстрее чем из бд)
async def load_data_into_memory():
    global private_key_address_map
    async with session_factory() as session:
        async with session.begin():
            # Загрузка данных PrivateKeyAddress в память
            result = await session.execute(select(PrivateKeyAddress))
            private_key_address_map = {
                entry.address: entry.private_key for entry in result.scalars()
            }


# Функция отправки запросов на ноду
async def request(method, params):
    try:
        url = RPC_URL
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        response = await asyncio.to_thread(
            lambda: requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=HTTPBasicAuth(RPC_USER, RPC_PASSWORD)
            )
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"Exception in request: {e}")
        return None


# Проверка пендинг транзакций на наличие в выходах наших адресов и вывод монет с этих адресов
async def process_transaction(tx_hash):
    global processed_tx_hashes, private_key_address_map

    try:
        # Запрос на получение данных о транзакции по ее хешу
        result = await request("getrawtransaction", [tx_hash, True])

        # Если данных нет - пропускаем
        if not result or "result" not in result:
            return

        # Запись данных транзакции в переменную
        transaction_data = result["result"]

        # Добавление хеша транзакции в память как обработанную, чтобы больше ее не проверять
        processed_tx_hashes.add(tx_hash)

        # Собирает выходы из транзакции, чтобы получить адрес получателя и баланс
        for output in transaction_data.get("vout", []):
            try:
                script_pub_key = output.get("scriptPubKey", {})
                # Получение адреса получателя
                addresses = script_pub_key.get("addresses")
                address = addresses[0] if addresses else None
                # Получение суммы отправки
                ltc_value = output.get("value", 0.0)
                # Перевод суммы в сатоши
                amount = int(ltc_value * 1e8)
                # Получение индекса выхода
                n_index = output.get("n")

                # Если адрес получателя есть в базе данных (адреса из базы заливаются в память при запуске софта)
                if address in private_key_address_map:
                    # По адресу из базы данных находим приватный ключ от этого адреса (тоже в базе данных)
                    private_key_db = private_key_address_map[address]
                    private_key = Key(import_key=private_key_db, network='litecoin')  # Явно указываем сеть

                    try:
                        # Рассчитываем сумму отправки и комиссию
                        send_amount = int(amount * SEND_AMOUNT_PROCENT)
                        fee = int(amount * FEE_PROCENT)

                        # Создание транзакции
                        tx = Transaction(network=Network('litecoin'), replace_by_fee=False)
                        # Добавление входов
                        tx.add_input(prev_txid=tx_hash, output_n=n_index, value=amount, address=address,
                                     sequence=0xFFFFFFFE)
                        # Добавление выходов
                        tx.add_output(address=TO_ADDRESS, value=send_amount)
                        # Подписание транзакции
                        tx.sign(private_key)
                        # Подписанная транзакция в hex
                        sign = tx.as_hex()
                        # Отправка hex транзакции в блокчейн на обработку
                        result_send = await request("sendrawtransaction", [str(sign)])

                        await telegram_message(BOT_TOKEN, CHAT_IDS, tx_hash, address, private_key, amount, n_index, send_amount, fee, sign, result_send)

                    except Exception as e:
                        print(f"Error during transaction processing: {e}")
                else:
                    log_message = await address_not_found_message(tx_hash, address, amount, n_index)
                    print(log_message)
            except Exception as e:
                print(f"Error processing output: {e}")
    except Exception as e:
        print(f"Error processing transaction {tx_hash}: {e}")


# Получение списка пендинг транзакций с учетом их появления в сети и наличием в памяти как уже проверенных
async def checkmem():
    while True:
        try:
            print("Начинаем получение списка транзакций")
            method = "getrawmempool"
            params = [True, False]
            # Отправка запроса на ноду для получения списка транзакций в mempool
            result = await request(method, params)

            if result and "result" in result:
                tx_data = result["result"]
                print(f"Общее количество транзакций в пуле: {len(tx_data)}")

                # Получаем текущее время в формате Unix timestamp
                current_time = int(time.time())

                # Объект для хранения всех транзакций с подходящим под критерий времени создания
                recent_tx_hashes = []

                # Фильтруем транзакции, оставляя только те, которые были сделаны в последний час
                for tx_hash, tx_info in tx_data.items():
                    # время транзакции (Unix timestamp)
                    tx_time = tx_info["time"]
                    # проверяем, было ли это в последние 3600 секунд (1 час)
                    if current_time - tx_time <= 3600:
                        recent_tx_hashes.append(tx_hash)

                print(f"Количество транзакций за последний час: {len(recent_tx_hashes)}")

                # Убираем из списка транзакций те, которые уже были обработаны
                recent_tx_hashes = [tx_hash for tx_hash in recent_tx_hashes if tx_hash not in processed_tx_hashes]
                print(f"Оставшиеся транзакции после исключения обработанных: {len(recent_tx_hashes)}")

                # Обрабатываем транзакции
                if recent_tx_hashes:
                    tasks = [process_transaction(tx_hash) for tx_hash in recent_tx_hashes]
                    await asyncio.gather(*tasks)

                    processed_tx_hashes.update(recent_tx_hashes)
                    print(f"Обработано {len(recent_tx_hashes)} транзакций, добавлено в processed_tx_hashes.")
                else:
                    print("Нет новых транзакций для обработки.")
            else:
                print("Не удалось получить список транзакций.")
        except Exception as e:
            print(f"Error in checkmem: {e}")


# Функция очистки памяти (нужно, что бы при долгой работе память не забилась совсем старыми транзакциями)
async def clear_memory():
    global processed_tx_hashes
    try:
        processed_tx_hashes.clear()
        print("Память с обработанными хэшами очищена.")
    except Exception as e:
        print(f"Ошибка при очистке памяти: {e}")


async def main():
    try:
        scheduler = AsyncIOScheduler()
        # Добавляем в scheduler функцию для очистки памяти с интервалом указанным в CLEAR_INTERVAL_HOURS
        scheduler.add_job(clear_memory, 'interval', hours=CLEAR_INTERVAL_HOURS)
        scheduler.start()

        await create_tables()
        await load_data_into_memory()

        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

        await checkmem()
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
