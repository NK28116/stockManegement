import chardet
import sys

def decode_mojibake_file(filepath):
    with open(filepath, 'rb') as f:
        raw_data = f.read()
    
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    
    if encoding:
        try:
            decoded_content = raw_data.decode(encoding)
            print(f"Detected encoding: {encoding}")
            print("--- Decoded Content ---")
            print(decoded_content)
            print("-----------------------")
        except UnicodeDecodeError:
            print(f"Error: Could not decode the file with {encoding} encoding.")
    else:
        print("Error: Could not detect encoding.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_mojibake.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    decode_mojibake_file(filepath)
