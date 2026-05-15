Set WshShell = CreateObject("WScript.Shell")

' Streamlit をバックグラウンドで起動（黒い画面なし）
Dim pythonPath
pythonPath = "C:\Users\Shizuka Soma\AppData\Local\Python\pythoncore-3.14-64\python.exe"

Dim appDir
appDir = "C:\Users\Shizuka Soma\nutrition-label-tool"

WshShell.Run """" & pythonPath & """ -m streamlit run """ & appDir & "\app.py"" --server.headless true", 0, False

' 起動を待つ
WScript.Sleep 4000

' ブラウザを開く
WshShell.Run "http://localhost:8501"
