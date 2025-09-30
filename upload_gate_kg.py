import requests
import os
import json

def check_server_health(server_url="http://localhost:5000"):
    """Check if the GraphDB server is healthy"""
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Server is healthy: {health_data}")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False

def check_repository_exists(repository_name, server_url="http://localhost:5000"):
    """Check if a repository exists"""
    try:
        response = requests.get(f"{server_url}/repositories")
        if response.status_code == 200:
            repos_data = response.json()
            existing_repos = repos_data.get('repositories', [])
            return repository_name in existing_repos
        return False
    except Exception as e:
        print(f"❌ Error checking repository: {str(e)}")
        return False

def create_repository(repository_name, server_url="http://localhost:5000"):
    """Create a new repository"""
    try:
        create_data = {
            'id': repository_name,
            'title': f'{repository_name} Knowledge Graph Repository',
            'ruleset': 'rdfsplus-optimized'
        }
        
        response = requests.post(f"{server_url}/repositories/create", data=create_data)
        
        if response.status_code == 201:
            print(f"✅ Repository '{repository_name}' created successfully!")
            return True
        else:
            print(f"❌ Failed to create repository: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating repository: {str(e)}")
        return False

def validate_jsonld_file(file_path):
    """Validate that the file exists and contains valid JSON"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ JSON-LD file is valid: {file_path}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return False

def upload_jsonld_file(file_path, repository="GATE", server_url="http://localhost:5000"):
    """Upload a JSON-LD file to GraphDB repository"""
    
    print(f"🚀 Starting upload process for {file_path} to repository '{repository}'...")
    
    # Step 1: Check server health
    if not check_server_health(server_url):
        return False
    
    # Step 2: Validate file
    if not validate_jsonld_file(file_path):
        return False
    
    # Step 3: Check if repository exists
    if not check_repository_exists(repository, server_url):
        print(f"❌ Repository '{repository}' not found. Creating it...")
        if not create_repository(repository, server_url):
            return False
    else:
        print(f"✅ Repository '{repository}' exists")
    
    # Step 4: Upload file
    try:
        with open(file_path, 'rb') as file:
            files = {"file": file}
            data = {"repository": repository}
            
            print(f"📤 Uploading {file_path} to repository '{repository}'...")
            
            response = requests.post(f"{server_url}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"📊 Repository: {result.get('repository')}")
                print(f"📄 Filename: {result.get('filename')}")
                print(f"🔢 Total triples: {result.get('total_triples')}")
                return True
            else:
                print(f"❌ Upload failed with status code: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error: {response.text}")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running")
        return False
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False

def get_repository_info(repository, server_url="http://localhost:5000"):
    """Get information about the repository after upload"""
    try:
        response = requests.get(f"{server_url}/repository/{repository}/info")
        if response.status_code == 200:
            info = response.json()
            print(f"\n📈 Repository '{repository}' Information:")
            print(f"   Triple count: {info['info'].get('triple_count', 'Unknown')}")
            print(f"   Named graphs: {len(info['info'].get('named_graphs', []))}")
        else:
            print(f"❌ Could not get repository info: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting repository info: {str(e)}")

if __name__ == "__main__":
    # Configuration
    file_to_upload = "KG\\gateKG_fixed.jsonld"  # Use the fixed JSON-LD file
    target_repository = "GATE"
    
    print("🌟 GATE Knowledge Graph Upload Tool")
    print("=" * 50)
    
    # Upload the file
    success = upload_jsonld_file(file_to_upload, target_repository)
    
    if success:
        print("\n🎉 Upload completed successfully!")
        # Get repository information
        get_repository_info(target_repository)
    else:
        print("\n💥 Upload failed!")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure the Flask server is running (python inGraphApp.py)")
        print("2. Check that GraphDB is running on port 7200")
        print("3. Verify the JSON-LD file is valid")
        print("4. Check server logs for detailed error messages")
