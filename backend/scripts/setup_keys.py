import os
import sys

def main():
    print("🔑 API Key Setup (Multi-Key Support)")
    print("====================================")
    print("Add multiple Google API keys to avoid rate limits.")
    print("The system will automatically rotate keys if one hits the limit.\n")
    
    print("Paste your keys one by one (press Enter after each).")
    print("Type 'done' when finished.\n")
    
    keys = []
    while True:
        key = input(f"Enter Key #{len(keys)+1}: ").strip()
        if key.lower() == 'done':
            break
        if key:
            keys.append(key)
            print(f"   ✅ Added Key #{len(keys)}")
    
    if not keys:
        print("\n❌ No keys added. Exiting.")
        return

    # Join keys
    keys_str = ",".join(keys)
    
    # Path to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    # Read existing .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    # Update or Append
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("GOOGLE_API_KEYS="):
            new_lines.append(f"GOOGLE_API_KEYS={keys_str}\n")
            found = True
        elif line.startswith("GOOGLE_API_KEY="):
             pass # Remove single key legacy config to avoid confusion
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"\nGOOGLE_API_KEYS={keys_str}\n")
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
        
    print(f"\n✨ Saved {len(keys)} keys to {env_path}")
    print("🚀 You can now run the debate system with higher limits!")

if __name__ == "__main__":
    main()
