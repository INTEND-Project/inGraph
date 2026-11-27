import requests

data = {
    "id": "GATE",
    "title": "MyGATE", 
    "ruleset": "rdfsplus-optimized"
}

response = requests.post("http://localhost:5000/repositories/create", data=data)
print(response.json())