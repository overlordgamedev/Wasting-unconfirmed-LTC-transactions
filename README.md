# Wasting-unconfirmed-LTC-transactions

Программа для постоянного мониторинга транзакций в mempool на перевод монет LTC на ваши адреса и автоматического вывода монет без ожидания подтверждений. Разработано OverlordGameDev специально для форума XSS.IS.

## 🔥 Функционал
- ✅ Получение приватных ключей и адресов типа **Segwit** и **Legacy**
- ✅ Импортирование и сбор базы данных для хранения всех адресов с приватными ключами
- ✅ Бесконечный поиск неподтвержденных транзакций в **mempool** и проверка наличия ваших адресов в выходах
- ✅ Автоматический вывод еще **неподтвержденных** монет с адресов
- ✅ Отправка уведомлений о выводе монет в **Telegram**

## ⚙️ Требования
- **Litecoin-нода** (собственная, для надежности)
- **PostgreSQL** (используется в качестве СУБД)
- **Python 3.12**

## 🚀 Объяснение кода и инструкция по установке  
https://docs.google.com/document/d/1WIpUMxuHJPCo4RuzfSHyiS00G56Bt6iV6DFMaJF9tEo

## 📡 Как работает программа?
1. Сканирует **mempool** в реальном времени.
2. Проверяет все транзакции на наличие ваших **адресов**.
3. Автоматически создаёт **новую транзакцию** для вывода монет не дожидаясь подтверждений.
4. Отправляет уведомление в **Telegram** о выполненной операции.

