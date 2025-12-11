
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from main import app
    print("Successfully imported app from main.py")
except Exception as e:
    print(f"Failed to import app: {e}")
    import traceback
    traceback.print_exc()
