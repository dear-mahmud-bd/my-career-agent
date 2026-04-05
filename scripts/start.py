import subprocess
import sys
import os


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print("🚀 Starting Career Agent...")
    print("📍 URL    : http://localhost:8000")
    print("📊 Flower : http://localhost:5555")
    print("🛑 Press Ctrl+C to stop\n")

    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Career Agent stopped.")


if __name__ == "__main__":
    main()