# sd_control_console.py
import json

def build_sd_prompt(shot_blueprint_path: str, protocol_path: str) -> tuple:
    """构造Stable Diffusion的标准化提示词与负向提示词"""
    with open(shot_blueprint_path, 'r') as f:
        blueprint = json.load(f)
    with open(protocol_path, 'r') as f:
        protocol = json.load(f)
    
    # 构造正向提示词
    positive_prompt = (
        f"masterpiece, best quality, {protocol['render_style_lock']['visual_style']}, "
        f"{protocol['render_style_lock']['color_gradient']}, "
        f"{blueprint['VISUAL_PROMPT']}, "
        f"<lora:{list(protocol['entity_definitions'].keys())[0]}_visual:0.8>, "  # 动态绑定实体LoRA
        "sharp focus, cinematic lighting"
    )
    
    # 构造负向提示词（系统约束）
    negative_prompt = (
        "(low quality, worst quality:1.4), (bad anatomy, deformed, extra limbs), "
        "blurry, text, watermark, signature, "
        f"{protocol['render_style_lock']['style_contamination_block']}"  # 风格污染防护
    )
    
    return positive_prompt, negative_prompt

# 使用示例
if __name__ == "__main__":
    pos, neg = build_sd_prompt(
        "../1_TERRAIN_BLUEPRINTS/Episode_01/SC-001_shot_blueprint.json",
        "../0_CORE_PROTOCOL/World_Terrain_Protocol.json"
    )
    print("=== 正向提示词 ===")
    print(pos)
    print("\n=== 负向提示词（系统约束）===")
    print(neg)
    print("\n[控制台] 请将以上提示词复制至Stable Diffusion WebUI。")