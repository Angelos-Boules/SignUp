import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
ssm = boto3.client("ssm")

FIELDS = ["firstName", "lastName", "phone", "email"]
MAX_GUESTS = 10
MAX_LENGTH = 100
PRICE_CENTS = 100


def reply(status_code, body):
    return {"statusCode": status_code, "body": json.dumps(body)}


def strings_ok(person):
    if not isinstance(person, dict):
        return False
    for field in FIELDS:
        value = person.get(field, "")
        if not isinstance(value, str) or len(value) > MAX_LENGTH:
            return False
    return True


def create_checkout_session(registration_id, email, headcount):
    key = ssm.get_parameter(Name=os.environ["STRIPE_KEY_PARAM"], WithDecryption=True)["Parameter"]["Value"]
    site_url = os.environ["SITE_URL"]

    fields = {
        "mode": "payment",
        "customer_email": email,
        "success_url": site_url + "/?payment=success",
        "cancel_url": site_url + "/?payment=cancelled",
        "metadata[registration_id]": registration_id,
        "line_items[0][quantity]": str(headcount),
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(PRICE_CENTS),
        "line_items[0][price_data][product_data][name]": "Soccer game spot",        
    }

    request = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read())

def lambda_handler(event, context):
    try:
        data = json.loads(event.get("body") or "")
    except json.JSONDecodeError:
        return reply(400, {"error": "Invalid JSON"})

    if not strings_ok(data):
        return reply(400, {"error": "Invalid fields"})

    for field in FIELDS:
        if not data.get(field, "").strip():
            return reply(400, {"error": f"Missing required field: {field}"})

    guests = data.get("guests")
    if not isinstance(guests, list):
        guests = []
    if len(guests) > MAX_GUESTS:
        return reply(400, {"error": "Too many guests"})
    for guest in guests:
        if not strings_ok(guest):
            return reply(400, {"error": "Invalid guest"})

    headcount = 1 + len(guests)

    item = {
        "registration_id": str(uuid.uuid4()),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "pending_payment",
        "headcount": headcount,
        "amountCents": headcount * PRICE_CENTS,
        "firstName": data["firstName"],
        "lastName": data["lastName"],
        "phone": data["phone"],
        "email": data["email"],
        "guests": [{f: guest.get(f, "") for f in FIELDS} for guest in guests],
    }

    table.put_item(Item=item)

    try:
        session = create_checkout_session(item["registration_id"], item["email"], headcount)
    except Exception as error:
        print("Stripe error:", error)
        return reply(502, {"error": "Could not start payment"})

    return reply(201, {"checkoutUrl": session["url"]})