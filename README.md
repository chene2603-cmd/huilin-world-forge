```markdown
# 🏔️ 慧凌世界地形系统 (Huilin World Forge)

> **AI 驱动的虚拟世界内容生产框架**  
> 一次定义世界法则，批量生成风格统一的场景、对白与视频。

## 🧭 核心思想
将虚拟世界的构建过程拆分为 **5 个严格分层**，每一层只做一件事，层与层之间通过结构化协议文件传递信息。  
架构师只需在顶层“烧录”一次世界法则，后续所有产出都在约束下自动或半自动完成，确保**视觉、声纹、叙事逻辑高度一致**。

## 🗺️ 架构分层

| 层级 | 目录 | 职责 |
|------|------|------|
| **0** | `0_CORE_PROTOCOL` | 定义世界法则（地形、生态、实体、文明）并编译为不可变协议 |
| **1** | `1_TERRAIN_BLUEPRINTS` | 读取协议，将自然语言场景转为结构化分镜蓝图 |
| **2** | `2_RENDER_ENGINE` | 根据蓝图生成 Stable Diffusion 标准化提示词（含 LoRA 绑定） |
| **3** | `3_SOUND_GENERATOR` | 管理角色声纹，生成 TTS 合成任务；控制背景音乐 |
| **4** | `4_WORLD_BUILDER` | 使用 FFmpeg 自动装配图片、音频、字幕为最终视频 |
| **5** | `5_SCANNER` | 终极质检：校验视觉、声纹、字幕、时长是否符合协议 |

## 🚀 快速开始

### 1. 克隆仓库
```bash
git clone https://github.com/yourname/ai-terrain-system.git
cd ai-terrain-system
```

2. 安装依赖

· Python 3.8+
· FFmpeg（需加入 PATH）
· （可选）Stable Diffusion WebUI / API 或 Midjourney 订阅
· （可选）TTS 引擎（如 Bark、VITS）

3. 配置全局参数

编辑根目录下的 config.yaml，设置模型路径、输出目录等。

4. 烧录世界法则

```bash
cd 0_CORE_PROTOCOL
python protocol_compiler.py
```

按提示输入世界描述，将生成 example_world_protocol.json。

5. 生成分镜蓝图

```bash
cd ../1_TERRAIN_BLUEPRINTS
python blueprint_generator.py
```

交互式创建镜头蓝图，产出 JSON + 对白文件 + 字幕模板。

6. 构建渲染提示词

```bash
cd ../2_RENDER_ENGINE
python sd_control_console.py
```

选择蓝图，输出标准化 SD 提示词（可配合 WebUI 批量出图）。

7. 语音合成

```bash
cd ../3_SOUND_GENERATOR
python tts_control_console.py
```

生成 TTS 任务配置，接入引擎后得到 _dialogue.wav。

8. 视频装配

将渲染图片、音频、字幕放入对应剧集目录，运行：

```bash
cd ../4_WORLD_BUILDER
python assembly_workflow.py
```

自动合成 Episode_01_FINAL.mp4。

9. 终极校验

```bash
cd ../5_SCANNER
python stability_scanner.py
```

扫描报告将显示一切是否仍遵守核心协议。

⚙️ 配置参考

项目全局设置集中在根目录 config.yaml 中，包括：

· 协议文件默认路径
· 渲染引擎类型（SD/MJ）
· 声纹模型目录
· 输出视频分辨率等

首次使用前请根据环境修改。

📁 项目结构

```
ai-terrain-system/
├── README.md
├── LICENSE
├── config.yaml
├── 0_CORE_PROTOCOL/
│   ├── protocol_compiler.py
│   └── example_world_protocol.json
├── 1_TERRAIN_BLUEPRINTS/
│   ├── blueprint_generator.py
│   └── Episode_01/        (示例剧集)
├── 2_RENDER_ENGINE/
│   ├── sd_control_console.py
│   ├── mj_prompt_builder.py   (待扩展)
│   ├── lora/
│   └── references/
├── 3_SOUND_GENERATOR/
│   ├── tts_control_console.py
│   ├── voice_cloning/
│   └── bgm/
├── 4_WORLD_BUILDER/
│   ├── assembly_workflow.py
│   └── exports/
└── 5_SCANNER/
    └── stability_scanner.py
```

🧩 核心理念

“规则锁定，量产可控”
顶层协议一旦烧录，下层所有施工都在其约束下进行，从根本上杜绝风格漂移和设定矛盾。

🤝 贡献

欢迎提出 Issue 或 PR，共同完善这个 AI 内容生产框架。

📄 许可证

本项目使用 MIT License，详见 LICENSE 文件。

