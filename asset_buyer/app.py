import os
import json
import urllib.request
import subprocess

from flask import Flask, request, render_template

app = Flask(__name__)
conn = None
ASSET_DETAILS_API = os.environ['ASSET_DETAILS_API']

try:
    address_exists_response = subprocess.run(['solana', 'address'], check=True, stdout=subprocess.PIPE, text=True)\
        .stdout.strip()
    print(address_exists_response)
except Exception as e:
    create_account_response = subprocess.run(['solana-keygen', 'new', '--no-passphrase', '--silent'],
                                             check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    print(create_account_response)


def read_asset_details():
    asset_details = {}
    try:
        asset_details = json.loads(urllib.request.urlopen(ASSET_DETAILS_API).read()
                                   .decode('utf-8'))
    except Exception:
        pass
    return asset_details


def get_token_balance():
    asset_details = read_asset_details()
    tokens = []
    response = subprocess.run(['spl-token', 'accounts'], check=True, stdout=subprocess.PIPE, text=True).stdout \
        .strip().split("\n")
    print(response)
    if response[0] != 'None':
        response = response[2:]
    else:
        response = []
    print(response)
    for res in response:
        details = res.replace("  ", " ").split(" ")
        address = ''
        token_id = details[0]
        amount = details[1]
        tokens.append({
            "address": address,
            "id": token_id,
            "amount": amount,
            "name": asset_details.get(token_id, {}).get("name", ""),
            "image_url": asset_details.get(token_id, {}).get("image_url", "")
        })
    return tokens


@app.route("/", methods=['GET'])
def wallet_info():
    try:
        address = subprocess.run(['solana', 'address'], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
        tokens = get_token_balance()
    except Exception as e:
        print(e)
        address = ''
        tokens = []
    return render_template('wallet_info.html', address=address, tokens=tokens)


@app.route("/send_asset/", methods=['GET'])
def send_asset():
    return render_template('send_asset.html')


@app.route("/api/v1/get_wallet_info/", methods=['GET'])
def get_wallet_info_api():
    try:
        response = get_token_balance()
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/get_address/", methods=['GET'])
def get_address_api():
    try:
        address = subprocess.run(['solana', 'address'], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
        response = {"address": address}
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/send_asset/", methods=['POST'])
def send_asset_api():
    try:
        data = request.json
        address = data['address']
        asset_amount = str(1)
        asset_id = data['asset_id']
        send_token_response = subprocess.run(['spl-token', 'transfer', '--allow-unfunded-recipient',
                                              '--fund-recipient', asset_id, asset_amount, address],
                                             check=True, stdout=subprocess.PIPE, text=True).stdout
        print(send_token_response)
    except Exception as e:
        print(e)
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response),
            status=500,
            mimetype='application/json'
        )
    response = {"success": True}
    return app.response_class(
        response=json.dumps(response),
        status=200,
        mimetype='application/json'
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
