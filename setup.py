#!/usr/bin/env python3
"""
Setup script for Text-to-SQL System
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def check_csv_file():
    """Check if enhanced_db_schema.csv exists"""
    csv_file = "enhanced_db_schema.csv"
    if os.path.exists(csv_file):
        print(f"✅ Found CSV file: {csv_file}")
        return True
    else:
        print(f"❌ CSV file not found: {csv_file}")
        print("Please ensure you have the enhanced_db_schema.csv file in the current directory")
        return False

def main():
    print("🚀 Setting up Text-to-SQL System...")
    print("=" * 50)
    
    # Check CSV file
    if not check_csv_file():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Update database credentials in config.py if needed")
    print("2. Run: python main.py enhanced_db_schema.csv")
    print("3. Start asking questions in natural language!")
    
    return True

if __name__ == "__main__":
    main()