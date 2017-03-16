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
  InstallDir "$PROGRAMFILES64\mzDesktop"


  ;Get installation folder from registry if available
  InstallDirRegKey HKLM "Software\mzDesktop" ""

;--------------------------------
;Variables

  Var MUI_TEMP
  Var STARTMENU_FOLDER
  Var TARGETURL	

;--------------------------------
;Interface Settings

  ;!define MUI_ICON "mzDesktop\images\icons\mz_installer.ico"
  ;!define MUI_UNICON "mzDesktop\images\icons\mz_installer.ico"
  !define MUI_ABORTWARNING

;--------------------------------
;Pages
  !define MUI_WELCOMEPAGE_TITLE "multiplierz/mzDesktop Installation"
  !define MUI_WELCOMEPAGE_TITLE_3LINES
  !define MUI_WELCOMEPAGE_TEXT "Welcome to the multiplierz/mzDesktop installer.\n\nIf you are upgrading from a previous version, it is recommended that you first backup your data and uninstall mzDesktop."
  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
  !insertmacro MUI_PAGE_COMPONENTS
  Page custom mascot_page
  !insertmacro MUI_PAGE_DIRECTORY


  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\mzDesktop"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

  !insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER

  !insertmacro MUI_PAGE_INSTFILES
  
  !define MUI_FINISHPAGE_TEXT "mzDeskop installation has completed. \r\n \
In order to access .RAW files through mzDesktop, you will need to install\
the latest version of MS File Reader from Thermo Scientific."
  !define MUI_FINISHPAGE_LINK_LOCATION "http://sjsupport.thermofinnigan.com/public/detail.asp?id=703"
  !define MUI_FINISHPAGE_LINK "MS File Reader download page."
  !define MUI_FINISHPAGE_NOREBOOTSUPPORT
  ;!insertmacro MUI_PAGE_FINISH


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
  WriteRegStr HKCR "mzDesktop.mzScript\DefaultIcon" "" "$INSTDIR\mzDesktop\images\icons\mz_script.ico"
  WriteRegStr HKCR "mzDesktop.mzScript\shell\open\command" "" '"$INSTDIR\mzDesktop.exe" "%1" %*'

  ;Assign mzd file type to mzDesktop
  WriteRegStr HKCR ".mzd" "" "mzDesktop.mzResults"
  WriteRegStr HKCR "mzDesktop.mzResults" "" "mzResults database"
  WriteRegStr HKCR "mzDesktop.mzResults\DefaultIcon" "" "$INSTDIR\mzDesktop\images\icons\mz_results.ico"
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

  Call SetupDotNetSectionIfNeeded
  


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



;----------------------------
; .NET installer.

; Usage
; 1 Call SetupDotNetSectionIfNeeded from .onInit function
;   This function will check if the required version 
;   or higher version of the .NETFramework is installed.
;   If .NET is NOT installed the section which installs dotnetfx is selected.
;   If .NET is installed the section which installs dotnetfx is unselected.
 
#!define SF_USELECTED  0
#!define SF_SELECTED   1
#!define SF_SECGRP     2
#!define SF_BOLD       8
#!define SF_RO         16
#!define SF_EXPAND     32
###############################
 
!define DOT_MAJOR 4
!define DOT_MINOR 0
 
; Lots of macro definitions went here.
 
