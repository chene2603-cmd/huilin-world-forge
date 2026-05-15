from auto_log_wrap import func_log

"""
慧凌世界地形系统 - 蓝图生成器 v1.0
根据核心世界协议和场景描述，生成机器可读的分镜建造蓝图。
蓝图驱动下游渲染、对白、音效等模块。
"""

import json
from pathlib import Path
from typing import Dict, Optional
import sys

class BlueprintGenerator:
    """加载核心协议，产出镜头蓝图"""

    def __init__(self, protocol_path: str):
        """初始化并加载世界协议"""
        protocol_file = Path(protocol_path)
        if not protocol_file.exists():
            raise FileNotFoundError(f"协议文件不存在: {protocol_path}")
        with open(protocol_file, 'r', encoding='utf-8') as f:
            self.protocol = json.load(f)
        print(f"[蓝图生成器] 已载入世界协议: {self.protocol.get('world_name', '未命名世界')}")

    def generate_shot_blueprint(self, scene_description: str, shot_id: str, 
                                dialogue: str = "", emotion: str = "neutral",
                                camera_move: str = "static", duration: float = 4.0) -> Dict:
        """
        生成单个镜头的建造蓝图。
        
        参数：
            scene_description: 场景自然语言描述
            shot_id: 镜头编号，如 SC-001
            dialogue: 对白文本（可选）
            emotion: 说话情绪（可选）
            camera_move: 镜头运动描述
            duration: 镜头时长（秒）
        
        返回：
            结构化蓝图字典
        """
        # 提取协议中的固定约束
        world_constants = self.protocol.get('world_constants', {})
        entity_defs = self.protocol.get('entity_definitions', {})
        style_lock = self.protocol.get('render_style_lock', {})

        # 构造视觉提示词骨架（为下游 render engine 准备）
        visual_prompt_base = (
            f"{style_lock.get('visual_style', 'concept art')}, "
            f"{scene_description}"
        )

        # 如果有实体定义，拼入实体视觉哈希
        if entity_defs:
            entity_tags = []
            for entity_id, entity_data in entity_defs.items():
                if 'visual_hash' in entity_data:
                    entity_tags.append(f"<{entity_id}: {entity_data['visual_hash']}>")
            if entity_tags:
                visual_prompt_base += ", featuring " + ", ".join(entity_tags)

        # 组装完整蓝图
        blueprint = {
            "SHOT_ID": shot_id,
            "SCENE_DESCRIPTION": scene_description,
            "VISUAL_PROMPT_BASE": visual_prompt_base,
            "DIALOGUE": dialogue,
            "DIALOGUE_EMOTION": emotion,
            "CAMERA_MOVE": camera_move,
            "DURATION_SEC": duration,
            "PROTOCOL_SNAPSHOT": {
                "world_name": self.protocol.get('world_name'),
                "protocol_version": self.protocol.get('metadata', {}).get('compiled_at', 'unknown')
            }
        }
        return blueprint

    def save_blueprint(self, blueprint: Dict, output_dir: Path):
        """保存蓝图为 JSON 文件，并创建配套标记文件"""
        output_dir.mkdir(parents=True, exist_ok=True)
        shot_id = blueprint['SHOT_ID']
        
        # 保存主蓝图 JSON
        blueprint_path = output_dir / f"{shot_id}_shot_blueprint.json"
        with open(blueprint_path, 'w', encoding='utf-8') as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        print(f"[蓝图生成器] 蓝图已保存: {blueprint_path}")

        # 同时创建对话流标记文件（为后续 TTS 准备）
        if blueprint.get('DIALOGUE'):
            dialogue_path = output_dir / f"{shot_id}_dialogue_stream.md"
            with open(dialogue_path, 'w', encoding='utf-8') as f:
                f.write(f"# {shot_id} 对白流\n")
                f.write(f"**情绪**: {blueprint['DIALOGUE_EMOTION']}\n\n")
                f.write(f"> {blueprint['DIALOGUE']}\n")
            print(f"[蓝图生成器] 对白流文件已生成: {dialogue_path}")

        # 创建字幕骨架 SRT
        if blueprint.get('DIALOGUE'):
            subtitle_path = output_dir / f"{shot_id}_subtitle.srt"
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(f"1\n00:00:00,000 --> 00:00:{int(blueprint['DURATION_SEC']):02d},000\n")
                f.write(f"{blueprint['DIALOGUE']}\n")
            print(f"[蓝图生成器] 字幕模板已生成: {subtitle_path}")


# ---------- 交互式创建示例 ----------
def interactive_blueprint_creation(generator: BlueprintGenerator):
    """命令行交互式批量生成蓝图"""
    print("\n>>> 蓝图生成模式 <<<")
    episode = input("请输入集数名称 (如 Episode_01): ").strip()
    output_dir = Path(f"./{episode}")
    
    while True:
        print("\n--- 新镜头 ---")
        shot_id = input("镜头ID (例如 SC-001，直接回车结束): ").strip()
        if not shot_id:
            break
        scene = input("场景描述: ").strip()
        if not scene:
            print("场景描述不能为空，跳过此镜头。")
            continue
        dialogue = input("对白 (可选): ").strip()
        emotion = input("情绪 (neutral/happy/angry/sad/thoughtful): ").strip() or "neutral"
        camera = input("镜头运动 (static/slow push-in/pan/track): ").strip() or "static"
        dur_str = input("时长(秒) [默认4.0]: ").strip()
        try:
            duration = float(dur_str) if dur_str else 4.0
        except ValueError:
            duration = 4.0
        
        blueprint = generator.generate_shot_blueprint(
            scene_description=scene,
            shot_id=shot_id,
            dialogue=dialogue,
            emotion=emotion,
            camera_move=camera,
            duration=duration
        )
        generator.save_blueprint(blueprint, output_dir)


if __name__ == "__main__":
    # 默认协议路径（相对于项目根目录）
    default_protocol = "../0_CORE_PROTOCOL/example_world_protocol.json"
    if len(sys.argv) > 1:
        protocol_path = sys.argv[1]
    else:
        protocol_path = default_protocol
    
    try:
        generator = BlueprintGenerator(protocol_path)
        interactive_blueprint_creation(generator)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保协议文件存在，或通过命令行参数指定路径。")
        print("例如: python blueprint_generator.py ../0_CORE_PROTOCOL/example_world_protocol.json")