import requests
import json

def check_and_create_gate_repository(server_url="http://localhost:5000"):
    """
    Check if GATE repository exists and create it if it doesn't
    """
    
    print("🔍 Checking if GATE repository exists...")
    
    try:
        # Check existing repositories
        response = requests.get(f"{server_url}/repositories")
        
        if response.status_code == 200:
            repos_data = response.json()
            existing_repos = repos_data.get('repositories', [])
            
            if 'GATE' in existing_repos:
                print("✅ GATE repository already exists!")
                return True
            else:
                print("❌ GATE repository not found. Creating it...")
                
                # Create GATE repository
                create_data = {
                    'id': 'GATE',
                    'title': 'GATE Knowledge Graph Repository',
                    'ruleset': 'rdfsplus-optimized'
                }
                
                create_response = requests.post(f"{server_url}/repositories/create", data=create_data)
                
                if create_response.status_code == 201:
                    print("✅ GATE repository created successfully!")
                    return True
                else:
                    print(f"❌ Failed to create GATE repository: {create_response.status_code}")
                    print(f"Error: {create_response.text}")
                    return False
        else:
            print(f"❌ Failed to check repositories: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_server_health(server_url="http://localhost:5000"):
    """
    Check if the GraphDB server is healthy
    """
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

if __name__ == "__main__":
    print("🚀 Setting up GATE repository...")
    
    # First check server health
    if check_server_health():
        # Then check/create repository
        if check_and_create_gate_repository():
            print("\n🎉 GATE repository is ready for uploads!")
        else:
            print("\n💥 Failed to setup GATE repository!")
    else:
        print("\n💥 Server is not available!")
