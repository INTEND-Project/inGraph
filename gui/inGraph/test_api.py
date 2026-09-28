#!/usr/bin/env python3
"""
Test script per verificare l'API del Knowledge Graph Visualizer
"""

import requests
import json

def test_repositories():
    """Test endpoint repositories"""
    print("🔍 Testing /repositories endpoint...")
    try:
        response = requests.get("http://localhost:5000/repositories")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Repositories found: {data.get('count', 0)}")
        for repo in data.get('repositories', []):
            print(f"  - {repo}")
        return data.get('repositories', [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def test_query(repository, query):
    """Test query execution"""
    print(f"\n🔍 Testing query on repository '{repository}'...")
    try:
        data = {
            'repository': repository,
            'query': query,
            'format': 'json'
        }
        
        response = requests.post("http://localhost:5000/query", data=data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Raw response: {json.dumps(result, indent=2)}")
            
            if 'results' in result:
                actual_results = result['results']
                if isinstance(actual_results, dict):
                    # Check if it's the nested structure from GraphDB
                    if 'results' in actual_results and 'bindings' in actual_results['results']:
                        bindings = actual_results['results']['bindings']
                        print(f"Results found: {len(bindings)}")
                        
                        # Show first few results
                        for i, binding in enumerate(bindings[:3]):
                            print(f"  Result {i+1}:")
                            for var, value in binding.items():
                                if isinstance(value, dict):
                                    print(f"    {var}: {value.get('value', 'N/A')} ({value.get('type', 'unknown')})")
                                else:
                                    print(f"    {var}: {value}")
                        
                        return actual_results
                    elif 'bindings' in actual_results:
                        bindings = actual_results['bindings']
                        print(f"Results found: {len(bindings)}")
                        return actual_results
                    else:
                        print(f"No bindings found in results: {actual_results.keys()}")
                        return None
                else:
                    print(f"Unexpected results format: {type(actual_results)}")
                    return None
            else:
                print("No 'results' key in response")
                return None
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🚀 Testing Knowledge Graph Visualizer API\n")
    
    # Test repositories
    repositories = test_repositories()
    
    if not repositories:
        print("❌ No repositories found!")
        return
    
    # Test query on first repository with data
    test_query_str = """
    SELECT ?subject ?predicate ?object
    WHERE {
        ?subject ?predicate ?object .
    }
    LIMIT 10
    """
    
    for repo in repositories:
        print(f"\n📊 Checking repository size: {repo}")
        try:
            size_response = requests.get(f"http://localhost:5000/repository/{repo}/size")
            if size_response.status_code == 200:
                size_data = size_response.json()
                size = size_data.get('size', 0)
                print(f"Repository {repo} has {size} triples")
                
                if size > 0:
                    # Test query on this repository
                    results = test_query(repo, test_query_str)
                    if results:
                        print("✅ Query test successful!")
                        break
            else:
                print(f"Could not get size for {repo}")
        except Exception as e:
            print(f"Error checking {repo}: {e}")
    
    print("\n🎯 Test completed!")

if __name__ == "__main__":
    main()
