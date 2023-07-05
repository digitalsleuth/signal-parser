#!/usr/bin/env python3

import os
import sys
import json
import argparse
from datetime import datetime as dt
from sqlcipher3 import dbapi2 as sqlcipher

"""
Notes: E164 - https://en.wikipedia.org/wiki/E.164
"""

__version__ = "1.2.0"
__authors__ = "G-K7, Corey Forman (digitalsleuth)"


def get_key(config_file):
    f = open(config_file)
    db_key = json.load(f)["key"]
    return db_key


def parse_db(args):
    db_key = get_key(f"{args['dir']}{os.sep}config.json")
    PRAGMA_KEY = f"""pragma key="x'{db_key}'";"""
    db = sqlcipher.connect(f"{args['dir']}{os.sep}sql{os.sep}db.sqlite")
    db.execute(PRAGMA_KEY)
    messages = db.execute("select json from messages;").fetchall()
    conversations = db.execute("select json from conversations;").fetchall()
    items = db.execute("select json from items;").fetchall()
    return messages, conversations, items


def analyze_data(messages, conversations, items, args):
    data_path = f'{args["dir"]}{os.sep}'
    out_dir = f'{args["output"]}{os.sep}'
    SIG_ITEMS = get_items(items)
    SIG_CONTACTS = get_contacts(conversations, SIG_ITEMS["accountE164"])
    SIG_MESSAGES = get_messages(messages)
    SIG_PRETTY_MSGS = get_msg_display(SIG_MESSAGES, SIG_CONTACTS)
    SIG_APP_LOGS = get_logs(data_path, "app", args)
    SIG_MAIN_LOGS = get_logs(data_path, "main", args)
    contacts_json = open(f"{out_dir}contacts.json", "w")
    json.dump(SIG_CONTACTS, contacts_json)
    contacts_json.close()
    messages_json = open(f"{out_dir}messages.json", "w")
    json.dump(SIG_PRETTY_MSGS, messages_json)
    messages_json.close()
    convos_json = open(f"{out_dir}convos.json", "w")
    json.dump(conversations, convos_json)
    convos_json.close()
    items_json = open(f"{out_dir}items.json", "w")
    json.dump(SIG_ITEMS, items_json)
    items_json.close()
    config_json = open(f"{out_dir}config.json", "w")
    with open(f'{data_path}config.json') as config:
        config_file = json.load(config)
    json.dump(config_file, config_json)
    config_json.close()
    config.close()

def get_contacts(conversations, accountE164):
    contacts = {}
    for entry in range(0, len(conversations)):
        contact = json.loads(conversations[entry][0])
        avatars, profileAvatar, group_avatar = get_avatars(contact)
        contact["avatars"] = avatars
        contact["profileAvatar"] = profileAvatar
        contact["avatar"] = group_avatar
        if contact.get("e164", ""):
            if str(contact["e164"]) in str(accountE164) and "name" in contact:
                contact["name"] = f"{contact['name']} - NOTE TO SELF"
            elif str(contact["e164"]) in str(accountE164) and "name" not in contact:
                contact["name"] = "NOTE TO SELF"
        else:
            contact["e164"] = "NO E.164"
        contacts[contact["id"]] = (
            contact.get("name", ""),
            f"{contact.get('profileName', '')}",
            f"{contact.get('profileFamilyName', '')}",
            f"{contact.get('e164', '')} ",
            f"{contact['type'].upper()} ",
            contact["messageCount"],
            contact["sentMessageCount"],
            contact["avatars"],
            contact["profileAvatar"],
            contact.get("avatar", ""),
            contact.get("membersV2", ""),
            contact["type"],
            contact.get("uuid", ""),
        )
    sorted_contacts = dict(
        sorted(contacts.items(), key=lambda x: x[1][5], reverse=True)
    )
    return sorted_contacts


def get_messages(message_list):
    messages = []
    for entry in range(0, len(message_list)):
        msg = {}
        msg_dict = json.loads(message_list[entry][0])
        for k, v in msg_dict.items():
            msg[k] = v
        if "type" in msg:
            if msg["type"] in ["call-history", "incoming", "outgoing"]:
                messages.append(msg)
    return messages


