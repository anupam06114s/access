

import sys
import os
import binascii
import atexit
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

#
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL
except ImportError:

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    import blackboxprotobuf
except ImportError:
    print(f"{RED}Please Install Required Libraries{RESET}")
    print(f"{YELLOW}Install: pip install pycryptodome blackboxprotobuf{RESET}")
    sys.exit(1)

def print_banner():
    banner = f"""
{BOLD}{BLUE}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   {CYAN}██████╗ ██╗███████╗██╗  ██╗██╗   ██╗                         ║
║   {CYAN}██╔══██╗██║██╔════╝██║  ██║██║   ██║                         ║
║   {CYAN}██████╔╝██║███████╗███████║██║   ██║                         ║
║   {CYAN}██╔══██╗██║╚════██║██╔══██║██║   ██║                         ║
║   {CYAN}██║  ██║██║███████║██║  ██║╚██████╔╝                         ║
║   {CYAN}╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝                          ║
║                                                                  ║
║        {GREEN}Access Token Capture –{RESET}{BLUE}              ║
║                   {YELLOW}by Rishu 💀{RESET}{BLUE}                              ║
╚══════════════════════════════════════════════════════════════════╝{RESET}
    """
    print(banner)

# ---------- AES Keys (unchanged) ----------
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV  = b'6oyZDr22E3ychjM%'

KNOWN_HOSTS = [
    "client.ind.freefiremobile.com",
    "clientbp.ggpolarbear.com",
    "clientbp.common.ggbluefox.com",
]
DEFAULT_HOST = KNOWN_HOSTS[0]

GAME_PATHS = {
    "normal": "/storage/emulated/0/Android/data/com.dts.freefireth/files/localconfig.json",
    "max": "/storage/emulated/0/Android/data/com.dts.freefiremax/files/localconfig.json"
}
CONFIG_JSON = '{"serverLoginUrl":"http://127.0.0.1:8080/"}'

deployed_path = None

# Folder relative to the directory where the script is executed
SAVE_FOLDER = os.path.join(os.getcwd(), "Local config")
SAVE_CONFIG_PATH = os.path.join(SAVE_FOLDER, "localconfig.json")


def deploy(game_type):
    global deployed_path

    path = GAME_PATHS.get(game_type)

    if not path:
        print(f"{RED}Invalid game type.{RESET}")
        return False

    folder = os.path.dirname(path)

    if not os.path.exists(folder):
        print(f"{YELLOW}Folder not found: {folder}{RESET}")
        print(f"{YELLOW}Make Sure Termux Has Permission And You Downloaded The Game{RESET}")
        return False

    try:
        # Create "Local config" folder in execution directory
        os.makedirs(SAVE_FOLDER, exist_ok=True)

        # Create localconfig.json inside that folder
        with open(SAVE_CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(CONFIG_JSON)

        print(f"{GREEN}✓ Local config folder created!{RESET}")
        print(f"   {BLUE}Saved: {SAVE_CONFIG_PATH}{RESET}")

        # Deploy to game location
        with open(path, "w", encoding="utf-8") as f:
            f.write(CONFIG_JSON)

        deployed_path = path

        print(f"{GREEN}✓ localconfig.json deployed successfully!{RESET}")
        print(f"   {BLUE}Game Path: {path}{RESET}")

        return True

    except Exception as e:
        print(f"{RED}Deployment failed: {e}{RESET}")
        return False


def remove_config():
    global deployed_path

    if deployed_path and os.path.exists(deployed_path):
        try:
            os.remove(deployed_path)
            deployed_path = None
        except Exception:
            pass


atexit.register(remove_config)

signal.signal(
    signal.SIGINT,
    lambda s, f: (remove_config(), sys.exit(0))
)

signal.signal(
    signal.SIGTERM,
    lambda s, f: (remove_config(), sys.exit(0))
)


def decrypt_data(ciphertext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self): self._handle()
    def do_POST(self): self._handle()
    def do_PUT(self): self._handle()
    def do_DELETE(self): self._handle()

    def _handle(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''
        if '/GetLoginData' in self.path:
            self._extract_token(body)
        self._forward(body)

    def _extract_token(self, data):
        if not data:
            return
        try:
            dec = decrypt_data(data)
            decoded, _ = blackboxprotobuf.decode_message(dec)
            field = decoded.get(29) or decoded.get('29')
            if isinstance(field, bytes):
                try:
                    token = field.decode('ascii')
                    if len(token) == 64 and all(c in '0123456789abcdefABCDEF' for c in token):
                        # ---- Branded token output ----
                        print(f"\n{GREEN}{BOLD}🎯 Got Access Token!{RESET}")
                        print(f"{CYAN}{BOLD}Access Token =>{RESET} {YELLOW}{token}{RESET}")
                        print(f"{GREEN}🔑 Token captured successfully.{RESET}\n")
                    else:
                        print(f"{RED}Unexpected token format (not 64 hex):{RESET} {field.hex()}")
                except:
                    print(f"{RED}Decoded field is not valid ASCII:{RESET} {field.hex()}")
        except Exception as e:
            print(f"{RED}Extraction error: {e}{RESET}")

    def _forward(self, body):
        host = self.headers.get('Host')
        if not host or '127.0.0.1' in host or ':8080' in host:
            host = DEFAULT_HOST
        url = f'https://{host}{self.path}'
        try:
            req = urllib.request.Request(url, data=body, headers=dict(self.headers))
            req.get_method = lambda: self.command
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()

            try:
                self.send_response(resp.status)
                for h, v in resp.headers.items():
                    if h.lower() not in ('content-length','connection','transfer-encoding'):
                        self.send_header(h, v)
                self.send_header('Content-Length', len(data))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            try:
                self.send_response(502)
                self.send_header('Content-Length', 0)
                self.send_header('Connection', 'close')
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass
        except Exception:
            try:
                self.send_response(502)
                self.send_header('Content-Length', 0)
                self.send_header('Connection', 'close')
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, *args):
        pass

def main():
    print_banner()
    print(f"{BLUE}Select game:{RESET}")
    print(f"  {GREEN}1){RESET} Normal Free Fire")
    print(f"  {GREEN}2){RESET} Free Fire Max")
    choice = input(f"{YELLOW}Enter 1 or 2: {RESET}").strip()
    game = "normal" if choice == "1" else "max" if choice == "2" else None
    if not game:
        print(f"{RED}Invalid choice. Exiting.{RESET}")
        return

    deploy(game)

    host, port = '127.0.0.1', 8080
    server = HTTPServer((host, port), ProxyHandler)
    server.handle_error = lambda *args: None

    print(f"\n{GREEN}✅ Proxy is running!{RESET}")
    print(f"{BLUE}🌐 Listening on {host}:{port}{RESET}")
    print(f"{YELLOW}📱 Open your game now.{RESET}")
    print(f"{MAGENTA}💡 Press Ctrl+C to stop.{RESET}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        remove_config()
        print(f"\n{GREEN}✓ Done. localconfig removed.{RESET}")

if __name__ == '__main__':
    main()
