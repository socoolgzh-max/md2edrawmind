; md2edrawmind 安装器（Inno Setup 6）
; 由 tools/build_installer.py 调用，或手工：
;   ISCC.exe /DStageDir="<打包输出目录>" tools\installer.iss
;
; 需要先跑 tools/build_desktop.py 生成 dist\md2edrawmind\。
;
; 说明：Inno Setup 不自带简体中文语言文件，官方仓库里的 ChineseSimplified.isl
; 属于 Unofficial 目录且需要联网获取，因此向导界面使用英文；但应用名、
; 快捷方式名、附加任务说明与许可页说明都是中文，用户实际看到的是中文条目。

#define AppName        "md2edrawmind"
#define AppVersion     "1.0.0"
#define AppPublisher   "socoolgzh-max"
#define AppURL         "https://github.com/socoolgzh-max/md2edrawmind"
#define AppExeName     "md2edrawmind.exe"

#ifndef StageDir
  #define StageDir "..\dist\md2edrawmind"
#endif

[Setup]
AppId={{7E2A5C41-9B3D-4A86-9F1E-2C5D8B7A4E10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
; PrivilegesRequired=lowest => 装到 %LOCALAPPDATA%\Programs，不弹 UAC，普通用户可装
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\dist
OutputBaseFilename={#AppName}-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=..\docs\icon.ico
LicenseFile=..\LICENSE
InfoBeforeFile=..\docs\install-notes.txt
MinVersion=10.0
; 卸载时提示用户是否保留转换产生的临时文件
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: checkedonce
Name: "runnow"; Description: "安装完成后立即启动 {#AppName}"; GroupDescription: "附加任务："; Flags: checkedonce

[Files]
; 整个打包目录（_internal 里含 Python 运行时、随包 Node、mathjax、前端资源）
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "把带公式的 Markdown 转成思维导图可导入的 Word"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "立即启动 {#AppName}"; Flags: nowait postinstall skipifsilent; Tasks: runnow

[UninstallDelete]
; 启动日志不属于安装内容，卸载时一并清理
Type: filesandordirs; Name: "{localappdata}\md2edrawmind"
