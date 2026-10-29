import os, sys, re, shutil, importlib.util

INSTALLER_API = 1
MODULES = ("bot", "updater")

import bot as bundled_bot


def num(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run():
    bundled_bot.INSTALLER_API = INSTALLER_API
    app = None
    code = os.path.join(bundled_bot.PARENT, "code")
    paths = {}
    for n in ("bot", "updater", "app"):
        paths[n] = os.path.join(code, n + ".py")

    if all(os.path.exists(p) for p in paths.values()):
        saved = {}
        for n in MODULES:
            saved[n] = sys.modules.get(n)
        try:
            with open(paths["bot"], encoding="utf-8") as f:
                m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', f.read())
            if m and num(m.group(1)) > num(bundled_bot.APP_VERSION):
                for n in MODULES:
                    sys.modules.pop(n, None)
                new_bot = load("bot", paths["bot"])
                new_bot.INSTALLER_API = INSTALLER_API
                load("updater", paths["updater"])
                app = load("app", paths["app"])
        except Exception:
            app = None
            for n in MODULES:
                sys.modules.pop(n, None)
                if saved[n] is not None:
                    sys.modules[n] = saved[n]
            sys.modules.pop("app", None)
            bad = code + ".bad"
            shutil.rmtree(bad, ignore_errors=True)
            try:
                os.rename(code, bad)
            except OSError:
                pass

    if app is None:
        import updater
        import app

    app.main()


if __name__ == "__main__":
    run()
