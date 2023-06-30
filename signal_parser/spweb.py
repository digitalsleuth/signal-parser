#!/usr/bin/env python3

from flask import Flask
from flask import render_template
import json
import sys
import os

app = Flask(__name__)

@app.route("/")
def home():
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}contacts.json') as json_contacts:
        contacts = json.load(json_contacts)
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    return render_template(
        'index.html',
        contacts=contacts,
        device_number=device_info['accountE164'],
        title="Signal",
        description="Signal Contacts"
    )

@app.route("/<contact>")
def conversation(contact):
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}messages.json') as json_messages:
        messages = json.load(json_messages)
    with open(f'{src_dir}contacts.json') as json_contacts:
        contacts = json.load(json_contacts)
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    contact_name = contacts[contact]
    return render_template(
        'conversations.html',
        device_number=device_info['accountE164'],
        contact_name=contact_name,
        contact=contact,
        contacts=contacts,
        messages=messages,
        title="Signal",
        description="Signal Message Analyzer"
    )

@app.route("/device.html")
def device():
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}config.json') as json_config:
        config = json.load(json_config)
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    return render_template(
        'device.html',
        device_info=device_info,
        key=config['key'],
        title="Signal Device Info",
        description="Signal Device Info"
    )

@app.route("/attachments.html")
def attachments():
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    with open(f'{src_dir}messages.json') as json_messages:
        messages = json.load(json_messages)
    return render_template(
        'attachments.html',
        device_number=device_info['accountE164'],
        messages=messages,
        src_dir=src_dir,
        title="Signal Attachments",
        description="Signal Attachments"
    )

@app.route("/applogs.html")
def applog():
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}applogs.json') as json_applogs:
        applogs = json.load(json_applogs)
        applogs.sort(key=lambda x:x["time"])
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    return render_template(
        'applogs.html',
        device_number=device_info['accountE164'],
        applogs=applogs,
        title="Signal App Logs",
        description="Signal App Logs"
    )

@app.route("/mainlogs.html")
def mainlog():
    src_dir = app.config.get('src')
    src_dir = f'{src_dir}{os.sep}'
    with open(f'{src_dir}items.json') as json_items:
        device_info = json.load(json_items)
    with open(f'{src_dir}mainlogs.json') as json_mainlogs:
        mainlogs = json.load(json_mainlogs)
        mainlogs.sort(key=lambda x:x["time"])

    return render_template(
        'mainlogs.html',
        device_number=device_info['accountE164'],
        mainlogs=mainlogs,
        title="Signal Main Logs",
        description="Signal Main Logs"
    )

if __name__ == "__main__":
    if len(sys.argv[1:]) == 0:
        print("[!] Source directory missing: provide the path to the directory holding the files to process")
        raise SystemExit(1)
    else:
        src = sys.argv[1]
        if not os.path.exists(src):
            print("[!] The selected path does not exist! Check your path and try again")
            raise SystemExit(1)
        else:
            src = src.rstrip(os.sep)
            app.config['src'] = src
            app.static_url_path = src
            app.static_folder = f'{src}{os.sep}static'
            app.run()
