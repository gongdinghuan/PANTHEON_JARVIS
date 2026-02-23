Set WshShell = WScript.CreateObject("WScript.Shell")

' 等待SSH窗口打开
WScript.Sleep 2000

' 激活SSH窗口（尝试多种窗口标题）
On Error Resume Next
WshShell.AppActivate "root@47.97.113.144"
WScript.Sleep 500
WshShell.AppActivate "ssh"
WScript.Sleep 500
WshShell.AppActivate "C:\Windows\System32\OpenSSH\ssh.exe"
WScript.Sleep 500
On Error GoTo 0

' 等待密码提示
WScript.Sleep 1000

' 自动输入密码
WshShell.SendKeys "zXc363324112"
WScript.Sleep 200

' 按回车
WshShell.SendKeys "{ENTER}"

' 保持连接，不关闭
WScript.Sleep 5000

MsgBox "密码已自动输入，请检查SSH窗口", 0, "JARVIS 自动化"
