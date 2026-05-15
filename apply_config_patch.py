from auto_log_wrap import func_log

#!/usr/bin/env python3
"""
补丁脚本：自动为核心模块注入 config.yaml 读取逻辑。
运行一次后，所有模块将统一从根目录 config.yaml 获取路径和参数。
"""

import re
from pathlib import Path

# 定义每个模块需要替换的 main 代码块
# key: 相对文件路径
# value: 新的 if __name__ == "__main__": 之后的完整代码（不包含该行本身）
PATCHES = {
    "0_CORE_PROTOCOL/protocol_compiler.py": '''
import sys, json, yaml
from pathlib import Path

config = yaml.safe_load(open("../config.yaml", encoding="utf-8"))
protocol_dir = Path(config["paths"]["protocol_dir"])
protocol_name = config["paths"]["default_protocol"]
protocol_path = protocol_dir / f"{protocol_name}.json"

if not protocol_path.exists():
    print(f"协议文件 {protocol_path} 不存在，使用内置模板生成...")
    concept = input("请输入世界构想（直接回车使用默认）: ").strip()
    if not concept:
        concept = "一个中土风格的世界，有高山、森林、海洋，文明处于铁器时代"
    # 内置最小协议模板
    template = {
        "world_name": "慧凌试做界",
        "seed": 20260515,
        "map_size": [512, 512],
        "height_rules": [
            {"min_height": -500, "max_height": 0, "coverage": 0.3, "terrain_types": ["ocean"]},
            {"min_height": 0, "max_height": 300, "coverage": 0.5, "terrain_types": ["plain", "forest"]},
            {"min_height": 300, "max_height": 3000, "coverage": 0.2, "terrain_types": ["mountain"]}
        ],
        "biomes": [
            {"name": "temperate_forest", "temperature_range": [5,22], "humidity_range": [40,80], "allowed_terrains": ["plain","forest"], "vegetation_density": 0.8}
        ],
        "resources": [
            {"name": "iron_ore", "biome_affinity": ["temperate_forest"], "rarity": 0.4, "min_depth": -50}
        ],
        "civilization": {
            "max_city_radius": 5.0,
            "preferred_terrains": ["plain"],
            "forbidden_biomes": [],
            "tech_level": 3
        },
        "metadata": {"compiled_at": "2026-05-15", "architect": "user"}
    }
    protocol = template
    protocol_dir.mkdir(parents=True, exist_ok=True)
    with open(protocol_path, "w", encoding="utf-8") as f:
        json.dump(protocol, f, ensure_ascii=False, indent=2)
    print(f"✅ 协议已生成: {protocol_path}")
else:
    with open(protocol_path, "r") as f:
        protocol = json.load(f)
    print(f"📜 已加载协议: {protocol['world_name']}")

# 如果有校验函数，可在此调用
# ProtocolCompiler.validate_protocol(protocol)
''',

    "1_TERRAIN_BLUEPRINTS/blueprint_generator.py": '''
import yaml, json
from pathlib import Path

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
protocol_dir = config["paths"]["protocol_dir"]
protocol_name = config["paths"]["default_protocol"]
protocol_path = f"../{protocol_dir}/{protocol_name}.json"

generator = BlueprintGenerator(protocol_path)
episode = config["paths"]["default_episode"]
output_dir = Path(config["paths"]["blueprint_dir"]) / episode

print(f">>> 蓝图生成模式 - 剧集: {episode} <<<")
while True:
    shot_id = input("镜头ID (如 SC-001，回车结束): ").strip()
    if not shot_id:
        break
    scene = input("场景描述: ").strip()
    dialogue = input("对白: ").strip()
    emotion = input("情绪: ").strip() or "neutral"
    camera = input("镜头运动: ").strip() or "static"
    dur = input("时长(秒): ").strip() or "4.0"
    bp = generator.generate_shot_blueprint(scene, shot_id, dialogue, emotion, camera, float(dur))
    generator.save_blueprint(bp, output_dir)
''',

    "2_RENDER_ENGINE/sd_control_console.py": '''
import yaml, json
from pathlib import Path

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
protocol_path = f"../{config['paths']['protocol_dir']}/{config['paths']['default_protocol']}.json"
builder = SDPromptBuilder(protocol_path)

while True:
    bp_path = input("蓝图路径 (q 退出): ").strip()
    if bp_path.lower() == "q":
        break
    pos, neg, meta = builder.build_prompt(bp_path)
    print(f"\\n--- {meta['shot_id']} 正向提示词 ---\\n{pos}\\n")
    print(f"--- 负向提示词 ---\\n{neg}\\n")
    export = input("导出txt? (y/n): ").strip().lower()
    if export == "y":
        builder.export_prompt_file(bp_path)
''',

    "3_SOUND_GENERATOR/tts_control_console.py": '''
import yaml, json
from pathlib import Path

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
protocol_path = f"../{config['paths']['protocol_dir']}/{config['paths']['default_protocol']}.json"
voice_dir = config["paths"]["voice_models_dir"]
controller = TTSController(protocol_path, voice_dir)

while True:
    mode = input("\\n模式：1-单个蓝图 2-整集批量 (q 退出): ").strip()
    if mode.lower() == "q":
        break
    if mode == "1":
        bp = input("蓝图JSON路径: ").strip()
        if Path(bp).exists():
            controller.generate_dialogue_audio(bp)
        else:
            print("文件不存在。")
    elif mode == "2":
        ep = input("剧集目录路径: ").strip()
        if Path(ep).exists():
            controller.batch_generate_from_episode(ep)
        else:
            print("目录不存在。")
''',

    "4_WORLD_BUILDER/assembly_workflow.py": '''
import yaml
from pathlib import Path

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
episode_dir = f"../{config['paths']['blueprint_dir']}/{config['paths']['default_episode']}"
output_dir = config["paths"]["exports_dir"]
builder = AssemblyWorkflow(episode_dir, output_dir)
builder.assemble(config["paths"]["default_episode"])
''',

    "5_SCANNER/stability_scanner.py": '''
import yaml
from pathlib import Path

with open("../config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
protocol_path = f"../{config['paths']['protocol_dir']}/{config['paths']['default_protocol']}.json"
episode_dir = f"../{config['paths']['blueprint_dir']}/{config['paths']['default_episode']}"
scanner = WorldStabilityScanner(protocol_path)
scanner.full_scan(episode_dir)
'''
}

