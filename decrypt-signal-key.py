#!/usr/bin/env python3

"""
Under macOS:
On a live system, you can get the Signal Safe Storage key by using the following command (with admin credentials):
security find-generic-password -s "Signal Safe Storage" -w
It will look like a base64 value. It is not meant to be decoded.

The Signal path should be at /Users/<user>/Library/Application Support/Signal
In there, the next value you need is in the config.json file as "encryptedKey".
Now you can run this script with -k <keychain_base64_value> -e <encryptedKey_value> -m 'mac'

On a dead-box system, the process is almost identical, except when interacting with the keychain.
You will need to try the following commands to attempt to unlock the keychain file 'login.keychain-db'
after copying it to your Mac. It may be found at /System/Volumes/Data/Users/<user>/Library/Keychains/login.keychain-db.

    security list-keychains -d user -s /path/to/login.keychain-db
    security unlock-keychain -p "<user_password>" /path/to/login.keychain-db
    security find-generic-password -s "Signal Safe Storage" -w /path/to/login.keychain-db

Some tools, like ReconITR, may extract the keychain value for you.

Under Windows:
On a live system, you will need to obtain the DPAPI masterkey in order to decrypt the "encryptedKey".
You can attempt to run a tool like mimikatz or pypykatz to extract the master keys.
You will also need the contents of the "C:\\Users\\<user>\\AppData\\Roaming\\Signal\\Local State" file, specifically
the "encrypted_key" value, as well as the "encryptedKey" value from the config.json

On a dead-box system, you will need a memory dump in order to proceed, as well as volatility3, pypykatz, 
the pypykatz-volatility3 plugin from https://github.com/skelsec/pypykatz-volatility3.

Using volatilty3, run:
    vol3 -f <memory_dump> -p <path_to_pypykatz-volatility3_folder> pypykatz
It will take a while to load, but once done, you should see a number of masterkeys. Make note of all of them.

For both live and dead-box on Windows, you will also need impacket, and the following steps will be the same.

If you already have the "encrypted_key" value from the Signal Local State file, it needs to be base64 decoded and
placed / redirected to a file. If you don't already have it, you can get it using the following
command in Windows PowerShell:
    $hex = cat -Raw 'C:\\Users\\<user>\\AppData\\Roaming\\Signal\\Local State' | ConvertFrom-Json | % os_crypt | % encrypted_key | % {[convert]::FromBase64String($_)}
    [System.IO.File]::WriteAllBytes(<full_file_path>, $hex)
Or Linux or Mac (you may need the jq program if you don't already have it):
    cat <path_to_Local State> | jq -r .os_crypt.encrypted_key | base64 -d | tail -c +6 > <full_file_path>

Once you have this encrypted file (which is the base64 decoded encrypted_key), you can use the 'dpapi.py' module from Impacket to unprotect it:
    dpapi.py unprotect -file <encrypted_file> -k 0x<master_key>
Make sure you place a 0x in front of the master key you retrieved. If you get an error, try the next master key.

Once you get "Successfully decrypted data", copy the bytes from the result and combine them together (no spaces).
This is the "decrypted" master key.

Now run the script with: -e <encrypted_key_from_config.json> -k <decrypted_master_key>

References:
    https://github.com/signalapp/signal-desktop
    https://source.chromium.org/chromium/chromium/src/+/main:components/os_crypt/sync/os_crypt_mac.mm
    https://www.hackthebox.com/blog/memory-dump-analysis-with-signal
    https://github.com/MatejKafka/PSSignalDecrypt
    https://www.coresecurity.com/core-labs/articles/reading-dpapi-encrypted-keys-mimikatz
    https://github.com/bepaald/signalbackup-tools
"""

import binascii
import sys
import argparse
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2

__version__ = "1.0.0"
__author__ = "Corey Forman (digitalsleuth)"


def pkcs7_unpad(data):
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise ValueError("Invalid padding length")
    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("Invalid PKCS#7 padding")
    return data[:-pad_len]


def decrypt_windows_signal_key(master_key: str, encrypted_key_hex: str) -> str:
    NONCE_LEN = 96 // 8
    PFX_LEN = 3

    key = bytes.fromhex(master_key)
    data = bytes.fromhex(encrypted_key_hex)
    nonce = data[PFX_LEN : PFX_LEN + NONCE_LEN]
    cipher_text = data[PFX_LEN + NONCE_LEN :]
    cipher = AES.new(key, AES.MODE_GCM, nonce)
    plain_text = cipher.decrypt(cipher_text)
    result = plain_text[:64].decode("utf-8")

    return result


def decrypt_signal_key(secret_b64: str, encrypted_key_hex: str, machine: str) -> str:
    salt = b"saltysalt"
    version_header = b"v10" if machine == "mac" else b"v11"
    encrypted_bytes = binascii.unhexlify(encrypted_key_hex)
    if encrypted_bytes[:3] != version_header:
        print(
            f"The header of the provided hex string does not match {version_header}\nPlease check your config.json value again."
        )
        raise SystemExit(1)
    encrypted_payload = encrypted_bytes[3:]
    iterations = 1003 if machine == "mac" else 1
    key_length = 16
    derived_key = PBKDF2(secret_b64, salt, dkLen=key_length, count=iterations)
    iv = b" " * 16

    cipher = AES.new(derived_key, AES.MODE_CBC, iv=iv)
    decrypted_padded = cipher.decrypt(encrypted_payload)
    decrypted = pkcs7_unpad(decrypted_padded)
    decrypted_str = decrypted.decode("utf-8")
    if not all(c in "abcdefghijklmnopqrstuvwxyz0123456789" for c in decrypted_str):
        raise ValueError("Decryption succeeded but contents are invalid")

    return decrypted_str


def main():
    arg_parse = argparse.ArgumentParser(description="Signal DB Key decryptor")
    arg_parse.add_argument(
        "-k",
        "--key",
        help="macOS Keychain entry for 'Signal Safe Storage', Linux Keyring entry, or the Windows decrypted master key",
        required=True,
    )
    arg_parse.add_argument(
        "-e",
        "--encrypted",
        help="encryptedKey value from the 'config.json' file",
        required=True,
    )
    arg_parse.add_argument(
        "-m",
        "--machine",
        help="Source machine type: choose from 'windows', 'mac' or 'linux'",
        default="mac",
    )
    arg_parse.add_argument(
        "-t",
        "--tips",
        help="Print tips to obtain the necessary keys",
        action="store_true",
    )
    args = arg_parse.parse_args()
    if args.tips:
        print(__doc__)
        sys.exit(0)
    if not args.key and not args.encrypted:
        arg_parse.error("Both -k/--key and -e/--encrypted are required")
    machine = (args.machine).lower()
    if machine not in {"windows", "mac", "linux"}:
        arg_parse.error(
            "Only 'windows', 'mac' or 'linux' are available for the -m/--machine argument. Please check your entry and try again."
        )
    if machine in {"mac", "linux"}:
        result = decrypt_signal_key(args.key, args.encrypted, machine)
    else:
        result = decrypt_windows_signal_key(args.key, args.encrypted)

    print(f"Decrypted key for the SQLCipher DB: {result}")


if __name__ == "__main__":
    main()
