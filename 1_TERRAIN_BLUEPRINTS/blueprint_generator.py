# blueprint_generator.py
import json
from pathlib import Path

class BlueprintGenerator:
    def __init__(self, protocol_path: str):
        with open(protocol_path, 'r', encoding='utf-8') as f:
            self.protocol = json.load(f)
        print(f"[蓝图生成器] 已载入协议: {self.protocol['metadata']['project_name']}")
    
    def generate_shot_blueprint(self, scene_desc: str, shot_id: str) -> dict:
        """生成分镜施工图 (SHOT_BLUEPRINT)"""
        # 此处逻辑：调用LLM，结合protocol和scene_desc，生成结构化指令
        # 示例返回：
        blueprint = {
            "SHOT_ID": shot_id,
            "VISUAL_PROMPT": f"({self.protocol['render_style_lock']['visual_style']}), {scene_desc}, featuring {self.protocol['entity_definitions']['主角']['visual_hash']}, ...",
            "DIALOGUE": "主角(EMOTION:坚定): 我们必须前进。",
            "CAMERA_MOVE": "slow push-in, DURATION:3s"
        }
        return blueprint
    
    def save_blueprint(self, blueprint: dict, output_dir: Path):
        # 保存为JSON，供下游工具解析
        output_path = output_dir / f"{blueprint['SHOT_ID']}_shot_blueprint.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        print(f"[系统] 蓝图已保存至: {output_path}")

# 使用示例
if __name__ == "__main__":
    generator = BlueprintGenerator("../0_CORE_PROTOCOL/World_Terrain_Protocol.json")
    scene = "主角站在城市废墟上，眺望远方。"
    bp = generator.generate_shot_blueprint(scene, "SC-001")
    generator.save_blueprint(bp, Path("./Episode_01/"))