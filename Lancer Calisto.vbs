' Lance Calisto sans aucune fenetre console (ni fenetre noire visible).
Option Explicit
Dim shell, fso, appDir, pythonw, script, cmd

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
script = appDir & "\app_desktop.py"

pythonw = ""
If fso.FileExists(appDir & "\.venv\Scripts\pythonw.exe") Then
    pythonw = appDir & "\.venv\Scripts\pythonw.exe"
Else
    pythonw = "pythonw.exe"
End If

cmd = """" & pythonw & """ """ & script & """"
shell.CurrentDirectory = appDir
shell.Run cmd, 0, False
