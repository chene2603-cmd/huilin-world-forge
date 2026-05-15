from auto_log_wrap import func_log

"""
慧凌世界地形系统 - 渲染引擎 v1.0 (Stable Diffusion 控制台)
从镜头蓝图和核心协议构建标准化提示词，锁定视觉风格、绑定实体LoRA，输出可直接用于SD WebUI/API。
"""

import json
from pathlib import Path
from typing import Tuple, Dict
import sys

class SDPromptBuilder:
    """基于协议和蓝图构造SD提示词"""

    def __init__(self, protocol_path: str):
        protocol_file = Path(protocol_path)
        if not protocol_file.exists():
            raise FileNotFoundError(f"协议文件不存在: {protocol_path}")
        with open(protocol_file, 'r', encoding='utf-8') as f:
            self.protocol = json.load(f)
        self.style_lock = self.protocol.get('render_style_lock', {})
        self.entity_defs = self.protocol.get('entity_definitions', {})
        print(f"[SD控制台] 已加载协议，视觉风格锁定: {self.style_lock.get('visual_style', '未定义')}")

    def build_prompt(self, blueprint_path: str) -> Tuple[str, str, Dict]:
        """
        读取蓝图，构造正向提示词、负向提示词和渲染元数据。
        返回: (positive_prompt, negative_prompt, metadata)
        """
        bp_file = Path(blueprint_path)
        if not bp_file.exists():
            raise FileNotFoundError(f"蓝图文件不存在: {blueprint_path}")
        with open(bp_file, 'r', encoding='utf-8') as f:
            blueprint = json.load(f)

        # === 组装正向提示词 ===
        prompt_parts = [
            "masterpiece, best quality, highly detailed",
            self.style_lock.get('visual_style', 'concept art'),
            self.style_lock.get('color_gradient', 'natural lighting'),
            blueprint.get('VISUAL_PROMPT_BASE', ''),
        ]

        # 绑定实体 LoRA（从协议中动态获取）
        for entity_id, entity_data in self.entity_defs.items():
            lora_name = entity_data.get('lora_model', f"{entity_id}_visual")
            lora_weight = entity_data.get('lora_weight', 0.8)
            prompt_parts.append(f"<lora:{lora_name}:{lora_weight}>")

        prompt_parts.append("sharp focus, cinematic composition")

        positive = ", ".join(part for part in prompt_parts if part)

        # === 组装负向提示词 ===
        negative_parts = [
            "(low quality, worst quality:1.4)",
            "(bad anatomy, deformed, extra limbs, fused fingers)",
            "blurry, text, watermark, signature, jpeg artifacts",
            "ugly, tiling, out of frame, disfigured",
            self.style_lock.get('style_contamination_block', '')
        ]
        negative = ", ".join(part for part in negative_parts if part)

        # === 元数据记录（用于追溯和扫描器校验） ===
        metadata = {
            "shot_id": blueprint.get('SHOT_ID'),
            "protocol_version": self.protocol.get('metadata', {}).get('compiled_at', 'unknown'),
            "active_loras": list(self.entity_defs.keys()),
            "positive_length": len(positive),
            "negative_length": len(negative),
        }
        return positive, negative, metadata

    def export_prompt_file(self, blueprint_path: str, output_dir: Path = None):
        """生成可直接复制到SD WebUI的文本文件，并返回路径"""
        positive, negative, meta = self.build_prompt(blueprint_path)
        shot_id = meta['shot_id']
        
        if output_dir is None:
            output_dir = Path(blueprint_path).parent
        
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = output_dir / f"{shot_id}_sd_prompt.txt"
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"# {shot_id} Stable Diffusion 提示词\n")
            f.write(f"# 生成时间: {Path(blueprint_path).stat().st_mtime}\n\n")
            f.write("=== 正向提示词 ===\n")
            f.write(positive + "\n\n")
            f.write("=== 负向提示词 ===\n")
            f.write(negative + "\n\n")
            f.write("# 请将以上两段分别复制到SD WebUI的对应输入框。\n")
        
        print(f"[SD控制台] 提示词文件已导出: {prompt_file}")
        return prompt_file


# ---------- 交互式 / 批量入口 ----------
def interactive_console():
    """命令行交互式选择蓝图并导出提示词"""
    default_protocol = "../0_CORE_PROTOCOL/example_world_protocol.json"
    protocol_path = input(f"协议文件路径 (回车默认: {default_protocol}): ").strip()
    if not protocol_path:
        protocol_path = default_protocol
    
    try:
        builder = SDPromptBuilder(protocol_path)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return

    while True:
        bp_path = input("\n蓝图JSON路径 (输入 'q' 退出): ").strip()
        if bp_path.lower() == 'q':
            break
        if not Path(bp_path).exists():
            print("文件不存在，请重新输入。")
            continue
        
        try:
            pos, neg, meta = builder.build_prompt(bp_path)
            print(f"\n--- {meta['shot_id']} 正向提示词 ---")
            print(pos)
            print(f"\n--- 负向提示词 ---")
            print(neg)
            
            export_choice = input("\n导出为txt文件? (y/n): ").strip().lower()
            if export_choice == 'y':
                builder.export_prompt_file(bp_path)
        except Exception as e:
            print(f"生成失败: {e}")


if __name__ == "__main__":
    interactive_console()