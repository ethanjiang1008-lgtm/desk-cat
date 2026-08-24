# 双猫桌面宠物 🐱🐱

在 Windows 桌面上同时生活着两只真实宠物猫：各自拥有独立的行为、状态与生活节奏，共享桌面活动空间，可彼此互动、与用户互动。即使用户什么都不做，两只猫也会自己走动、蹲坐、舔毛、打滚、睡觉、喝水、吃饭、伸懒腰，偶尔互相蹭、一起睡觉、互相打闹。

## 功能一览

- **透明无边框置顶窗口**：宠物悬浮桌面，透明区域逐像素点击穿透（不挡桌面、不抢焦点）
- **两只独立行为系统**：各自的状态机 + 权重 + 条件 + 随机性，不同步
- **8 个单猫动作**：走动 / 打滚 / 舔毛 / 睡觉 / 伸懒腰 / 喝水 / 吃饭 / 蹲坐
- **3 个双猫互动**：互相蹭 / 一起睡觉 / 互相打闹
- **状态系统**：饥饿 / 口渴 / 精力 / 心情 / 亲密度 / 双猫关系（0–100，随时间与互动变化）
- **走动方向自动水平翻转**：单套走动素材即可双向行走
- **用户交互**：单击（随机反应）/ 双击（兴奋/翻滚）/ 拖动 / 右键菜单（喂食·喝水·抚摸·设置·暂停·隐藏·退出）
- **时间系统**：喝水提醒 / 喂食时间 / 睡眠时间（到点猫自己靠近并显示气泡提醒）
- **多显示器**：可选主/指定显示器
- **系统托盘**：显示·隐藏·暂停活动·暂停提醒·设置·退出
- **设置页**：宠物名称/大小/速度/活动范围/显示器、喝水/喂食/睡眠时间、互动开关、声音开关
- **首次启动向导**：命名 → 确认 → 活动区域 → 完成，猫从屏幕两侧走入
- **本地持久化**：关闭即保存全部状态，重启按真实时间差重算饥渴/精力等属性
- **离线运行**：核心行为系统完全本地，断网照常生活

## 素材处理

视频素材已用 AI 抠像（u2netp）转为带 alpha 通道的动画 WebP（背景透明、边缘干净、无黑/白边），内置于 `assets/` 目录，由 QMovie 逐帧播放。

## 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

## 构建为 Windows .exe

依赖 GitHub Actions（windows-latest）自动构建：

1. 把本目录推到你的 GitHub 仓库（公开或私有均可）。
2. 推送 `main` 分支后，`build-windows-exe` 工作流自动运行 PyInstaller 打包。
3. 在仓库 **Actions** 页找到运行 → **Artifacts** 下载 `DualCatPet-exe`，或在 **Releases** 页下载已发布的 `.exe`。

也可在本地 Windows 上直接构建：

```bash
pip install -r requirements.txt pyinstaller
pyinstaller build.spec --noconfirm --clean
# 产物在 dist/双猫桌面宠物.exe
```

## 目录结构

```
dualcat_pet/
├─ main.py              入口
├─ config.py           配置/常量/资源路径
├─ state.py            持久化 + 重启按真实时间重算
├─ behavior.py         行为状态机与加权调度器
├─ cat.py              单只猫行为控制器
├─ interactions.py     双猫互动导演
├─ cat_sprite.py       猫咪精灵（QMovie+翻转+缩放+alpha）
├─ pet_window.py       透明桌宠窗口 + 逐像素点击穿透 + 主循环
├─ settings_dialog.py 设置对话框
├─ first_run.py        首次启动向导
├─ tray.py             系统托盘
├─ sound.py            声音系统（预留接口）
├─ build.spec          PyInstaller 配置
├─ requirements.txt
├─ .github/workflows/build.yml   自动构建 exe
└─ assets/
   ├─ catA/*.webp      猫A 的 8 个动作
   ├─ catB/*.webp      猫B 的 8 个动作
   ├─ both/*.webp      3 个双猫互动动作
   └─ icons/app.ico    应用图标
```

## 可扩展（当前未实现，已预留接口）

AI 聊天、宠物记忆/成长/等级、更多动作、自定义家具/玩具、多只宠物、自定义房间、宠物语音、自然语言指令、宠物声音素材。
