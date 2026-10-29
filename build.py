import os, sys, shutil, subprocess, platform

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

NAME = "MemoryBot"
system = platform.system()

if system == "Linux":
    print("linux: gebruik install.sh")
    sys.exit(0)

subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "pyinstaller", "pillow", "selenium"])

from PIL import Image

img = Image.open("icon.png").convert("RGBA")
if system == "Windows":
    icon = "icon.ico"
    img.save(icon, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
else:
    icon = "icon.icns"
    img.resize((1024, 1024)).save(icon)

for folder in ("build", "dist"):
    shutil.rmtree(folder, ignore_errors=True)

sep = os.pathsep
args = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
    "--name", NAME, "--icon", icon,
    "--add-data", "icon.png" + sep + ".",
    "--hidden-import", "bot",
    "--hidden-import", "app",
    "--hidden-import", "updater",
    "--collect-all", "selenium",
    "--collect-all", "certifi",
]
if os.path.isdir("lists"):
    args += ["--add-data", "lists" + sep + "lists"]
if system == "Darwin":
    args += ["--osx-bundle-identifier", "local.memorybot"]
args.append("launcher.py")
subprocess.check_call(args)

if system == "Windows":
    iscc = shutil.which("ISCC") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    subprocess.check_call([iscc, "installer.iss"])
    print("klaar: installer_out\\MemoryBot-Setup.exe")

elif system == "Darwin":
    app = os.path.join("dist", NAME + ".app")
    subprocess.check_call(["codesign", "--force", "--deep", "--sign", "-", app])

    stage = "dmg_stage"
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    shutil.copytree(app, os.path.join(stage, "Memory Bot.app"), symlinks=True)
    os.symlink("/Applications", os.path.join(stage, "Applications"))
    with open(os.path.join(stage, "LEES MIJ.txt"), "w", encoding="utf-8") as f:
        f.write(
            "eerste keer openen:\n"
            "1. sleep Memory Bot naar de map Apps (Programma's)\n"
            "2. dubbelklik Memory Bot. krijg je een melding dat de app niet geopend kan worden: klik OK\n"
            "3. open Systeeminstellingen > Privacy en beveiliging, scroll naar beneden, klik 'Toch openen'\n"
            "4. open de app opnieuw. daarna werkt hij gewoon.\n"
        )

    dmg = "MemoryBot-" + platform.machine() + ".dmg"
    if os.path.exists(dmg):
        os.remove(dmg)
    subprocess.check_call(["hdiutil", "create", "-volname", "Memory Bot", "-srcfolder", stage, "-ov", "-format", "UDZO", dmg])
    shutil.rmtree(stage)
    print("klaar: " + dmg)
