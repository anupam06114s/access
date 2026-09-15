from flask import Flask, request, Response, jsonify
import time
import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import blackboxprotobuf

app = Flask(__name__)

# ---------- In-memory token store ----------
tokens = {}

# ---------- AES Keys (same as Termux version) ----------
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV  = b'6oyZDr22E3ychjM%'

# ---------- Game server hosts ----------
KNOWN_HOSTS = [
    "client.ind.freefiremobile.com",
    "clientbp.ggpolarbear.com",
    "clientbp.common.ggbluefox.com",
]
DEFAULT_HOST = KNOWN_HOSTS[0]


def decrypt_data(ciphertext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)


def extract_token(data):
    """Decrypt + parse protobuf, extract access token from field 29."""
    if not data:
        return None
    try:
        dec = decrypt_data(data)
        decoded, _ = blackboxprotobuf.decode_message(dec)
        field = decoded.get(29) or decoded.get('29')
        if isinstance(field, bytes):
            token = field.decode('ascii')
            if len(token) == 64 and all(c in '0123456789abcdefABCDEF' for c in token):
                return token
    except Exception as e:
        print(f"[-] Extraction error: {e}")
    return None


def forward_to_game_server(method, path, body, headers):
    """Forward request to the actual game server and return response."""
    # Determine target host
    incoming_host = headers.get('Host', '')
    target_host = DEFAULT_HOST

    # Check if Host header points to a known game server
    for known in KNOWN_HOSTS:
        if known in incoming_host:
            target_host = known
            break

    url = f'https://{target_host}{path}'

    # Clean headers for forwarding
    forward_headers = {}
    skip_headers = {'host', 'content-length', 'transfer-encoding', 'connection'}
    for key, value in headers.items():
        if key.lower() not in skip_headers:
            forward_headers[key] = value
    forward_headers['Host'] = target_host

    try:
        with httpx.Client(timeout=15.0, verify=False, follow_redirects=True) as client:
            resp = client.request(
                method=method,
                url=url,
                content=body,
                headers=forward_headers,
            )

        # Build Flask response
        excluded = {'content-encoding', 'transfer-encoding', 'connection', 'content-length'}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}

        return Response(
            response=resp.content,
            status=resp.status_code,
            headers=resp_headers,
        )
    except Exception as e:
        print(f"[-] Proxy error: {e}")
        return Response("Bad Gateway", status=502)


# ==================== ROUTES ====================

@app.route('/')
def home():
    """Status page — shows if API is running."""
    return jsonify({
        "status": "running",
        "developer": "Anupam Mishra",
        "project": "🔥 Free Fire Access Token Capture API",
        "version": "2.0",
        "message": "API is live and ready to capture tokens!",
        "credits": "Developed & Maintained by Anupam Mishra 💀",
        "endpoints": {
            "/token": "GET — View captured token with full details",
            "/config": "GET — Get localconfig.json content (Vercel URL)",
            "/<any-path>": "Proxy — Game traffic forward + token sniff",
        }
    })


@app.route('/token', methods=['GET'])
def get_token():
    """Return the latest captured token with line-by-line details."""
    data = tokens.get('latest')
    if data:
        token = data['access_token']
        ts = data['timestamp']
        return jsonify({
            "🎯 Status": "Token Captured Successfully",
            "👤 Developer": "Anupam Mishra",
            "🔑 Access Token": token,
            "📏 Token Length": f"{len(token)} characters",
            "🕐 Timestamp": ts,
            "📅 Captured At": time.ctime(ts),
            "📦 Token Type": "Free Fire Access Token (Hex-64)",
            "👁️ Token Preview": f"{token[:8]}...{token[-8:]}",
            "🌐 Game Server": DEFAULT_HOST,
            "💀 Credits": "Powered by Anupam Mishra"
        })
    return jsonify({"error": "No token captured yet", "status": "waiting"}), 404


@app.route('/config', methods=['GET'])
def config():
    """Return localconfig.json content pointing to this Vercel URL."""
    # Auto-detect the deployed Vercel URL
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.headers.get('X-Forwarded-Host', request.host)
    vercel_url = f"{scheme}://{host}/"
    return jsonify({
        "serverLoginUrl": vercel_url
    })


# ---------- Catch-all proxy route ----------

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    """
    Proxy handler — same as Termux version ka ProxyHandler.
    1) Agar path me /GetLoginData hai → token extract karo
    2) Request ko actual game server pe forward karo
    3) Game server ka response wapas bhejo
    """
    body = request.get_data()

    # Sniff token from GetLoginData requests
    if 'GetLoginData' in path and body:
        token = extract_token(body)
        if token:
            tokens['latest'] = {
                'access_token': token,
                'timestamp': time.time(),
            }
            print(f"[+] 🎯 TOKEN CAPTURED: {token}")

    # Forward to real game server
    return forward_to_game_server(
        method=request.method,
        path=f'/{path}',
        body=body,
        headers=dict(request.headers),
    )