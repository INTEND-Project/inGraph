import requests
import json

def test_small_upload():
    """Test upload with a small JSON-LD file"""
    
    print("🧪 Testing small JSON-LD upload...")
    
    try:
        with open("test_small.jsonld", 'rb') as file:
            files = {"file": file}
            data = {"repository": "GATE"}
            
            response = requests.post("http://localhost:5000/upload", files=files, data=data)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Small file upload successful!")
                return True
            else:
                print("❌ Small file upload failed!")
                return False
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_direct_graphdb():
    """Test direct upload to GraphDB bypassing Flask"""
    
    print("🔗 Testing direct GraphDB upload...")
    
    try:
        with open("test_small.jsonld", 'r', encoding='utf-8') as file:
            content = file.read()
        
        headers = {'Content-Type': 'application/ld+json'}
        url = "http://localhost:7200/repositories/GATE/statements"
        
        response = requests.post(url, headers=headers, data=content)
        
        print(f"Direct GraphDB Status: {response.status_code}")
        print(f"Direct GraphDB Response: {response.text}")
        
        if response.status_code in [200, 204]:
            print("✅ Direct GraphDB upload successful!")
            return True
        else:
            print("❌ Direct GraphDB upload failed!")
            return False
            
    except Exception as e:
        print(f"❌ Direct GraphDB Error: {str(e)}")
        return False

def check_repository_status():
    """Check GATE repository status"""
    
    print("📊 Checking GATE repository status...")
    
    try:
        # Check via Flask API
        response = requests.get("http://localhost:5000/repository/GATE/info")
        print(f"Flask API Status: {response.status_code}")
        if response.status_code == 200:
            info = response.json()
            print(f"Repository info: {info}")
        
        # Check direct GraphDB
        response = requests.get("http://localhost:7200/repositories/GATE/size")
        print(f"Direct GraphDB size check: {response.status_code}")
        print(f"Current size: {response.text if response.status_code == 200 else 'Error'}")
        
    except Exception as e:
        print(f"❌ Status check error: {str(e)}")

if __name__ == "__main__":
    print("🔍 GraphDB Upload Diagnostics")
    print("=" * 40)
    
    # Check repository status first
    check_repository_status()
    
    print("\n" + "=" * 40)
    
    # Test small file via Flask
    test_small_upload()
    
    print("\n" + "=" * 40)
    
    # Test direct GraphDB
    test_direct_graphdb()
