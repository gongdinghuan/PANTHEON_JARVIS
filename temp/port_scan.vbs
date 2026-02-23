Option Explicit
Dim objFSO, objFile
Dim server, ports, port, objShell, result
Dim openPorts, closedPorts

server = "106.14.45.250"
ports = Array(22, 80, 443, 3306, 6379, 9200, 2222, 8080, 21, 23)

Set objFSO = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

' 创建输出文件
Set objFile = objFSO.CreateTextFile("C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\temp\scan_result.txt", True)

objFile.WriteLine("=" * 60)
objFile.WriteLine("端口扫描报告 - " & server)
objFile.WriteLine("=" * 60)
objFile.WriteLine("")
objFile.WriteLine("扫描时间: " & Now)
objFile.WriteLine("")

openPorts = 0
closedPorts = 0

For Each port In ports
    If TestPort(server, port) Then
        objFile.WriteLine("  Port " & Right("     " & port, 5) & " [OPEN]  ✅"
        openPorts = openPorts + 1
    Else
        objFile.WriteLine("  Port " & Right("     " & port, 5) & " [关闭] ❌"
        closedPorts = closedPorts + 1
    End If
Next

objFile.WriteLine("")
objFile.WriteLine("=" * 60)
objFile.WriteLine("扫描完成: " & (openPorts + closedPorts) & " 个端口，" & openPorts & " 个开放"
objFile.WriteLine("=" * 60)

objFile.Close

Function TestPort(host, port)
    On Error Resume Next
    Dim objHTTP
    Set objHTTP = CreateObject("MSXML2.XMLHTTP")
    objHTTP.Open "GET", "http://" & host & ":" & port & "/", False
    objHTTP.setTimeouts 2000, 2000, 2000, 2000
    objHTTP.Send
    
    If Err.Number = 0 Then
        TestPort = True
    Else
        TestPort = False
    End If
    
    Set objHTTP = Nothing
    On Error GoTo 0
End Function
