import json
import os

def fix_jsonld_format(input_file, output_file):
    """
    Fix JSON-LD format by adding proper @context
    """
    print(f"🔧 Fixing JSON-LD format for {input_file}...")
    
    try:
        # Read the original file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create proper JSON-LD structure with @context
        fixed_data = {
            "@context": {
                "@vocab": "https://intendproject.eu/schema/",
                "gate": "https://intendproject.eu/gate/",
                "schema": "https://schema.org/",
                "ds": "https://vocab.sti2.at/ds/",
                "semantify": "https://semantify.it/ds/",
                "id": "@id",
                "type": "@type"
            },
            "@graph": data
        }
        
        # Write the fixed file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Fixed JSON-LD saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing JSON-LD: {str(e)}")
        return False

def validate_jsonld_structure(file_path):
    """
    Validate the JSON-LD structure
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 JSON-LD Structure Analysis:")
        
        if isinstance(data, dict):
            if "@context" in data:
                print("✅ Has @context")
            else:
                print("❌ Missing @context")
                
            if "@graph" in data:
                print(f"✅ Has @graph with {len(data['@graph'])} items")
            elif isinstance(data, list):
                print(f"⚠️  Root is array with {len(data)} items (should be wrapped in @graph)")
            else:
                print("⚠️  Single object (not an array)")
        elif isinstance(data, list):
            print(f"⚠️  Root is array with {len(data)} items (missing @context)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating JSON-LD: {str(e)}")
        return False

if __name__ == "__main__":
    input_file = "KG\\gateKG.jsonld"
    output_file = "KG\\gateKG_fixed.jsonld"
    
    print("🌟 JSON-LD Format Fixer")
    print("=" * 40)
    
    # Validate original file
    print("\n📋 Original file analysis:")
    validate_jsonld_structure(input_file)
    
    # Fix the format
    print("\n🔧 Fixing format...")
    if fix_jsonld_format(input_file, output_file):
        print("\n📋 Fixed file analysis:")
        validate_jsonld_structure(output_file)
        print(f"\n🎉 Fixed file ready: {output_file}")
        print("💡 You can now upload the fixed file using:")
        print(f"   python upload_gate_kg.py  # (update the file path to use {output_file})")
    else:
        print("\n💥 Failed to fix JSON-LD format")
