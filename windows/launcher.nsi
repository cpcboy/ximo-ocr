Unicode True
SilentInstall silent
AutoCloseWindow true
RequestExecutionLevel user

!ifndef OUTPUT_FILE
  !error "OUTPUT_FILE is required"
!endif
!ifndef ICON_FILE
  !error "ICON_FILE is required"
!endif

Name "墨析 OCR 工作台"
OutFile "${OUTPUT_FILE}"
Icon "${ICON_FILE}"
VIProductVersion "1.3.0.2"
VIAddVersionKey /LANG=2052 "ProductName" "墨析 OCR 工作台"
VIAddVersionKey /LANG=2052 "FileDescription" "墨析 OCR 工作台启动程序"
VIAddVersionKey /LANG=2052 "CompanyName" "Moxi OCR Studio"
VIAddVersionKey /LANG=2052 "FileVersion" "1.3.0-rc.2"
VIAddVersionKey /LANG=2052 "LegalCopyright" "Moxi OCR Studio"

Section
  SetOutPath "$EXEDIR"
  Exec '"$EXEDIR\runtime\python\pythonw.exe" "$EXEDIR\runtime\python\windows_launcher.py"'
SectionEnd
