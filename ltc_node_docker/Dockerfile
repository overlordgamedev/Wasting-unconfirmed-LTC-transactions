# Используем образ Ubuntu 22.04 в качестве основы
FROM ubuntu:22.04

# Обновляем пакеты и устанавливаем необходимые утилиты
RUN apt-get update && apt-get install -y wget tar dirmngr

# Устанавливаем рабочую директорию
WORKDIR /opt

# Скачиваем Litecoin Core 0.21.4 и устанавливаем
RUN wget https://download.litecoin.org/litecoin-0.21.4/linux/litecoin-0.21.4-x86_64-linux-gnu.tar.gz --no-check-certificate \
    && tar -zvxf litecoin-0.21.4-x86_64-linux-gnu.tar.gz \
    && mv litecoin-0.21.4/bin/* /usr/bin \
    && rm -rf litecoin-0.21.4-x86_64-linux-gnu.tar.gz litecoin-0.21.4

# Создаем директорию для конфигурационных файлов Litecoin
RUN mkdir -p /root/.litecoin

# Копируем конфигурационный файл в контейнер
COPY litecoin.conf /root/.litecoin/litecoin.conf

# Открываем порты:
EXPOSE 9333 9332

# Запускаем Litecoin ноду с логированием в консоль
CMD ["litecoind", "-printtoconsole"]
