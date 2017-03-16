;--------------------------------
;Include Modern UI

  !include "MUI.nsh"
  !include "FileFunc.nsh"
  !insertmacro DirState

;--------------------------------
;General

  RequestExecutionLevel admin

  ;Name and file
  Name "mzDesktop"
  OutFile "mzDesktop_setup.exe"


  ;Default installation folder
  InstallDir "$PROGRAMFILES\mzDesktop"


  ;Get installation folder from registry if available
  InstallDirRegKey HKLM "Software\mzDesktop" ""

;--------------------------------
;Variables

  Var MUI_TEMP
  Var STARTMENU_FOLDER
  Var TARGETURL	

;--------------------------------
;Interface Settings

  !define MUI_ICON "images\icons\mz_installer.ico"
  !define MUI_UNICON "images\icons\mz_installer.ico"
  !define MUI_ABORTWARNING

;--------------------------------
;Pages
  !define MUI_WELCOMEPAGE_TITLE "multiplierz/mzDesktop Installation"
  !define MUI_WELCOMEPAGE_TITLE_3LINES
  !define MUI_WELCOMEPAGE_TEXT "Welcome to the multiplierz/mzDesktop installer.\n\nIf you are upgrading from a previous version, it is recommended that you first backup your data and uninstall mzDesktop."
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "License.txt"
  ;!insertmacro MUI_PAGE_COMPONENTS
  Page custom mascot_page
  !insertmacro MUI_PAGE_DIRECTORY


  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\mzDesktop"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

  !insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER

  !insertmacro MUI_PAGE_INSTFILES
  
  !define MUI_FINISHPAGE_TEXT "mzDeskop installation has been completed. \r\n \r\n \
In order to access .RAW files through mzDesktop, you will need to install \
the latest version of MS File Reader from Thermo Scientific."
  !define MUI_FINISHPAGE_LINK_LOCATION "http://sjsupport.thermofinnigan.com/public/detail.asp?id=703"
  !define MUI_FINISHPAGE_LINK "MS File Reader download page."
  !define MUI_FINISHPAGE_NOREBOOTSUPPORT
  !insertmacro MUI_PAGE_FINISH


  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Reserve Files

  ;If you are using solid compression, files that are required before
  ;the actual installation should be stored first in the data block,
  ;because this will make your installer start faster.

  ReserveFile "mascot.ini"
  !insertmacro MUI_RESERVEFILE_INSTALLOPTIONS


;--------------------------------
;Variables

  Var mascot_text
  Var mascot_version
  Var mascot_security
  
  Var "LANGUAGE_DLL_TITLE"
  Var "LANGUAGE_DLL_INFO"
  Var "URL_DOTNET"
  Var "OSLANGUAGE"
  Var "DOTNET_RETURN_CODE"


;--------------------------------
;Installer Sections

Section "mzDesktop" SecMain

  SetOutPath "$INSTDIR"

  ;ADD YOUR OWN FILES HERE...
  File /r /x .svn /x *.nsi /x *.ini *

  ;Store installation folder
  WriteRegStr HKLM "Software\mzDesktop" "" $INSTDIR
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\mzDesktop" \
                   "mzDesktop" "multiplierz/mzDesktop mass-spectrometry toolkit"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\mzDesktop" \
                   "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\mzDesktop" \
                   "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"

  ;Assign mz file type to mzDesktop
  WriteRegStr HKCR ".mz" "" "mzDesktop.mzScript"
  WriteRegStr HKCR "mzDesktop.mzScript" "" "mzDesktop mz script"
  WriteRegStr HKCR "mzDesktop.mzScript\DefaultIcon" "" "$INSTDIR\images\icons\mz_script.ico"
  WriteRegStr HKCR "mzDesktop.mzScript\shell\open\command" "" '"$INSTDIR\mzDesktop.exe" "%1" %*'

  ;Assign mzd file type to mzDesktop
  WriteRegStr HKCR ".mzd" "" "mzDesktop.mzResults"
  WriteRegStr HKCR "mzDesktop.mzResults" "" "mzResults database"
  WriteRegStr HKCR "mzDesktop.mzResults\DefaultIcon" "" "$INSTDIR\images\icons\mz_results.ico"
  WriteRegStr HKCR "mzDesktop.mzResults\shell\open\command" "" '"$INSTDIR\mzDesktop.exe" "%1" %*'

  ;Assign mzi file type to mzDesktop
  WriteRegStr HKCR ".mzi" "" "mzDesktop.mzInfo"
  WriteRegStr HKCR "mzDesktop.mzInfo" "" "mzDesktop mz information object"
  WriteRegStr HKCR "mzDesktop.mzInfo\DefaultIcon" "" "$INSTDIR\images\icons\mz_info.ico"

  ;Assign mzl file type to mzDesktop
  WriteRegStr HKCR ".mzl" "" "mzDesktop.mzLib"
  WriteRegStr HKCR "mzDesktop.mzLib" "" "mzDesktop mz spectral library"
  WriteRegStr HKCR "mzDesktop.mzLib\DefaultIcon" "" "$INSTDIR\images\icons\mz_results.ico"

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application

    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\mzDesktop.lnk" "$INSTDIR\mzDesktop.exe"
    CreateShortCut "$DESKTOP\mzDesktop.lnk" "$INSTDIR\mzDesktop.exe"

  !insertmacro MUI_STARTMENU_WRITE_END

  ;Read a value from an InstallOptions INI file
  !insertmacro MUI_INSTALLOPTIONS_READ $mascot_text "mascot.ini" "Field 2" "State"
  !insertmacro MUI_INSTALLOPTIONS_READ $mascot_version "mascot.ini" "Field 5" "State"
  !insertmacro MUI_INSTALLOPTIONS_READ $mascot_security "mascot.ini" "Field 6" "State"

  Call writeMascotToFile

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\mzDesktop" \
		     "EstimatedSize" "$0"

