; NSIS installer customization for MSSQL Dashboard
; Checks for Python and ODBC Driver before completing install

!macro customInstall
  ; Check for Python
  nsExec::ExecToStack 'python --version'
  Pop $0
  ${If} $0 != 0
    nsExec::ExecToStack 'py --version'
    Pop $0
    ${If} $0 != 0
      MessageBox MB_YESNO|MB_ICONEXCLAMATION \
        "Python 3.11+ was not detected on this machine.$\n$\nMSSQL Dashboard requires Python to run the monitoring backend.$\n$\nWould you like to open the Python download page?" \
        IDYES openPython IDNO skipPython
      openPython:
        ExecShell "open" "https://www.python.org/downloads/"
      skipPython:
    ${EndIf}
  ${EndIf}

  ; Check for ODBC Driver
  ReadRegStr $R0 HKLM "SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 18 for SQL Server" "Driver"
  ${If} $R0 == ""
    ReadRegStr $R0 HKLM "SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 17 for SQL Server" "Driver"
    ${If} $R0 == ""
      MessageBox MB_YESNO|MB_ICONEXCLAMATION \
        "Microsoft ODBC Driver for SQL Server was not detected.$\n$\nThis driver is required to connect to SQL Server databases.$\n$\nWould you like to open the download page?" \
        IDYES openODBC IDNO skipODBC
      openODBC:
        ExecShell "open" "https://aka.ms/odbc18"
      skipODBC:
    ${EndIf}
  ${EndIf}

  ; Install Python dependencies in background
  nsExec::Exec 'cmd /C cd "$INSTDIR\resources\backend" && python -m pip install -r ..\..\..\resources\app.asar.unpacked\installer\requirements.txt --quiet 2>nul'

!macroend

!macro customUnInstall
  ; Nothing special needed on uninstall
!macroend
