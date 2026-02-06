
from googlesearch import search
import time

def test():
    query = "python"
    print(f"Testing raw google search for: {query}")
    try:
        # Try without advanced first
        print("1. Standard search:")
        for url in search(query, num_results=3, advanced=False, lang="en"):
            print(f" - {url}")
        
        print("\n2. Advanced search:")
        for res in search(query, num_results=3, advanced=True, lang="en"):
            print(f" - [{res.title}]({res.url})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
