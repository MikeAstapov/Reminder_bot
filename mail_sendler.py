import smtplib
import config


def send_email(to):
    user = "promise-bot@mail.ru"
    passwd = config.password
    server = "smtp.mail.ru"
    port = 465
    subject = "Информационное письмо о том,что данное Вам обещание не было выполнено"

    charset = 'Content-Type: text/plain; charset=utf-8'
    mime = 'MIME-Version: 1.0'
    text = f"Привет.Я бот-напоминалка.Пользователь указал вашу почту ,как мотивацию для выполнения обещания. \n" \
           f"Т.к. обещание он не выполнил - вы получили это письмо.\n" \
           f"Чтобы узнать кто , и что Вам обещал - пришлите 100руб. на этот номер : 8-800-555-35-35"
    body = "\r\n".join((f"From: {user}", f"To: {to}",
                        f"Subject: {subject}", mime, charset, "", text))

    try:
        smtp = smtplib.SMTP_SSL(server, port)
        smtp.ehlo()
        smtp.login(user, passwd)
        smtp.sendmail(user, to, body.encode('utf-8'))

    except smtplib.SMTPException as err:
        print('Что - то пошло не так...')
        raise err
    finally:
        smtp.quit()
