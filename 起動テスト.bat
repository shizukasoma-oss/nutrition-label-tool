@echo off
cd /d "C:\Users\Shizuka Soma\nutrition-label-tool"
start "" "C:\Users\Shizuka Soma\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.headless true
timeout /t 4 /nobreak > nul
start http://localhost:8501
