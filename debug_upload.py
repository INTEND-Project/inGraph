import requests
import json

def debug_upload_approaches(file_path="KG\\gateKG_fixed.jsonld", repository="GATE"):
    """Try different upload approaches to debug the issue"""
    
    print("🔍 Debug Upload - Testing Different Approaches")
    print("=" * 60)
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 File size: {len(content)} characters")
    print(f"📄 File preview (first 200 chars): {content[:200]}...")
    
    # Approach 1: Try different content types
    content_types = [
        'application/ld+json',
        'application/json',
        'text/turtle',
        'application/rdf+xml'
    ]
    
    print(f"\n🧪 Testing different Content-Type headers:")
    for ct in content_types:
        try:
            headers = {'Content-Type': ct}
            url = f"http://localhost:7200/repositories/{repository}/statements"
            
            response = requests.post(url, headers=headers, data=content)
            print(f"   {ct}: Status {response.status_code}")
            
            if response.status_code in [200, 204]:
                print(f"   ✅ SUCCESS with {ct}!")
                return True
            else:
                print(f"   ❌ Failed: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error with {ct}: {str(e)}")
    
    # Approach 2: Try with charset specification
    print(f"\n🧪 Testing with charset specification:")
    try:
        headers = {'Content-Type': 'application/ld+json; charset=utf-8'}
        url = f"http://localhost:7200/repositories/{repository}/statements"
        
        response = requests.post(url, headers=headers, data=content.encode('utf-8'))
        print(f"   With charset: Status {response.status_code}")
        
        if response.status_code in [200, 204]:
            print(f"   ✅ SUCCESS with charset!")
            return True
        else:
            print(f"   ❌ Failed: {response.text[:100]}...")
            
    except Exception as e:
        print(f"   ❌ Error with charset: {str(e)}")
    
    # Approach 3: Try smaller chunks
    print(f"\n🧪 Testing with smaller data chunk:")
    try:
        # Parse JSON and take only first few items
        data = json.loads(content)
        small_data = {
            "@context": data["@context"],
            "@graph": data["@graph"][:5]  # Only first 5 items
        }
        small_content = json.dumps(small_data, indent=2)
        
        headers = {'Content-Type': 'application/ld+json'}
        url = f"http://localhost:7200/repositories/{repository}/statements"
        
        response = requests.post(url, headers=headers, data=small_content)
        print(f"   Small chunk (5 items): Status {response.status_code}")
        
        if response.status_code in [200, 204]:
            print(f"   ✅ SUCCESS with small chunk!")
            print(f"   💡 Issue might be file size or specific content")
            return True
        else:
            print(f"   ❌ Failed: {response.text[:100]}...")
            
    except Exception as e:
        print(f"   ❌ Error with small chunk: {str(e)}")
    
    # Approach 4: Check repository accessibility
    print(f"\n🧪 Testing repository accessibility:")
    try:
        # Test if we can query the repository
        query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        url = f"http://localhost:7200/repositories/{repository}"
        
        response = requests.post(url, headers=headers, data=query)
        print(f"   Query test: Status {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            count = result['results']['bindings'][0]['count']['value']
            print(f"   ✅ Repository accessible, current triples: {count}")
        else:
            print(f"   ❌ Repository query failed: {response.text[:100]}...")
            
    except Exception as e:
        print(f"   ❌ Repository query error: {str(e)}")
    
    return False

if __name__ == "__main__":
    debug_upload_approaches()
