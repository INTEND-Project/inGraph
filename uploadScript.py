import requests
import os

def upload_jsonld_file(file_path, repository="second-graph", server_url="http://localhost:5000"):
    """
    Upload a JSON-LD file to GraphDB repository
    
    Args:
        file_path (str): Path to the JSON-LD file
        repository (str): Repository name (default: "second-graph")
        server_url (str): Server URL (default: "http://localhost:5000")
    """
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        return False
    
    try:
        # Prepare the file for upload
        with open(file_path, 'rb') as file:
            files = {"file": file}
            data = {"repository": repository}
            
            print(f"Uploading {file_path} to repository '{repository}'...")
            
            # Make the POST request
            response = requests.post(f"{server_url}/upload", files=files, data=data)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"Repository: {result.get('repository')}")
                print(f"Filename: {result.get('filename')}")
                print(f"Total triples: {result.get('total_triples')}")
                return True
            else:
                print(f"❌ Upload failed with status code: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    # Configuration
    file_to_upload = "KG\\gateKG_fixed.jsonld"  # Upload the fixed GATE knowledge graph
    target_repository = "GATE"
    
    # Upload the file
    success = upload_jsonld_file(file_to_upload, target_repository)
    
    if success:
        print("\n🎉 File uploaded successfully!")
    else:
        print("\n💥 Upload failed!")
