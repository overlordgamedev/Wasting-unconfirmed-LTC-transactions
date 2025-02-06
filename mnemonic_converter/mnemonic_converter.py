import asyncio
import aiofiles
from bip_utils import Bip39SeedGenerator, Bip44, Bip49, Bip84, Bip44Coins, Bip49Coins, Bip84Coins, Bip44Changes
import hashlib
import base58


# Функция для преобразования приватного ключа в WIF
async def private_key_to_wif(private_key_hex, compressed = True):
    litecoin_prefix = b'\xb0'  # Префикс для Litecoin
    # Конвертация ключа из hex в байты.
    raw_key_bytes = bytes.fromhex(private_key_hex)

    # В конец полученного байтового ключа добавляется префикс \x01, обозначающий, что ключ будет компрессированным.
    if compressed:
        compressed_suffix = b'\x01'
        key_with_suffix = raw_key_bytes + compressed_suffix
    else:
        key_with_suffix = raw_key_bytes

    # Добавление префикса в начале ключа. Префикс означает что ключ будет для монеты лайткойн
    prefixed_key = litecoin_prefix + key_with_suffix

    # Вычисление контрольной суммы
    # Хеширование и повторное хеширование первого хеша
    first_hash = hashlib.sha256(prefixed_key).digest()
    second_hash = hashlib.sha256(first_hash).digest()
    # Первые 4 байта второго хеша
    checksum = second_hash[:4]

    # Формирование полного payload путем добавления 4 байтов от хеша в конец ключа
    full_wif_bytes = prefixed_key + checksum

    # Кодирование в Base58
    base58_encoded = base58.b58encode(full_wif_bytes)

    # Конвертация в строку
    wif_string = base58_encoded.decode('utf-8')

    return wif_string


async def mnemonic_to_wallet(mnemonic_phrase):
    # Объект для хранения созданных адресов и приватных ключей
    all_wallets = []

    try:
        # Генерируем seed из мнемонической фразы
        seed = Bip39SeedGenerator(mnemonic_phrase).Generate("")

        # Список стандартов для генерации кошельков
        wallet_standards = [
            (Bip44, Bip44Coins.LITECOIN),  # BIP44 - Legacy адреса
            (Bip49, Bip49Coins.LITECOIN),  # BIP49 - SegWit адреса
            (Bip84, Bip84Coins.LITECOIN)  # BIP84 - Native SegWit (Bech32)
        ]

        for wallet_class, coin_type in wallet_standards:
            # Создаем мастер-кошелек из seed используя данные из wallet_standards
            # То-есть стандарт кошелька, например Bip44 а так же монету, в нашем случае Bip44Coins.LITECOIN
            master_wallet = wallet_class.FromSeed(seed, coin_type)

            # Генерируем два типа адресов: для получения и для сдачи
            # Bip44Changes.CHAIN_EXT для получения
            # Bip44Changes.CHAIN_INT для сдачи
            for change_type in [Bip44Changes.CHAIN_EXT, Bip44Changes.CHAIN_INT]:
                # Генерируем конкретное количество (указанное в переменной depth) адресов
                for address_index in range(depth):
                    # Строим путь деривации
                    derived_key = (master_wallet
                                   .Purpose()  # Начало пути (BIP44/49/84)
                                   .Coin()  # Выбор монеты (Litecoin)
                                   .Account(0)  # Основной аккаунт
                                   .Change(change_type)  # Тип адреса
                                   .AddressIndex(address_index))  # Номер адреса

                    # Получаем адрес кошелька
                    address = derived_key.PublicKey().ToAddress()

                    # Конвертируем приватный ключ
                    raw_private_key = derived_key.PrivateKey().Raw().ToHex()
                    wif_private_key = await private_key_to_wif(raw_private_key)

                    # Сохраняем результат
                    all_wallets.append((address, wif_private_key))

        return all_wallets

    except Exception as error:
        print(f"Ошибка генерации кошельков: {error}")
        return []



# Асинхронная обработка одной мнемонической фразы
async def process_mnemonic(mnemonic_phrase):
    async with aiofiles.open(output_file_path, "a", encoding="utf-8") as output_file:
        # Убирает пробелы в начале и в конце мнемонической фразы если они есть
        mnemonic_phrase = mnemonic_phrase.strip()
        # Если мнемоническая фраза есть
        if mnemonic_phrase:
            # Вызываем функцию для генерации приватных ключей и адресов передавая в функцию мнемоническую фразу
            # В переменную записываются данные из функции генерации приватных ключей и адресов
            wallets = await mnemonic_to_wallet(mnemonic_phrase)

            # Если переменная не пустая
            if wallets:
                for wallet in wallets:
                    # Данные из переменной разбиваются на отдельные переменные для адресов, приватных ключей и т.д
                    address, private_key_wif = wallet
                    # Данные из двух переменных записываются в переменную result.
                    result = f"{private_key_wif}:{address}\n"
                    # Вывод данных в консоль
                    print(result)
                    # Запись в файл
                    await output_file.write(result)
            else:
                print(f"Не удалось обработать фразу: {mnemonic_phrase}")


# Основная асинхронная функция для обработки всех фраз
async def process_mnemonics():
    async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
        mnemonics = await file.readlines()

    # Корутина это объекты или задачи которые будут выполнены позже.
    # В нашем случае это вызов функции process_mnemonic.
    # То есть, первым делом срабатывает цикл for записывающий мнемоническую фразу из списка в переменную,
    # при каждой итерации цикла, то есть при записи мнемонической фразы в переменную,
    # создается корутина вызова функции process_mnemonic с записанной в переменную мнемонической фразы
    tasks = [process_mnemonic(mnemonic) for mnemonic in mnemonics]

    # Означает в данном случае асинхронный вызов всех корутин, то есть асинхронный вызов вызовов функции process_mnemonic
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    file_path = "./mnemonic_converter/mnemonics.txt"  # Путь к файлу с мнемоническими фразами
    output_file_path = "./mnemonic_converter/output.txt"  # Путь к файлу для записи результата
    depth = 5  # Количество генерируемых адресов и приватных ключей для каждой фразы

    asyncio.run(process_mnemonics())
