# SSH Scripts for 47.97.113.144
# Created by JARVIS - 2026-02-13

## Script Overview

This directory contains automated SSH connection scripts for server maintenance.

### Files Included:

1. **ssh_connect_47.bat** - Windows Batch Script (推荐使用)
2. **ssh_connect_47.ps1** - PowerShell Script
3. **ssh_maintenance_47.ps1** - Automated Maintenance Script
4. **README.txt** - This file

---

## Connection Parameters:

```
Server IP: 47.97.113.144
SSH Port: 222
Username: root
Password: zXc363324112
```

---

## How to Use:

### Method 1: Using Batch Script (推荐)

```batch
# Double-click the file or run from command line
ssh_connect_47.bat
```

**Requirements:**
- Windows 10/11 or Windows Server 2016+
- OpenSSH Client (built into Windows 10+)

### Method 2: Using PowerShell Script

```powershell
# Run from PowerShell (may need to set execution policy)
powershell -ExecutionPolicy Bypass -File ssh_connect_47.ps1
```

### Method 3: Automated Maintenance

```powershell
# Run automated system checks
powershell -ExecutionPolicy Bypass -File ssh_maintenance_47.ps1
```

---

## Requirements:

### Option 1: Windows OpenSSH (Recommended)
- Built into Windows 10/11 and Server 2019+
- No installation required
- Password must be entered manually (security feature)

### Option 2: PuTTY/plink
1. Download PuTTY from: https://www.putty.org/
2. Install PuTTY (includes plink.exe)
3. Scripts will automatically detect and use plink

---

## What the Scripts Do:

### ssh_connect_47.bat / .ps1
- Connects to 47.97.113.144:222
- Opens interactive SSH session
- Allows manual command execution

### ssh_maintenance_47.ps1
Automatically runs the following checks:
- System information (hostname, kernel, date/time)
- CPU usage (top command)
- Memory usage (free command)
- Disk usage (df command)
- Network status (netstat)
- Running services (systemctl)

---

## Troubleshooting:

### Q: Script says "ssh is not recognized"
A: OpenSSH is not installed. Install it via:
Settings > Apps > Optional Features > OpenSSH Client

### Q: Connection timeout
A: Check firewall settings and ensure port 222 is open.

### Q: Access denied
A: Verify username (root) and password (zXc363324112)

### Q: Port 222 not working
A: Try port 22 or contact server administrator.

---

## Notes:

- Password will be prompted when using Windows OpenSSH
- For full automation, install PuTTY/plink
- All scripts log connection details
- Scripts are safe and only use standard SSH commands

---

Created by JARVIS - 2026-02-13
For questions or issues, contact JARVIS.
