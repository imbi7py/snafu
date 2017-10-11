!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"

!define MUI_PAGE_CUSTOMFUNCTION_SHOW Welcome
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE WelcomeLeave
!insertmacro MUI_PAGE_WELCOME

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"


!define NAME 'SNAFU Python Manager'

!define UNINSTALL_REGKEY \
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\SNAFU'

!define UNINSTALL_EXE "$INSTDIR\Uninstall.exe"

!define KBCODE 'KB2999226'

!define PYTHONVERSION '3.6'

!define SNAFU_SHIM_STRING "$INSTDIR\lib\python\python.exe$\r$\n-m$\r$\nsnafu"


ShowInstDetails hide
ManifestSupportedOS all

Name "${NAME}"
OutFile "snafu-setup.exe"
InstallDir "$LOCALAPPDATA\Programs\SNAFU"

Var InstallsPythonCheckbox
Var InstallsPython

Function Welcome
    ${IfNot} ${AtLeastWinVista}
        MessageBox MB_OK "SNAFU only supports Windows Vista or above."
        Quit
    ${EndIf}

    ${NSD_CreateCheckbox} 120u -18u 50% 12u \
        "Set up Python ${PYTHONVERSION} (needs Internet connection)"
    Pop $InstallsPythonCheckbox
    SetCtlColors $InstallsPythonCheckbox "" ${MUI_BGCOLOR}
    ${NSD_SetState} $InstallsPythonCheckbox $InstallsPython
FunctionEnd

Function WelcomeLeave
    ${NSD_GetState} $InstallsPythonCheckbox $InstallsPython
FunctionEnd

Function InstallMSU
    ${If} ${AtLeastWin10}
        Return
    ${ElseIf} ${IsWin8.1}
        StrCpy $0 '8.1'
    ${ElseIf} ${IsWin8}
        StrCpy $0 '8-RT'
    ${ElseIf} ${IsWin7}
        StrCpy $0 '6.1'
    ${ElseIf} ${IsWinVista}
        StrCpy $0 '6.0'
    ${EndIf}

    ${If} ${RunningX64}
        StrCpy $1 'x64'
    ${Else}
        StrCpy $1 'x32'
    ${EndIf}

    DetailPrint "Installing Windows update ${KBCODE} for your system..."
    nsExec::ExecToLog "wusa /quiet /norestart \
        $\"$INSTDIR\lib\snafusetup\Windows$0-${KBCODE}-$1.msu$\""
FunctionEnd

Section "SNAFU Python Manager"
    # Clean up lib directory from previous installtion to prevent version
    # confliction. Other directories are not touched because they contain
    # only shims, and may have user-generated files in them.
    Rmdir /r "$INSTDIR\lib"

    CreateDirectory "$INSTDIR"
    SetOutPath "$INSTDIR"

    File /r 'snafu\*'
    CreateDirectory "$INSTDIR\scripts"

    # Write snafu shim.
    FileOpen $0 "$INSTDIR\cmd\snafu.shim" w
    FileWrite $0 "${SNAFU_SHIM_STRING}"
    FileClose $0

    # Ensure appropriate CRT is installed.
    Call InstallMSU

    # Install Py launcher.
    DetailPrint "Installing Python Launcher (py.exe)..."
    nsExec::ExecToLog "msiexec /i $\"$INSTDIR\lib\snafusetup\py.msi$\" /quiet"

    # Setup environment.
    DetailPrint "Configuring environment..."
    nsExec::ExecToLog "$\"$INSTDIR\lib\python\python.exe$\" \
        $\"$INSTDIR\lib\snafusetup\env.py$\" $\"$INSTDIR$\""

    # Run SNAFU to install Python (if told to).
    ${If} $InstallsPython == ${BST_CHECKED}
        DetailPrint "Installing Python ${PYTHONVERSION}..."
        nsExec::ExecToLog "$\"$INSTDIR\lib\python\python.exe$\" \
            -m snafu install ${PYTHONVERSION}"
        nsExec::ExecToLog "$\"$INSTDIR\lib\python\python.exe$\" \
            -m snafu use ${PYTHONVERSION}"
    ${EndIf}

    WriteUninstaller "${UNINSTALL_EXE}"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" "DisplayName" "${NAME}"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" "Publisher" "Tzu-ping Chung"
    WriteRegStr HKLM "${UNINSTALL_REGKEY}" "UninstallString" "${UNINSTALL_EXE}"
SectionEnd


Section "un.Uninstaller"
    nsExec::ExecToLog "$\"$INSTDIR\lib\python\python.exe$\" \
        $\"$INSTDIR\lib\snafusetup\env.py$\" $\"$INSTDIR$\" \
        --uninstall"
    Rmdir /r "$INSTDIR"
    DeleteRegKey HKLM "${UNINSTALL_REGKEY}"
SectionEnd
