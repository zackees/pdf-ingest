import os

os.system('docker compose down --rmi=all')
os.system('docker compose up --build')