Unicode True

!include "MUI2.nsh"

!ifndef STAGE_DIR
  !error "STAGE_DIR is required"
!endif
!ifndef OUTPUT_FILE
  !error "OUTPUT_FILE is required"
!endif
!ifndef ICON_FILE
  !error "ICON_FILE is required"
!endif

!define PRODUCT_NAME "墨析 OCR 工作台"
!define PRODUCT_VERSION "1.3.0"
!define PRODUCT_PUBLISHER "Moxi OCR Studio"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MoxiOCRStudio"

Name "${PRODUCT_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\MoxiOCRStudio"
InstallDirRegKey HKCU "Software\MoxiOCRStudio" "InstallLocation"
RequestExecutionLevel user
Icon "${ICON_FILE}"
SetCompressor /SOLID lzma
SetCompressorDictSize 64

VIProductVersion "1.3.0.0"
VIAddVersionKey /LANG=2052 "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=2052 "FileDescription" "${PRODUCT_NAME} Windows 10 安装程序"
VIAddVersionKey /LANG=2052 "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=2052 "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "MIT licensed components; model downloaded separately."

!define MUI_ABORTWARNING
!define MUI_ICON "${ICON_FILE}"
!define MUI_UNICON "${ICON_FILE}"
!define MUI_FINISHPAGE_RUN "$INSTDIR\MoxiOCRStudio.exe"
!define MUI_FINISHPAGE_RUN_TEXT "启动墨析 OCR 工作台"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

Section "主程序" SEC_MAIN
  SetOutPath "$INSTDIR"
  File /r "${STAGE_DIR}/*.*"
  File "/oname=Windows安装说明.txt" "${__FILEDIR__}\Windows安装说明.txt"
  Delete "$INSTDIR\launch.ps1"
  Delete "$INSTDIR\stop.ps1"

  WriteUninstaller "$INSTDIR\卸载墨析OCR工作台.exe"

  CreateDirectory "$SMPROGRAMS\墨析 OCR 工作台"
  Delete "$SMPROGRAMS\墨析 OCR 工作台\停止后台服务.lnk"
  CreateShortcut \
    "$SMPROGRAMS\墨析 OCR 工作台\墨析 OCR 工作台.lnk" \
    "$INSTDIR\MoxiOCRStudio.exe" \
    "" \
    "$INSTDIR\MoxiOCRStudio.exe"
  CreateShortcut \
    "$DESKTOP\墨析 OCR 工作台.lnk" \
    "$INSTDIR\MoxiOCRStudio.exe" \
    "" \
    "$INSTDIR\MoxiOCRStudio.exe"

  WriteRegStr HKCU "Software\MoxiOCRStudio" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\MoxiOCRStudio.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" '"$INSTDIR\卸载墨析OCR工作台.exe"'
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  ExecWait '"$INSTDIR\runtime\python\pythonw.exe" "$INSTDIR\runtime\python\windows_launcher.py" --stop'

  Delete "$DESKTOP\墨析 OCR 工作台.lnk"
  RMDir /r "$SMPROGRAMS\墨析 OCR 工作台"
  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKCU "Software\MoxiOCRStudio"
  RMDir /r "$INSTDIR"

  MessageBox MB_OK "主程序已卸载。模型和识别记录仍保留在本机 AppData 中，重装后可以继续使用。"
SectionEnd