Function SetupDotNetSectionIfNeeded
 
  StrCpy $0 "0"
  StrCpy $1 "SOFTWARE\Microsoft\.NETFramework" ;registry entry to look in.
  StrCpy $2 0
 
  StartEnum:
    ;Enumerate the versions installed.
    EnumRegKey $3 HKLM "$1\policy" $2
 
    ;If we don't find any versions installed, it's not here.
    StrCmp $3 "" noDotNet notEmpty
 
    ;We found something.
    notEmpty:
      ;Find out if the RegKey starts with 'v'.  
      ;If it doesn't, goto the next key.
      StrCpy $4 $3 1 0
      StrCmp $4 "v" +1 goNext
      StrCpy $4 $3 1 1
 
      ;It starts with 'v'.  Now check to see how the installed major version
      ;relates to our required major version.
      ;If it's equal check the minor version, if it's greater, 
      ;we found a good RegKey.
      IntCmp $4 ${DOT_MAJOR} +1 goNext yesDotNetReg
      ;Check the minor version.  If it's equal or greater to our requested 
      ;version then we're good.
      StrCpy $4 $3 1 3
      IntCmp $4 ${DOT_MINOR} yesDotNetReg goNext yesDotNetReg
 
    goNext:
      ;Go to the next RegKey.
      IntOp $2 $2 + 1
      goto StartEnum
 
  yesDotNetReg:
    ;Now that we've found a good RegKey, let's make sure it's actually
    ;installed by getting the install path and checking to see if the 
    ;mscorlib.dll exists.
    EnumRegValue $2 HKLM "$1\policy\$3" 0
    ;$2 should equal whatever comes after the major and minor versions 
    ;(ie, v1.1.4322)
    StrCmp $2 "" noDotNet
    ReadRegStr $4 HKLM $1 "InstallRoot"
    ;Hopefully the install root isn't empty.
    StrCmp $4 "" noDotNet
    ;build the actuall directory path to mscorlib.dll.
    StrCpy $4 "$4$3.$2\mscorlib.dll"
    IfFileExists $4 yesDotNet noDotNet
 
  noDotNet:
    ;${SelectSection} ${SECDOTNET}
    goto done
 
  yesDotNet:
    ;Everything checks out.  Go on with the rest of the installation.
    ;${UnSelectSection} ${SECDOTNET}
    goto done
 
  done:
    ;All done.
 
FunctionEnd
 
!define BASE_URL "http://download.microsoft.com/download"
; .NET Framework
; English
;!define URL_DOTNET_1033 "${BASE_URL}/a/a/c/aac39226-8825-44ce-90e3-bf8203e74006/dotnetfx.exe"
!define $URL_DOTNET "${BASE_URL}/a/a/c/aac39226-8825-44ce-90e3-bf8203e74006/dotnetfx.exe"
; ... If you need one not listed above you will have to visit the Microsoft Download site,
; select the language you are after and scan the page source to obtain the link.
 

 
LangString DESC_REMAINING ${LANG_ENGLISH} " (%d %s%s remaining)"
LangString DESC_PROGRESS ${LANG_ENGLISH} "%d.%01dkB/s" ;"%dkB (%d%%) of %dkB @ %d.%01dkB/s"
LangString DESC_PLURAL ${LANG_ENGLISH} "s"
LangString DESC_HOUR ${LANG_ENGLISH} "hour"
LangString DESC_MINUTE ${LANG_ENGLISH} "minute"
LangString DESC_SECOND ${LANG_ENGLISH} "second"
LangString DESC_CONNECTING ${LANG_ENGLISH} "Connecting..."
LangString DESC_DOWNLOADING ${LANG_ENGLISH} "Downloading %s"
LangString DESC_SHORTDOTNET ${LANG_ENGLISH} "Microsoft .Net Framework"
LangString DESC_LONGDOTNET ${LANG_ENGLISH} "Microsoft .Net Framework"
;LangString DESC_DOTNET_DECISION ${LANG_ENGLISH} "$(DESC_SHORTDOTNET) is required.$\nIt is strongly \
;  advised that you install$\n$(DESC_SHORTDOTNET) before continuing.$\nIf you choose to continue, \
;  you will need to connect$\nto the internet before proceeding.$\nWould you like to continue with \
;  the installation?"
LangString DESC_DOTNET_DECISION ${LANG_ENGLISH} "$(DESC_SHORTDOTNET) is required for mzDesktop to \
access .WIFF files; click 'OK' to have mzDesktop Setup download and install the latest .NET version."
LangString SEC_DOTNET ${LANG_ENGLISH} "$(DESC_SHORTDOTNET) "
LangString DESC_INSTALLING ${LANG_ENGLISH} "Installing"
LangString DESC_DOWNLOADING1 ${LANG_ENGLISH} "Downloading"
LangString DESC_DOWNLOADFAILED ${LANG_ENGLISH} "Download Failed:"
LangString ERROR_DOTNET_DUPLICATE_INSTANCE ${LANG_ENGLISH} "The $(DESC_SHORTDOTNET) Installer is \
  already running."
