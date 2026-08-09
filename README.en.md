<p align="center">
  <img src="study_cat_icon.ico" width="80" alt="logo" />
  <h1 align="center">Focus Tool</h1>
  <p align="center">A Windows desktop tool that helps you truly focus: an always-on-top countdown overlay + automatic blocking of Zhihu and Bilibili</p>
  <p align="center">
    <a href="README.md">中文</a> | <b>English</b>
  </p>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-green" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-orange" />
  <a href="https://github.com/Cpuritan/Focus-Tool/releases"><img alt="Release" src="https://img.shields.io/badge/download-Releases-brightgreen" /></a>
</p>

---

## 🖼 Preview

![FocusTool in action](screen.png)

> During a focus session: the semi-transparent countdown hovers at the top of the screen, Zhihu and Bilibili are unreachable in the browser, and there is no taskbar window to close.

---

## ✨ Features

- **Always-on-top countdown overlay**: a semi-transparent, click-through countdown hovers at the top of your screen — always visible, never in the way
- **Automatic distraction blocking**: while a session runs, the `hosts` file is modified to block Zhihu, Bilibili and related domains; it is restored automatically when the session ends
- **Deliberate exit friction**:
  - The overlay does **not** appear in the taskbar or in the Alt+Tab switcher
  - "Close window" from the taskbar and `Alt+F4` are **both ignored**
  - The only way to quit mid-session is to **end the process in Task Manager** — helping you stay committed
- **Watchdog protection**: even if the main process is force-killed, an independent watchdog process immediately restores the `hosts` file
- **Single instance**: launching a second copy just shows a "already running" message
- **Flexible time input**: `25` (minutes), `1h30m`, `1:30:00` — up to 360 minutes per session
- **Graceful exit**: the timer restores the network automatically when finished, and on shutdown/logoff as well

## 📥 Download & Usage

### Download

Grab the latest `FocusTool.exe` from [Releases](https://github.com/Cpuritan/Focus-Tool/releases). No installation required — just double-click to run.

### How to use

1. Double-click `FocusTool.exe`
2. On first launch, a **UAC prompt** appears (admin rights are needed to modify the `hosts` file) — click **Yes**
3. Enter a focus duration in minutes (max 360) and click **Start**
4. The countdown overlay appears at the top of the screen; Zhihu and Bilibili are blocked during the session
5. When the countdown ends, the app exits automatically and websites are restored

### How to quit / end a session

| Scenario | How |
| --- | --- |
| Normal finish | The countdown runs out; the app exits and restores websites automatically |
| Force quit mid-session | Open **Task Manager** → find `FocusTool.exe` → **End task** (the `hosts` file is restored automatically) |
| Manually restore websites | Run `FocusTool.exe --restore` as administrator |

> ⚠️ **Note**: you cannot close the app via the taskbar or `Alt+F4` mid-session. This is intentional friction designed to help you stick with your focus session. Think twice before interrupting yourself.

## 🔧 How it works

1. **Countdown overlay**: a borderless, always-on-top, click-through layered window (`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW`) rendered via the Win32 API
2. **Site blocking**: a managed block delimited by `# >>> FocusTool managed block >>>` is appended to `C:\Windows\System32\drivers\etc\hosts`, mapping Zhihu/Bilibili domains to `0.0.0.0` and `::1`, followed by a DNS flush
3. **Watchdog**: a detached watchdog process monitors the main process; no matter how the main process ends (including being force-killed), the watchdog ensures the `hosts` file is restored

## 🛠 Build from source

**Requirements**: Python 3.11+, Windows 10/11

```bash
pip install pyinstaller pillow
pyinstaller focus_tool.spec --noconfirm
```

The build output is `dist/FocusTool.exe`.

### Project layout

```
├── focus_tool.py          # Main program (all logic)
├── focus_tool.spec        # PyInstaller build config
├── study_cat_icon.ico     # App icon
├── README.md              # 中文说明
└── README.en.md           # English documentation
```

## ❓ FAQ

**Q: Why does it require administrator privileges?**
Modifying the `hosts` file requires admin rights — that's a Windows security mechanism.

**Q: Which sites are blocked?**
The built-in domain list covers all related domains of Zhihu (`zhihu.com`, `zhimg.com`, etc.) and Bilibili (`bilibili.com`, `b23.tv`, `bilivideo.com`, etc.).

**Q: The `hosts` file wasn't restored after a force kill?**
The watchdog normally restores it within seconds. If not, run `FocusTool.exe --restore` as administrator to restore it manually.

**Q: Can I click the overlay?**
No. The overlay is click-through (`WS_EX_TRANSPARENT`), so it never interferes with your other apps.

## 📄 License

[MIT](LICENSE) © Cpuritan
