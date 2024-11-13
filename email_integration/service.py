import hashlib
import imaplib
import logging
from datetime import datetime
from email.header import decode_header
from email import message_from_bytes

from email_integration.models import EmailAccount, EmailMessage


class EmailServiceException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class EmailService:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.mailbox = None

    def validate_login_creds(self):
        self._connect()
        self._disconnect()

    def _connect(self):
        try:
            # Настройка для разных провайдеров почты
            if "gmail.com" in self.email:
                self.mailbox = imaplib.IMAP4_SSL("imap.gmail.com")
            elif "yandex.ru" in self.email:
                self.mailbox = imaplib.IMAP4_SSL("imap.yandex.ru")
            elif "mail.ru" in self.email:
                self.mailbox = imaplib.IMAP4_SSL("imap.mail.ru")
            else:
                raise ValueError("Unsupported email provider")

            # Логин
            self.mailbox.login(self.email, self.password)
        except imaplib.IMAP4.error as e:
            # Обработка ошибок аутентификации
            if "LOGIN" in str(e):
                raise EmailServiceException(code=401,
                                            message="Ошибка аутентификации. Проверьте правильность пароля приложения."
                                                    "Убедитесь, что вы используете пароль приложения, если включена двухфакторная аутентификация.")
            else:
                return EmailServiceException(code=500, message=f"Ошибка IMAP: {e}")

    def _disconnect(self):
        self.mailbox.logout()

    def decode_mime_words(self, s):
        """Декодирует заголовки MIME (например, тему)"""
        decoded_words = decode_header(s)
        decoded_string = ''.join(
            word.decode(enc or 'utf-8') if isinstance(word, bytes) else word
            for word, enc in decoded_words
        )
        return decoded_string

    def parse_email_part(self, part):
        """Извлекает текст и вложения из отдельной части письма"""
        content_type = part.get_content_type()
        content_disposition = part.get("Content-Disposition", "")

        if content_type == "text/plain" and "attachment" not in content_disposition:
            return "text", part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
        elif content_type == "text/html" and "attachment" not in content_disposition:
            return "html", part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
        elif "attachment" in content_disposition:
            # Обрабатываем вложение
            file_data = part.get_payload(decode=True)
            filename = self.decode_mime_words(part.get_filename())
            return "attachment", {"filename": filename, "data": file_data}

        return None, None

    def fetch_emails(self):
        self._connect()
        self.mailbox.select("inbox")

        account = EmailAccount.objects.filter(email=self.email).first()
        # Ищем все сообщения в почтовом ящике
        status, messages = self.mailbox.search(None, 'ALL')
        if status != 'OK':
            logging.error('Ошибка при попытке получить список сообщений.')
            return

        messages = messages[0].split()
        messages_count = len(messages)
        checked_messages = 0
        # Проходим по каждому сообщению
        for k, num in enumerate(messages):
            status, data = self.mailbox.fetch(num, '(RFC822 INTERNALDATE)')
            if status != 'OK':
                logging.error(f"Ошибка при получении письма {num}")
                continue

            raw_email = None
            internal_date = None
            for response_part in data:
                # Получаем дату и время получения письма
                if isinstance(response_part, tuple):
                    if b"RFC822" in response_part[0]:
                        raw_email = response_part[1]

                if b"INTERNALDATE" in response_part:
                    internal_date_str = response_part.decode().split('INTERNALDATE')[1].strip(' )"')
                    try:
                        internal_date = datetime.strptime(internal_date_str, '%d-%b-%Y %H:%M:%S %z')
                    except ValueError:
                        internal_date = datetime.now()

            if not raw_email:
                logging.error(f"Ошибка при получении письма {num}")
                continue

            unique_hash = hashlib.sha256(raw_email).hexdigest()
            try:
                exist_email = EmailMessage.objects.get(unique_hash=unique_hash)
                checked_messages += 1
                yield {
                    'checked_messages': checked_messages
                }
            except EmailMessage.DoesNotExist:
                pass

            # Проверяем, что письмо еще не было импортировано
            if EmailMessage.objects.filter(unique_hash=unique_hash).exists():
                continue

            message = message_from_bytes(raw_email)

            # Получаем и декодируем тему письма
            subject = self.decode_mime_words(message['subject'] or '')

            # Парсим и форматируем дату и время отправки
            date_sent_str = message.get('Date')
            try:
                date_sent = datetime.strptime(date_sent_str, '%a, %d %b %Y %H:%M:%S %z')
            except (TypeError, ValueError):
                date_sent = None

            text_content = ""
            html_content = ""
            attachments = []

            def process_parts(part):
                nonlocal text_content, html_content, attachments
                if part.is_multipart():
                    for subpart in part.get_payload():
                        process_parts(subpart)
                else:
                    part_type, content = self.parse_email_part(part)
                    if part_type == "text":
                        text_content += content
                    elif part_type == "html":
                        html_content += content
                    elif part_type == "attachment":
                        attachments.append(str(content))

            # Обрабатываем сообщение рекурсивно
            process_parts(message)

            # Выбираем текстовое содержание в порядке приоритета
            content = text_content if text_content else html_content

            # Создаем объект Message и сохраняем в БД
            message = EmailMessage(
                email_account_id=account.id,
                subject=subject,
                send_date=date_sent,
                received_date=internal_date,
                text=content,
                attachments=attachments,
                unique_hash=unique_hash
            )
            message.save()

            yield {
                'messages_count': messages_count,
                'k': k,
                'subject': subject,
                'send_date': date_sent.strftime('%d.%m.%Y %H:%M:%S'),
                'content': content
            }

        # Закрываем соединение
        self._disconnect()