LangString ERROR_NOT_ADMINISTRATOR ${LANG_ENGLISH} "$(DESC_000022)"
LangString ERROR_INVALID_PLATFORM ${LANG_ENGLISH} "$(DESC_000023)"
LangString DESC_DOTNET_TIMEOUT ${LANG_ENGLISH} "The installation of the $(DESC_SHORTDOTNET) \
  has timed out."
LangString ERROR_DOTNET_INVALID_PATH ${LANG_ENGLISH} "The $(DESC_SHORTDOTNET) Installation$\n\
  was not found in the following location:$\n"
LangString ERROR_DOTNET_FATAL ${LANG_ENGLISH} "A fatal error occurred during the installation$\n\
  of the $(DESC_SHORTDOTNET)."
LangString PRODUCT_NAME ${LANG_ENGLISH} "mzDesktop"
LangString FAILED_DOTNET_INSTALL ${LANG_ENGLISH} "The installation of $(PRODUCT_NAME) will$\n \
  continue. However, it may not function properly $\nuntil $(DESC_SHORTDOTNET)$\nis installed."
 
 
Section $(SEC_DOTNET) SECDOTNET
    SectionIn RO
    IfSilent lbl_IsSilent
    !define DOTNETFILESDIR "Common\Files\MSNET"
    StrCpy $DOTNET_RETURN_CODE "0"
!ifdef DOTNET_ONCD_1033
    StrCmp "$OSLANGUAGE" "1033" 0 lbl_Not1033
    SetOutPath "$PLUGINSDIR"
    file /r "${DOTNETFILESDIR}\dotnetfx1033.exe"
    DetailPrint "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)..."
    ;Banner::show /NOUNLOAD "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)..."
    Banner::show /NOUNLOAD /set 76 "mzDestkop Setup is working..." "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)..."
    nsExec::ExecToStack '"$PLUGINSDIR\dotnetfx1033.exe" /q /c:"install.exe /noaspupgrade /q"'
    pop $DOTNET_RETURN_CODE
    Banner::destroy
    ;SetRebootFlag true
    Goto lbl_NoDownloadRequired
    lbl_Not1033:
