import requests
import os
import time

def create_repository(repository_id, server_url="http://localhost:5000"):
    """
    Create a new GraphDB repository
    
    Args:
        repository_id (str): Repository ID/name
        server_url (str): Server URL (default: "http://localhost:5000")
    """
    try:
        data = {
            "id": repository_id,
            "title": repository_id,
            "ruleset": "rdfsplus-optimized"
        }
        
        print(f"Creating repository '{repository_id}'...")
        response = requests.post(f"{server_url}/repositories/create", data=data)
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Repository '{repository_id}' created successfully!")
            return True
        elif response.status_code == 409 or "already exists" in response.text.lower():
            print(f"ℹ️  Repository '{repository_id}' already exists")
            return True
        else:
            print(f"❌ Failed to create repository: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating repository: {str(e)}")
        return False

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
    file_to_upload = "fillKG-test2.jsonld"
    target_repository = "fillKG-test2"
    
    # Step 1: Create the repository
    repo_created = create_repository(target_repository)
    
    if not repo_created:
        print("\n💥 Failed to create repository!")
        exit(1)
    
    # Wait a moment for repository to be ready
    print("Waiting for repository to be ready...")
    time.sleep(2)
    
    # Step 2: Upload the file
    success = upload_jsonld_file(file_to_upload, target_repository)
    
    if success:
        print("\n🎉 File uploaded successfully!")
    else:
        print("\n💥 Upload failed!")