SectionEnd


;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecMain ${LANG_ENGLISH} "Multiplierz Software."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END


;--------------------------------
;Installer Functions

Function .onInit

  ;Extract InstallOptions INI files
  !insertmacro MUI_INSTALLOPTIONS_EXTRACT "mascot.ini"
  
  ;StrCpy $LANGUAGE_DLL_TITLE "Installer Language"
  ;StrCpy $LANGUAGE_DLL_INFO "Please select a language:"
  ;StrCpy $URL_DOTNET "${URL_DOTNET_1033}"
  ;StrCpy $OSLANGUAGE "1033"
 
; Insert other Language Blocks Here
 
  ;!define MUI_LANGDLL_WINDOWTITLE "$LANGUAGE_DLL_TITLE"
  ;!define MUI_LANGDLL_INFO "$LANGUAGE_DLL_INFO"
  ;!insertmacro MUI_LANGDLL_DISPLAY
  ;!undef MUI_LANGDLL_WINDOWTITLE
  ;!undef MUI_LANGDLL_INFO
  ;InitPluginsDir
  SetOutPath "$PLUGINSDIR"
;  File "Common\Plugins\*.*"
;  File /r "${NSISDIR}\Plugins\*.*"

  ;Call SetupDotNetSectionIfNeeded
  


FunctionEnd


Function mascot_page

  !insertmacro MUI_HEADER_TEXT "Mascot Server URL" ""
  !insertmacro MUI_INSTALLOPTIONS_DISPLAY "mascot.ini"

FunctionEnd

Function writeMascotToFile

  ClearErrors
  FileOpen $0 $INSTDIR\settings.xml a
  FileSeek $0 0 END
  IfErrors done
  FileWrite $0 "  <mascot server=$\""
  FileWrite $0 $mascot_text
  FileWrite $0 "$\" version=$\""
  FileWrite $0 $mascot_version
  FileWrite $0 "$\" security=$\""
  FileWrite $0 $mascot_security
  FileWrite $0 "$\" var_mods=$\"1$\" mascot_ms2=$\"1$\"/>$\r$\n"
  FileWrite $0 "</settings>$\r$\n"
  FileClose $0

  done:


FunctionEnd


;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;ADD YOUR OWN FILES HERE...

  RMDir /r "$INSTDIR"

  !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

  Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\mzDesktop.lnk"
  Delete "$DESKTOP\mzDesktop.lnk"

  ;Delete empty start menu parent directories
  StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"

  startMenuDeleteLoop:
	ClearErrors
    RMDir $MUI_TEMP
    GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

    IfErrors startMenuDeleteLoopDone

    StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop
  startMenuDeleteLoopDone:

  DeleteRegKey /ifempty HKLM "Software\mzDesktop"
  DeleteRegKey HKCR ".mz"
  DeleteRegKey HKCR "mzDesktop.mzScript"

  DeleteRegKey HKCR ".mzd"
  DeleteRegKey HKCR "mzDesktop.mzResults"

  DeleteRegKey HKCR ".mzi"
  DeleteRegKey HKCR "mzDesktop.mzInfo"

  DeleteRegKey HKCR ".mzl"
  DeleteRegKey HKCR "mzDesktop.mzLib"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\mzDesktop"

SectionEnd

