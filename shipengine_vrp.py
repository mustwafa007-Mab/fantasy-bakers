import requests
import json
import os

# ShipEngine Setup
# You need to get a FREE API KEY from https://www.shipengine.com/
API_KEY = os.getenv("SHIPENGINE_API_KEY", "TEST_KEY_PLACEHOLDER")
BASE_URL = "https://api.shipengine.com/v1"

headers = {
    "API-Key": API_KEY,
    "Content-Type": "application/json"
}

def validate_address_shipengine(address_line, city, country_code="KE"):
    """
    Available in ShipEngine: Address Validation.
    Ensures the Tuktuk is going to a real place.
    """
    payload = [{
        "address_line1": address_line,
        "city_locality": city,
        "country_code": country_code
    }]
    
    if API_KEY == "TEST_KEY_PLACEHOLDER":
        return {"status": "MOCK_VALID", "original": address_line}

    try:
        response = requests.post(f"{BASE_URL}/addresses/validate", headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def calculate_shipping_rates(weight_kg, from_zip, to_zip):
    """
    Uses ShipEngine Rates API to estimate logic costs.
    In a real scenario, we map Tuktuks to 'Carriers'.
    """
    payload = {
        "rate_options": {
            "carrier_ids": ["se-123456"], # Replace with your simulated carrier ID
        },
        "shipment": {
            "validate_address": "no_validation",
            "ship_to": {
                "postal_code": to_zip,
                "country_code": "KE"
            },
            "ship_from": {
                "postal_code": from_zip,
                "country_code": "KE"
            },
            "packages": [
                {
                    "weight": {
                        "value": weight_kg,
                        "unit": "kilogram"
                    }
                }
            ]
        }
    }
    
    if API_KEY == "TEST_KEY_PLACEHOLDER":
        # Simulate ShipEngine Response
        return {
            "rates": [
                {"carrier_id": "se-tuktuk-01", "shipping_amount": {"amount": 5.00, "currency": "USD"}, "delivery_days": 1},
                {"carrier_id": "se-boda-02", "shipping_amount": {"amount": 3.50, "currency": "USD"}, "delivery_days": 1}
            ]
        }

    response = requests.post(f"{BASE_URL}/rates", headers=headers, json=payload)
    return response.json()

if __name__ == "__main__":
    print("--- The Captain: ShipEngine Logistics Agent ---")
    print(f"Using API Key: {API_KEY}")
    
    # 1. Validate Bakery HQ
    print("\nValidating HQ Address (Kisauni)...")
    res = validate_address_shipengine("Old Malindi Road", "Mombasa")
    print(res)
    
    # 2. Get Rates for Delivery
    print("\nCalculating Rates for 50kg Flour...")
    rates = calculate_shipping_rates(50, "80100", "80100") # Mombasa Codes
    print(json.dumps(rates, indent=2))
