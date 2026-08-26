"""
Food Delivery Time Prediction - Flask API

Loads:
    xgb_best.pkl
    Standard_scaler.pkl

The preprocessing matches the training notebook:
- Road traffic: Low=0, Medium=1, High=2, Jam=3
- One-hot encoding with the same reference categories
- Same feature order
- StandardScaler -> tuned XGBoost
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
CORS(app)

# The notebook saves the scaler with a capital S.
model = joblib.load(BASE_DIR / "xgb_best.pkl")
scaler = joblib.load(BASE_DIR / "Standard_scaler.pkl")

FEATURE_COLUMNS = [
    "Delivery_person_Age",
    "Delivery_person_Ratings",
    "Distance",
    "order_hour",
    "Road_traffic_density",
    "Vehicle_condition",
    "multiple_deliveries",
    "Type_of_order_Drinks",
    "Type_of_order_Meal",
    "Type_of_order_Snack",
    "Type_of_vehicle_electric_scooter",
    "Type_of_vehicle_motorcycle",
    "Type_of_vehicle_scooter",
    "Festival_Yes",
    "City_Semi-Urban",
    "City_Urban",
    "Weatherconditions_Fog",
    "Weatherconditions_Sandstorms",
    "Weatherconditions_Stormy",
    "Weatherconditions_Sunny",
    "Weatherconditions_Windy",
]

TRAFFIC_MAP = {
    "Low": 0,
    "Medium": 1,
    "High": 2,
    "Jam": 3,
}


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371
    lat1, lon1, lat2, lon2 = map(
        np.radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return r * 2 * np.arcsin(np.sqrt(a))


def build_feature_row(payload):
    # Distance can be entered directly or calculated from coordinates.
    if payload.get("distance_km") not in (None, ""):
        distance = float(payload["distance_km"])
    else:
        distance = haversine_km(
            float(payload["restaurant_lat"]),
            float(payload["restaurant_lon"]),
            float(payload["delivery_lat"]),
            float(payload["delivery_lon"]),
        )

    row = {col: 0 for col in FEATURE_COLUMNS}

    row["Delivery_person_Age"] = float(payload["age"])
    row["Delivery_person_Ratings"] = min(float(payload["rating"]), 5.0)
    row["Distance"] = distance
    row["order_hour"] = int(payload["order_hour"])
    row["Road_traffic_density"] = TRAFFIC_MAP[payload["traffic"]]
    row["Vehicle_condition"] = int(payload["vehicle_condition"])
    row["multiple_deliveries"] = int(payload["multiple_deliveries"])

    order_type = payload["order_type"]
    if order_type != "Buffet":
        row[f"Type_of_order_{order_type}"] = 1

    vehicle_type = payload["vehicle_type"]
    if vehicle_type != "bicycle":
        row[f"Type_of_vehicle_{vehicle_type}"] = 1

    if payload["festival"] == "Yes":
        row["Festival_Yes"] = 1

    city = payload["city"]
    if city != "Metropolitian":
        row[f"City_{city}"] = 1

    weather = payload["weather"]
    if weather != "Cloudy":
        row[f"Weatherconditions_{weather}"] = 1

    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        payload = request.get_json()
        X = build_feature_row(payload)

        X_scaled = scaler.transform(X)
        prediction = float(model.predict(X_scaled)[0])

        return jsonify({
            "predicted_minutes": round(prediction, 1)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
