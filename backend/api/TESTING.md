# CargoMove CM — Backend Testing Guide

Run through these in order. Each step assumes the previous one worked.

## 0. Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in real DB_* values + SECRET_KEY
```

Create the Postgres database (name must match DB_NAME in .env):

```bash
createdb cargomove
```

Apply migrations and create a superuser:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Server should now be at http://127.0.0.1:8000/. Visit `/admin/` and log in
with the superuser to confirm the DB connection works.

## 1. Register a customer and a driver

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/customer/ \
  -H "Content-Type: application/json" \
  -d '{"user": {"username": "alice", "email": "a@x.com", "password": "TestPass123!"}, "company_name": "Alice Ltd"}'

curl -X POST http://127.0.0.1:8000/api/auth/register/driver/ \
  -H "Content-Type: application/json" \
  -d '{"user": {"username": "bob", "email": "b@x.com", "password": "TestPass123!"}, "license_number": "LIC001"}'
```

## 2. Log in as each and save the access tokens

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "TestPass123!"}'
# -> {"refresh": "...", "access": "..."}  save as ALICE_TOKEN

curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "TestPass123!"}'
# -> save as BOB_TOKEN
```

## 3. Role permission checks

```bash
# Bob (driver) trying to create a shipment should be rejected (403)
curl -X POST http://127.0.0.1:8000/api/shipments/ \
  -H "Authorization: Bearer $BOB_TOKEN" -H "Content-Type: application/json" \
  -d '{"origin_city":"Douala","origin_lat":4.05,"origin_lng":9.7,"destination_city":"Yaounde","destination_lat":3.86,"destination_lng":11.5,"pickup_date":"2026-09-15","items":[]}'
# expect 403 Forbidden

# Alice (customer) trying to register a vehicle should be rejected (403)
curl -X POST http://127.0.0.1:8000/api/vehicles/ \
  -H "Authorization: Bearer $ALICE_TOKEN" -H "Content-Type: application/json" \
  -d '{"vehicle_type":"Canter","license_plate":"LT1234","max_weight_kg":2000,"max_volume_m3":10}'
# expect 403 Forbidden
```

## 4. Bob registers a vehicle with a live GPS position

Bob needs `current_lat`/`current_lng` set for the matching algorithm to find
him — do this via `/admin/` for now (there's no "update my location" endpoint
yet for vehicles, only for tracking history), or add the fields to the POST
body if you've wired that up.

```bash
curl -X POST http://127.0.0.1:8000/api/vehicles/ \
  -H "Authorization: Bearer $BOB_TOKEN" -H "Content-Type: application/json" \
  -d '{"vehicle_type":"Canter","license_plate":"LT1234","max_weight_kg":2000,"max_volume_m3":10}'
```
Then in `/admin/`, open the vehicle and set current_lat/current_lng close to
Douala (e.g. 4.06, 9.71) and is_available=True.

## 5. Alice creates a shipment and triggers matching + pricing

```bash
curl -X POST http://127.0.0.1:8000/api/shipments/ \
  -H "Authorization: Bearer $ALICE_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "origin_city":"Douala","origin_lat":4.05,"origin_lng":9.7,
    "destination_city":"Yaounde","destination_lat":3.86,"destination_lng":11.5,
    "pickup_date":"2026-09-15","delivery_type":"EXPRESS",
    "items":[{"description":"Sacks of rice","quantity":10,"length_cm":50,"width_cm":30,"height_cm":20,"weight_kg":25}]
  }'
```

Check the response: `estimated_price_xaf` should be a nonzero number, and
`status` should be `PENDING`.

## 6. Confirm an offer was created for Bob, with the same price

```bash
curl http://127.0.0.1:8000/api/offers/ -H "Authorization: Bearer $BOB_TOKEN"
```
You should see one PENDING offer, `offered_fare_xaf` equal to the shipment's
`estimated_price_xaf`. Also check `/api/notifications/` as Bob — there
should be a "New shipment offer" notification.

## 7. Bob accepts the offer

```bash
curl -X POST http://127.0.0.1:8000/api/offers/<OFFER_ID>/accept/ \
  -H "Authorization: Bearer $BOB_TOKEN"
```
Then verify:
- The shipment's `status` is now `MATCHED`.
- The vehicle's `is_available` is now `False`.
- Alice has a new notification ("Driver accepted your shipment").
- If there were other pending offers on the same shipment, they're now `EXPIRED`.

## 8. Vehicle delete guard

While the vehicle above is committed to the accepted offer, try:
```bash
curl -X DELETE http://127.0.0.1:8000/api/vehicles/<VEHICLE_ID>/ \
  -H "Authorization: Bearer $BOB_TOKEN"
```
Expect `400 Bad Request` with a "currently transporting cargo" message.

## 9. Ratings recompute the driver's average

Mark the shipment `DELIVERED` in `/admin/`, then:
```bash
curl -X POST http://127.0.0.1:8000/api/ratings/ \
  -H "Authorization: Bearer $ALICE_TOKEN" -H "Content-Type: application/json" \
  -d '{"shipment": <SHIPMENT_ID>, "customer": <CUSTOMER_ID>, "driver": <DRIVER_ID>, "stars": 4}'
```
Then check `/admin/` → Driver → `rating_average` updated to 4.0.

## 10. Run the automated tests

```bash
python manage.py test
```
This runs `api/tests.py`, which covers the pricing service's math
(base fare, Express markup, shared-load discount, flat fees) without
touching the database, so it should pass instantly even before you've
set up Postgres.