def get_msg_display(messages, contacts):
    pretty_msgs = []
    for message in messages:
        message["ContactInfo"] = contacts[message["conversationId"]]
        message["UserInfo"] = message["ContactInfo"][0]
        if message["sent_at"] != "":
            message["SentUTC"] = get_utc(message["sent_at"])
        if message["type"] == "call-history":
            if "acceptedTime" not in message["callHistoryDetails"]:
                acceptedTime = ""
            else:
                acceptedTime = get_utc(message["callHistoryDetails"]["acceptedTime"])
            if "endedTime" not in message["callHistoryDetails"]:
                endedTime = ""
            else:
                endedTime = get_utc(message["callHistoryDetails"]["endedTime"])
            message["body"] = {
                "callMode": message["callHistoryDetails"]["callMode"],
                "wasIncoming": message["callHistoryDetails"]["wasIncoming"],
                "wasVideoCall": message["callHistoryDetails"]["wasVideoCall"],
                "wasDeclined": message["callHistoryDetails"]["wasDeclined"],
                "acceptedTime": acceptedTime,
                "endedTime": endedTime,
            }
        if message.get("hasAttachments", "") == 1:
            attachment, details = get_attachments(message["attachments"])
            message["Attachments"] = attachment
            message["AttachmentDetails"] = details
        pretty_msgs.append(message)
    return pretty_msgs


def get_items(item_list):
    items = {}
    for entry in range(0, len(item_list)):
        item = json.loads(item_list[entry][0])
        if "value" in item:
            items[item["id"]] = item["value"]
        else:
            items[item["id"]] = ""
    items["lastAttemptedToRefreshProfilesAt"] = get_utc(
        items["lastAttemptedToRefreshProfilesAt"]
    )
    items["lastHeartbeat"] = get_utc(items["lastHeartbeat"])
    items["lastStartup"] = get_utc(items["lastStartup"])
    items["nextSignedKeyRotationTime"] = get_utc(items["nextSignedKeyRotationTime"])
    items["synced_at"] = get_utc(items["synced_at"])
    sorted_items = dict(sorted(items.items()))
    return sorted_items


def get_attachments(attachments):
    attachment = []
    details = {}
    for this_attachment in attachments:
        if "path" in this_attachment:
            this_attachment["fileName"] = this_attachment.get("fileName", "NO-FILENAME")
            if os.sys.platform == "linux":
                this_attachment["path"] = this_attachment["path"].replace("\\", "/")
                if "thumbnail" in this_attachment:
                    this_attachment["thumbnail"]["path"] = this_attachment["thumbnail"][
                        "path"
                    ].replace("\\", "/")
            attachment.append(f'attachments.noindex{os.sep}{this_attachment["path"]}')
            if "uploadTimestamp" in this_attachment:
                this_attachment["uploadTimestamp"] = get_utc(
                    this_attachment["uploadTimestamp"]
                )
            for k, v in this_attachment.items():
                details.update({k: v})
            details.update({"path": f'attachments.noindex{os.sep}{details["path"]}'})
    details = dict(sorted(details.items()))
    return attachment, details


def get_avatars(contact):
    avatars_dict = {}
    profile_avatar = {}
    group_avatar = {}
    linux = os.sys.platform == "linux"
    if "avatars" in contact and contact["avatars"] is not None:
        avatar_list = contact["avatars"]
        for entry in avatar_list:
            if "imagePath" in entry:
                if linux:
                    path = entry["imagePath"].replace("\\", "/")
                    entry["imagePath"] = f"avatars.noindex{os.sep}{path}"
                avatars_dict.update({entry["id"]: entry["imagePath"]})
    if "profileAvatar" in contact and contact["profileAvatar"] is not None:
        for hash, path in contact["profileAvatar"].items():
            if linux:
                path = path.replace("\\", "/")
                path = f"attachments.noindex{os.sep}{path}"
            profile_avatar.update({hash: path})
    if "avatar" in contact and contact["avatar"] is not None:
        if linux:
            path = contact["avatar"]["path"].replace("\\", "/")
            contact["avatar"]["path"] = f"attachments.noindex{os.sep}{path}"
            group_avatar = contact["avatar"]
    avatars_dict = dict(sorted(avatars_dict.items()))
    return avatars_dict, profile_avatar, group_avatar


def get_logs(data_path, type, args):
    log_path = f"{data_path}{os.sep}logs/"
    out_dir = f'{args["output"]}{os.sep}'
    all_logs = os.listdir(log_path)
    selected_logs = []
    if type == "app":
        log_name = "app.log"
        json_name = "applogs.json"
    elif type == "main":
        log_name = "main.log"
        json_name = "mainlogs.json"
    for log in all_logs:
        if log_name in log:
            selected_logs.append(log)
    selected_logs.sort()
    selected_json = open(f"{out_dir}{json_name}", "w")
    log_content = []
    for log in selected_logs:
        content = open(f"{log_path}{log}", "r")
        lines = content.readlines()
        for i in range(0, len(lines)):
            entry_dict = {}
            entry = json.loads(lines[i])
            for k, v in entry.items():
                entry_dict.update({k: v})
            log_content.append(entry_dict)
    json.dump(log_content, selected_json)
    selected_json.close()
    return log_content


