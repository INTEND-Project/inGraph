# config.py (da aggiungere a .gitignore)
API_KEY = ""
PUBLISHER = ""
DATASOURCE = ""

# main script
import json
import requests
import time
from config import API_KEY, PUBLISHER, DATASOURCE

def delete_element(element_id, api_key):
    """Delete the element with the given ID."""
    delete_url = f"https://proxy.onlim.com/api/ts/v1/kg/things/{element_id.split('/')[-1]}?ns=https://intendproject.eu/gate/&dryRun=false&force=true"
    print(delete_url)

    headers = {"x-api-key": api_key}
    response = requests.delete(delete_url, headers=headers)
    
    if response.status_code == 200:
        print(f"Successfully deleted element: {element_id}")
    else:
        print(f"Failed to delete element: {element_id}. Status code: {response.status_code}, Response: {response.text}")

def add_element(payload, api_key, publisher, datasource):
    """Add the element using the provided payload."""
    url = "https://proxy.onlim.com/api/ts/v1/kg/things/imports"
    headers = {
        "x-api-key": api_key,
        "x-publisher": publisher,
        "x-datasource": datasource,
        "Content-Type": "application/ld+json"
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        print("element added successfully.")
    else:
        print(f"Failed to add element. Status code: {response.status_code}, Response: {response.text}")

def main():
    input_file = "Unit_1.jsonld" #file with knoledge graph content
    
    with open(input_file, "r") as f:
        data = json.load(f)

    for element_to_add in data:
        element_id = element_to_add["@id"]
        print(element_id)
       
        delete_element(element_id, API_KEY)
        add_element([element_to_add], API_KEY, PUBLISHER, DATASOURCE)
        
        time.sleep(10)

if __name__ == "__main__":
    main()
