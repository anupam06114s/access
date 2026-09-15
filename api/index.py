from flask import Flask, request, jsonify
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import blackboxprotobuf

app = Flask(__name__)
tokens = {}

# RishuAccessToken.py se same keys
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV  = b'6oyZDr22E3ychjM%'

def decrypt_data(ciphertext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)

@app.route('/')
def home():
    return jsonify({"message": "Free Fire Token Capture API is running"})

@app.route('/capture', methods=['POST', 'GET'])
def capture():
    global tokens
    
    if request.method == 'GET':
        data = tokens.get('latest')
        if data:
            return jsonify(data)
        return jsonify({"error": "No token captured yet"}), 404
    
    # POST request — game se data aayega
    raw = request.get_data()
    print(f"[*] Received {len(raw)} bytes")
    
    try:
        dec = decrypt_data(raw)
        decoded, _ = blackboxprotobuf.decode_message(dec)
        
        # Field 29 = access_token
        field = decoded.get(29) or decoded.get('29')
        
        if isinstance(field, bytes):
            token = field.decode('ascii')
            if len(token) == 64 and all(c in '0123456789abcdefABCDEF' for c in token):
                tokens['latest'] = {
                    'access_token': token,
                    'timestamp': time.time()
                }
                print(f"[+] Token: {token}")
                return jsonify({"status": "success", "message": "Token captured"})
    except Exception as e:
        print(f"[-] Error: {e}")
    
    return jsonify({"status": "error", "message": "Failed to capture"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)