def get_fields(table_data):
    fields = set()
    for entry in table_data:
        try:
            fields.update(set(entry.keys()))
        except:
            continue
    return list(fields)


def get_utc(ts):
    if ts is None:
        dtg = ""
    else:
        epoch = ts / 1000
        dt_unformatted = dt.fromtimestamp(epoch)
        dtg = dt_unformatted.strftime("%Y-%m-%d %H:%M:%S.%f UTC")
    return dtg


def start_web(args):
    try:
        from signal_parser import spweb
    except ImportError:
        import spweb
    IP = args["web"]
    data_path = f'{args["dir"]}{os.sep}'
    out_dir = f'{args["output"]}{os.sep}'
    dst_path = f"{out_dir}static"
    dst_path = os.path.abspath(dst_path)
    src_path = os.path.abspath(data_path)
    dir_fd = os.open(f"{data_path}", os.O_RDONLY)
    if os.path.exists(dst_path) and os.path.islink(dst_path):
        os.unlink(dst_path)
    elif os.path.exists(dst_path) and not os.path.islink(dst_path):
        print("The file/folder 'static' exists and is not a link. Either rename/delete this file, or run this command from another location.")
        raise SystemExit(1)
    curdir = os.getcwd()
    os.chdir(out_dir)
    os.symlink(src_path, "static")
    os.chdir(curdir)
    spweb.app.config['src'] = out_dir
    spweb.app.static_url_path = f'{dst_path}'
    spweb.app.static_folder = f'{dst_path}'
    spweb.app.run(host=IP)


def main():
    """Parse provided arguments"""
    arg_parse = argparse.ArgumentParser(
        description=f"Signal DB Parser v" f"{str(__version__)}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parse.add_argument(
        "-d",
        "--dir",
        metavar="SIGNAL_DIR",
        help="the Signal data directory",
        required=True,
    )
    arg_parse.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT_DIR",
        help="the location for storing processed data",
        required=True,
    )
    arg_parse.add_argument(
        "-l",
        "--load",
        help="load pre-processed data - does not re-process, requires -w, -o, -d",
        action='store_true',
    )
    arg_parse.add_argument(
        "-w",
        "--web",
        help="launch the web interface after parsing, specify the IP address to use",
        metavar="IP_ADDR",
        nargs="?",
        const="0.0.0.0",
        type=str,
    )
    if len(sys.argv[1:]) == 0:
        arg_parse.print_help()
        arg_parse.exit()
    args = arg_parse.parse_args()
    arg_list = vars(args)
    arg_list["dir"] = arg_list["dir"].rstrip(os.sep)
    arg_list["output"] = arg_list["output"].rstrip(os.sep)
    if not os.path.exists(arg_list["dir"]):
        print(
            "The chosen directory does not exist! Please check your path and try again!"
        )
        raise SystemExit(1)
    if not os.path.exists(f"{arg_list['dir']}{os.sep}config.json"):
        print(
            "The config.json file does not exist in the specified location. Please check that it exists and try again!"
        )
        raise SystemExit(1)
    if not os.path.exists(f"{arg_list['dir']}{os.sep}sql{os.sep}db.sqlite"):
        print(
            "The db.sqlite file does not exist in the specified location. Please check that it exists and try again!"
        )
        raise SystemExit(1)
    if not os.path.exists(arg_list["output"]):
        os.mkdir(arg_list["output"])
    if arg_list["load"] and not os.path.exists(arg_list["load"]):
        print(
            "The chosen directory does not exist! Please check your path and try again!"
        )
        raise SystemExit(1)
    if arg_list["load"] and not arg_list["web"]:
        print(
            "The \"load\" and \"web\" options must be used together. Try your command again and make sure you select -w/--web"
    )
        raise SystemExit(1)
    if arg_list["web"] and arg_list["dir"] and arg_list["output"] and arg_list["load"]:
        start_web(arg_list)
    elif (arg_list["dir"] and arg_list["output"]) and not arg_list["load"]:
        messages, conversations, items = parse_db(arg_list)
        analyze_data(messages, conversations, items, arg_list)
        if arg_list["web"]:
            start_web(arg_list)

if __name__ == "__main__":
    main()