def apply_patch(filepath, new_main_code):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 匹配 if __name__ == "__main__": 后面的所有内容（包括该行）
    pattern = r'(if\s+__name__\s*==\s*"__main__"\s*:).*'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print(f"⚠️ {filepath} 中未找到 if __name__ == '__main__': 块，跳过。")
        return False

    # 替换为新的 main 块
    new_block = f'if __name__ == "__main__":\n{new_main_code}'
    new_content = content[:match.start()] + new_block + "\n"
    # 保留原文件末尾可能存在的其他内容？没有，直接截断到 match 之前，因为原代码整个文件就到这里结束
    # 保险起见，加上原始文件可能有的尾随空白
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ 补丁应用成功: {filepath}")
    return True

def main():
    print("=== 慧凌世界地形系统 - 配置补丁应用工具 ===")
    print("将自动为所有核心模块注入 config.yaml 读取逻辑。")
    print("原文件将被修改，建议先备份 (git commit)。")
    input("按回车键继续...")

    for relative_path, code in PATCHES.items():
        full_path = Path(relative_path)
        if not full_path.exists():
            print(f"❌ 文件不存在: {relative_path}")
            continue
        apply_patch(full_path, code)

    print("\n🎉 全部补丁应用完成！现在所有模块都将从根目录 config.yaml 读取配置。")

if __name__ == "__main__":
    main()