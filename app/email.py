# !/usr/local/bin python3
# coding: utf-8
# @FileName  :email.py
# @Time      :2022-10-14 22:41
# @Author    :Sam

from flask_mail import Message
from threading import Thread
from flask import current_app
from app import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body=None,
               attachments=None,sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
        print('Send mail successfully ~')
    else:
        # 异步发送电子邮件
        print("msg:",msg)
        print('异步发送邮件')
        Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
    # return thr
    # mail.send(msg)
