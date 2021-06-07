import json
import sqlite3
import subprocess

from flask import Flask, request, render_template

app = Flask(__name__)
conn = None

try:
    address_exists_response = subprocess.run(['solana', 'address'], check=True, stdout=subprocess.PIPE, text=True)\
        .stdout.strip()
    print(address_exists_response)
except Exception as e:
    create_account_response = subprocess.run(['solana-keygen', 'new', '--no-passphrase', '--silent'],
                                             check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    print(create_account_response)


def get_db_connection():
    db_file = "./assets.db"
    global conn
    if conn is None:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        create_table()
    return conn


def create_table():
    try:
        connection = get_db_connection()
        c = connection.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS Asset (asset_id, asset_name, asset_image_url, asset_amount)""")
        connection.commit()
    except Exception:
        pass


def create_asset_entry(asset_id, asset_name, asset_image_url, asset_amount):
    connection = get_db_connection()
    c = connection.cursor()
    c.execute("""INSERT INTO Asset (asset_id, asset_name, asset_image_url, asset_amount) values(?, ?, ?, ?)""",
              (asset_id, asset_name, asset_image_url, asset_amount))
    connection.commit()


def read_asset_details():
    connection = get_db_connection()
    c = connection.cursor()
    results = c.execute("""Select * from Asset""").fetchall()
    asset_details = {}
    for result in results:
        asset_details[result[0]] = {"id": result[0], "name": result[1], "image_url": result[2], "amount": result[3]}
    return asset_details


def get_token_balance():
    asset_details = read_asset_details()
    tokens = []
    response = subprocess.run(['spl-token', 'accounts'], check=True, stdout=subprocess.PIPE, text=True).stdout\
        .strip().split("\n")
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
def home():
    asset_details = read_asset_details()
    assets = []
    for key, value in asset_details.items():
        assets.append(value)
    return render_template('index.html', assets=assets)


@app.route("/wallet_info/", methods=['GET'])
def wallet_info():
    try:
        address = subprocess.run(['solana', 'address'], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
        tokens = get_token_balance()
        print(tokens)
    except Exception as e:
        print(e)
        address = ''
        tokens = []
    return render_template('wallet_info.html', tokens=tokens, address=address)


@app.route("/issue_asset/", methods=['GET'])
def issue_asset():
    return render_template('issue_asset.html')


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


@app.route("/api/v1/get_issued_assets/", methods=['GET'])
def get_issued_assets_api():
    try:
        asset_details = read_asset_details()
        assets = []
        for key, value in asset_details.items():
            assets.append(value)
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(assets),
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


@app.route("/api/v1/get_assets_info/", methods=['GET'])
def get_assets_info_api():
    asset_details = read_asset_details()
    return app.response_class(
        response=json.dumps(asset_details),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/issue_asset/", methods=['POST'])
def issue_asset_api():
    try:
        response = {}
        data = request.json
        asset_amount = str(1)
        asset_name = data['asset_name']
        asset_icon_url = data['asset_icon_url']
        create_token_response = subprocess.run(['spl-token', 'create-token', '--decimals', '9'],
                                               check=True, stdout=subprocess.PIPE,
                                               text=True).stdout
        print(create_token_response)
        if "Signature:" not in create_token_response:
            raise ValueError("create token failed")
        asset_id = create_token_response.split("\n")[0].split(" ")[2]
        print(asset_id)
        create_token_account_response = subprocess.run(['spl-token', 'create-account', asset_id], check=True,
                                                       stdout=subprocess.PIPE, text=True).stdout
        print(create_token_account_response)
        if "Signature:" not in create_token_account_response:
            raise ValueError("create token account failed")
        token_account = create_token_account_response.split("\n")[0].split(" ")[2]
        mint_token_response = subprocess.run(['spl-token', 'mint', asset_id, asset_amount, token_account], check=True,
                                             stdout=subprocess.PIPE, text=True).stdout
        print(mint_token_response)
        if "Signature:" not in mint_token_response:
            raise ValueError("create token account failed")
        create_asset_entry(asset_id=asset_id, asset_name=asset_name, asset_image_url=asset_icon_url,
                           asset_amount=asset_amount)
    except Exception as e:
        print(e)
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
    app.run(host="0.0.0.0", port=5000, debug=True)