!endif
; Insert Other language blocks here
 
    ; the following Goto and Label is for consistency.
    Goto lbl_DownloadRequired
    lbl_DownloadRequired:
    DetailPrint "$(DESC_DOWNLOADING1) $(DESC_SHORTDOTNET)..."
    MessageBox MB_ICONEXCLAMATION|MB_YESNO|MB_DEFBUTTON2 "$(DESC_DOTNET_DECISION)" /SD IDNO \
      IDYES +2 IDNO lbl_Done
    Abort
    ; "Downloading Microsoft .Net Framework"

    StrCpy $TARGETURL "http://download.microsoft.com/download/B/A/4/BA4A7E71-2906-4B2D-A0E1-80CF16844F5F/dotNetFx45_Full_setup.exe"
    DetailPrint $TARGETURL
    DetailPrint "$TARGETURL"
    AddSize 153600
    nsisdl::download /TRANSLATE "$(DESC_DOWNLOADING)" "$(DESC_CONNECTING)" \
       "$(DESC_SECOND)" "$(DESC_MINUTE)" "$(DESC_HOUR)" "$(DESC_PLURAL)" \
       "$(DESC_PROGRESS)" "$(DESC_REMAINING)" \
       /TIMEOUT=30000 "$TARGETURL" "$PLUGINSDIR\dotnetfx.exe"
    Pop $0
    StrCmp "$0" "success" lbl_continue
    DetailPrint "$(DESC_DOWNLOADFAILED) $0"
    Abort
 
    lbl_continue:
      DetailPrint "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)..."
      Banner::show /NOUNLOAD "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)..."
      ;Banner::show "$(DESC_INSTALLING) $(DESC_SHORTDOTNET)... $\n \ (This may take some time.)"
      nsExec::ExecToStack '"$PLUGINSDIR\dotnetfx.exe" /q /c:"install.exe /noaspupgrade /q"'
      pop $DOTNET_RETURN_CODE
      Banner::destroy
      ;SetRebootFlag true
      ; silence the compiler
      Goto lbl_NoDownloadRequired
      lbl_NoDownloadRequired:
 
      ; obtain any error code and inform the user ($DOTNET_RETURN_CODE)
      ; If nsExec is unable to execute the process,
      ; it will return "error"
      ; If the process timed out it will return "timeout"
      ; else it will return the return code from the executed process.
      StrCmp "$DOTNET_RETURN_CODE" "" lbl_NoError
      StrCmp "$DOTNET_RETURN_CODE" "0" lbl_NoError
      StrCmp "$DOTNET_RETURN_CODE" "3010" lbl_NoError
      StrCmp "$DOTNET_RETURN_CODE" "8192" lbl_NoError
      StrCmp "$DOTNET_RETURN_CODE" "error" lbl_Error
      StrCmp "$DOTNET_RETURN_CODE" "timeout" lbl_TimeOut
      ; It's a .Net Error
      StrCmp "$DOTNET_RETURN_CODE" "4101" lbl_Error_DuplicateInstance
      StrCmp "$DOTNET_RETURN_CODE" "4097" lbl_Error_NotAdministrator
      StrCmp "$DOTNET_RETURN_CODE" "1633" lbl_Error_InvalidPlatform lbl_FatalError
      ; all others are fatal
 
    lbl_Error_DuplicateInstance:
    DetailPrint "$(ERROR_DOTNET_DUPLICATE_INSTANCE)"
    GoTo lbl_Done
 
    lbl_Error_NotAdministrator:
    DetailPrint "$(ERROR_NOT_ADMINISTRATOR)"
    GoTo lbl_Done
 
    lbl_Error_InvalidPlatform:
    DetailPrint "$(ERROR_INVALID_PLATFORM)"
    GoTo lbl_Done
 
    lbl_TimeOut:
    DetailPrint "$(DESC_DOTNET_TIMEOUT)"
    GoTo lbl_Done
 
    lbl_Error:
    DetailPrint "$(ERROR_DOTNET_INVALID_PATH)"
    GoTo lbl_Done
 
    lbl_FatalError:
    DetailPrint "$(ERROR_DOTNET_FATAL)[$DOTNET_RETURN_CODE]"
    GoTo lbl_Done
 
    lbl_Done:
    DetailPrint "$(FAILED_DOTNET_INSTALL)"
    lbl_NoError:
    lbl_IsSilent:
    
    DetailPrint "Running registrator for .WIFF files..."
    DetailPrint $INSTDIR  
    nsExec::ExecToLog '"$INSTDIR\regWiff.bat" "$INSTDIR\WiffReaderCOM.dll"'

    DetailPrint "Running registrator for Agilent files..."
    nsExec::ExecToLog '"$INSTDIR\regWiff.bat" "$INSTDIR\AgilentReader.dll"'
    
    DetailPrint "Asking about MSFR."
    MessageBox MB_ICONEXCLAMATION|MB_YESNO|MB_DEFBUTTON2 "Thermo MSFile Reader is required for .RAW file access.  Install now?"  IDYES lbl_NotQuiteDone IDNO lbl_ReallyDone
    lbl_NotQuiteDone:
    ;ExecWait 'msiexec /i "$INSTDIR\thermo msfilereader.msi" /qb' $0
    ExecWait '$INSTDIR\MSFileReader.exe' $0
    DetailPrint "$0"
    DetailPrint "MS File Reader installation complete."

    lbl_ReallyDone:
    DetailPrint "Done!"
 
SectionEnd

 
 

;!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
;!insertmacro MUI_DESCRIPTION_TEXT ${SECDOTNET} $(DESC_LONGDOTNET)
;!insertmacro MUI_FUNCTION_DESCRIPTION_END