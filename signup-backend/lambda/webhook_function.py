import hashlib
import hmac
import json
import os
import time

import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
ssm = boto3.client("ssm")


def reply(status_code, body):
    return {"statusCode": status_code, "body": json.dumps(body)}


def signature_ok(payload, header, secret):
    timestamp = None
    signatures = []
    for item in header.split(","):
        key, _, value = item.partition("=")
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)

    if not timestamp or not signatures:
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False

    signed = (timestamp + "." + payload).encode()
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in signatures)


def lambda_handler(event, context):
    payload = event.get("body") or ""
    header = (event.get("headers") or {}).get("stripe-signature", "")

    secret = ssm.get_parameter(Name=os.environ["WEBHOOK_SECRET_PARAM"], WithDecryption=True)["Parameter"]["Value"]

    if not signature_ok(payload, header, secret):
        return reply(400, {"error": "Bad signature"})

    stripe_event = json.loads(payload)

    if stripe_event["type"] == "checkout.session.completed":
        session = stripe_event["data"]["object"]
        if session.get("payment_status") == "paid":
            table.update_item(
                Key={"registration_id": session["metadata"]["registration_id"]},
                UpdateExpression="SET #s = :paid, paymentIntent = :pi",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":paid": "paid", ":pi": session.get("payment_intent")},
            )

    return reply(200, {"received": True})