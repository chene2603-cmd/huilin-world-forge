from auto_log_wrap import func_log

#!/usr/bin/env python3
"""
漫剧生成系统 - 基于慧凌世界框架
支持：分镜生成、角色一致性图像生成、视频合成
"""

import os
import json
import time
import argparse
import subprocess
import requests
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# ========== 配置部分 ==========
# 请根据你的环境修改
CONFIG = {
    "llm_api": {
        "provider": "openai",  # 或 "deepseek", "qwen"
        "api_key": os.getenv("LLM_API_KEY", "your-api-key"),
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini"
    },
    "comfyui": {
        "server_address": "127.0.0.1:8188",
        "client_id": "comic_studio"
    },
    "output_dir": "./output_comic",
    "ffmpeg_path": "ffmpeg",  # 确保 ffmpeg 在 PATH 中
    "temp_dir": "./temp_comic"
}

# ========== 数据模型 ==========
@dataclass
class Shot:
    """单个分镜"""
    shot_id: int
    scene_desc: str          # 场景描述
    characters: List[str]    # 角色列表
    dialogue: str            # 台词
    action: str              # 动作描述
    duration: float          # 预计时长(秒)
    camera_angle: str        # 镜头角度
    mood: str                # 情绪

@dataclass
class Storyboard:
    """分镜脚本"""
    title: str
    style: str
    shots: List[Shot]

# ========== 1. 分镜蓝图生成器 ==========
class ScriptToStoryboard:
    """将自然语言剧本转换为结构化分镜"""
    
    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        self.system_prompt = """你是一位专业漫剧分镜师。根据用户输入的剧本，生成结构化分镜脚本。
输出格式必须为 JSON，结构如下：
{
  "title": "故事标题",
  "style": "画风描述（如：国风、赛博朋克、二次元）",
  "shots": [
    {
      "shot_id": 1,
      "scene_desc": "场景描述，包含环境、光线等",
      "characters": ["角色名1", "角色名2"],
      "dialogue": "该镜头中的对白",
      "action": "角色动作描述",
      "duration": 5.0,
      "camera_angle": "特写/中景/远景等",
      "mood": "氛围关键词"
    }
  ]
}
要求：
- 每个镜头时长建议 3-8 秒
- 分镜数量根据剧本长度自动决定（通常 10-30 个）
- 角色名称保持一致
- 输出只包含 JSON，不要有其他解释。"""

    def generate(self, script_text: str) -> Storyboard:
        """调用 LLM 生成分镜"""
        response = self._call_llm(script_text)
        data = json.loads(response)
        shots = [Shot(**s) for s in data["shots"]]
        return Storyboard(title=data["title"], style=data["style"], shots=shots)
    
    def _call_llm(self, user_prompt: str) -> str:
        # 根据配置调用不同 API
        if self.llm_config["provider"] == "openai":
            import openai
            openai.api_key = self.llm_config["api_key"]
            openai.base_url = self.llm_config["base_url"]
            resp = openai.chat.completions.create(
                model=self.llm_config["model"],
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            return resp.choices[0].message.content
        else:
            # 可以扩展 DeepSeek 等
            raise NotImplementedError("其他 provider 请自行实现")

# ========== 2. 角色一致性图像生成（ComfyUI 工作流） ==========
class ComfyUIClient:
    """通过 API 调用 ComfyUI 工作流"""
    
    def __init__(self, server_address: str, client_id: str):
        self.server = server_address
        self.client_id = client_id
        self.base_url = f"http://{server_address}"
    
    def queue_prompt(self, workflow_json: Dict) -> str:
        """提交工作流，返回 prompt_id"""
        data = {"prompt": workflow_json, "client_id": self.client_id}
        resp = requests.post(f"{self.base_url}/prompt", json=data)
        return resp.json()["prompt_id"]
    
    def wait_for_image(self, prompt_id: str, timeout=120) -> Optional[str]:
        """轮询结果，返回生成的图片路径（本地临时文件）"""
        start = time.time()
        while time.time() - start < timeout:
            resp = requests.get(f"{self.base_url}/history/{prompt_id}")
            if resp.status_code == 200:
                history = resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]
                    # 假设第一个输出是图片
                    for node_id, node_out in outputs.items():
                        if "images" in node_out:
                            img = node_out["images"][0]
                            filename = img["filename"]
                            # 下载图片
                            img_data = requests.get(f"{self.base_url}/view?filename={filename}").content
                            out_path = Path(CONFIG["temp_dir"]) / filename
                            out_path.write_bytes(img_data)
                            return str(out_path)
            time.sleep(2)
        return None

    @staticmethod
    def load_workflow(json_path: str) -> Dict:
        with open(json_path, "r") as f:
            return json.load(f)

# 角色一致性工作流 JSON（见下一章节）
# 这里我们提供一个函数，动态生成工作流（简化版，实际建议用预置 JSON）
def build_character_consistent_workflow(character_ref_image: str, prompt: str, seed: int = 42) -> Dict:
    """
    生成一个简易的角色一致性工作流（使用 IPAdapter 或 Reference Only）
    注意：这个 JSON 是示意结构，你需要根据你的 ComfyUI 节点实际修改。
    """
    workflow = {
        "3": {"class_type": "LoadImage", "inputs": {"image": character_ref_image}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["5", 1]}},
        "5": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "6": {"class_type": "IPAdapter", "inputs": {"model": ["5", 0], "image": ["3", 0], "weight": 0.8}},
        "7": {"class_type": "KSampler", "inputs": {"seed": seed, "model": ["6", 0], "positive": ["4", 0], "negative": ["8", 0], "latent_image": ["9", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, bad", "clip": ["5", 1]}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 512, "batch_size": 1}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["5", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"filename_prefix": "comic_shot", "images": ["10", 0]}}
    }
    return workflow

# ========== 3. 视频合成模块 ==========
class VideoCompositor:
    """将图片序列+音频合成为漫剧视频（含字幕）"""
    
    def __init__(self, ffmpeg_path: str, temp_dir: Path):
        self.ffmpeg = ffmpeg_path
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def create_video_from_shots(self, shots: List[Shot], image_paths: List[str], audio_paths: List[str], output_video: str):
        """
        shots: 分镜列表（含时长、台词）
        image_paths: 每个镜头对应的图片路径
        audio_paths: 每个镜头的配音路径（可选，没有则生成 TTS）
        """
        # 生成每个镜头的独立视频片段
        segment_files = []
        for idx, (shot, img_path) in enumerate(zip(shots, image_paths)):
            duration = shot.duration
            # 如果有音频，则使用音频长度决定视频长度
            audio_path = audio_paths[idx] if idx < len(audio_paths) else None
            if audio_path:
                # 获取音频时长
                cmd = [self.ffmpeg, "-i", audio_path, "-f", "null", "-"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                # 解析时长（简化）
                duration = self._get_audio_duration(audio_path)
            
            out_seg = self.temp_dir / f"seg_{idx:03d}.mp4"
            # 使用 ffmpeg 将单张图片+音频（可选）合成为视频
            cmd = [self.ffmpeg, "-loop", "1", "-i", img_path, "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p"]
            if audio_path:
                cmd += ["-i", audio_path, "-c:a", "aac", "-shortest"]
            cmd += ["-y", str(out_seg)]
            subprocess.run(cmd, check=True)
            segment_files.append(out_seg)
        
        # 合并所有片段
        concat_list = self.temp_dir / "concat.txt"
        with open(concat_list, "w") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")
        
        subprocess.run([
            self.ffmpeg, "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", "-y", output_video
        ], check=True)
        print(f"视频已生成：{output_video}")
    
    def _get_audio_duration(self, audio_path: str) -> float:
        cmd = [self.ffmpeg, "-i", audio_path, "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.PIPE)
        # 解析 "Duration: 00:00:05.12"
        import re
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
        if match:
            h, m, s = match.groups()
            return int(h)*3600 + int(m)*60 + float(s)
        return 5.0

# ========== 4. 端到端命令行工具 ==========
class ComicStudioCLI:
    def __init__(self):
        self.storyboard_gen = ScriptToStoryboard(CONFIG["llm_api"])
        self.comfy_client = ComfyUIClient(CONFIG["comfyui"]["server_address"], CONFIG["comfyui"]["client_id"])
        self.compositor = VideoCompositor(CONFIG["ffmpeg_path"], Path(CONFIG["temp_dir"]))
        # 确保输出目录存在
        Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)
        Path(CONFIG["temp_dir"]).mkdir(parents=True, exist_ok=True)
    
    def run(self, script_file: str, character_ref: str, workflow_json_path: str):
        # 1. 读取剧本
        with open(script_file, "r", encoding="utf-8") as f:
            script = f.read()
        
        # 2. 生成分镜
        print("生成分镜...")
        storyboard = self.storyboard_gen.generate(script)
        print(f"分镜已生成，共 {len(storyboard.shots)} 个镜头")
        
        # 3. 为每个镜头生成图片（角色一致性）
        print("生成图像（使用 ComfyUI）...")
        workflow_template = ComfyUIClient.load_workflow(workflow_json_path)
        image_paths = []
        for shot in storyboard.shots:
            prompt = f"{storyboard.style}, {shot.scene_desc}, {shot.action}, character: {','.join(shot.characters)}, mood: {shot.mood}, camera: {shot.camera_angle}"
            # 动态设置工作流中的 prompt 和参考图
            workflow = workflow_template.copy()
            # 假设工作流中有节点"4"是 CLIP Text Encode，将其 text 替换为 prompt
            # 这里简化：实际需要根据你的工作流结构调整
            workflow["4"]["inputs"]["text"] = prompt
            # 如果需要替换参考图节点（例如 LoadImage 节点 ID 为 3）
            if "3" in workflow:
                workflow["3"]["inputs"]["image"] = character_ref
            
            prompt_id = self.comfy_client.queue_prompt(workflow)
            img_path = self.comfy_client.wait_for_image(prompt_id)
            if img_path:
                image_paths.append(img_path)
            else:
                print(f"镜头 {shot.shot_id} 图像生成超时")
                image_paths.append("")  # 占位
        
        # 4. 生成配音（可选，这里使用简单的 TTS，需要安装 edge-tts）
        print("生成配音...")
        audio_paths = []
        for shot in storyboard.shots:
            if shot.dialogue.strip():
                audio_file = Path(CONFIG["temp_dir"]) / f"audio_{shot.shot_id}.mp3"
                # 使用 edge-tts 生成
                subprocess.run([
                    "edge-tts", "--text", shot.dialogue, "--write-media", str(audio_file)
                ], check=False)
                if audio_file.exists():
                    audio_paths.append(str(audio_file))
                else:
                    audio_paths.append(None)
            else:
                audio_paths.append(None)
        
        # 5. 合成视频
        output_video = Path(CONFIG["output_dir"]) / f"{storyboard.title}.mp4"
        self.compositor.create_video_from_shots(storyboard.shots, image_paths, audio_paths, str(output_video))
        print(f"漫剧制作完成！视频位置：{output_video}")

def main():
    parser = argparse.ArgumentParser(description="AI 漫剧生成系统")
    parser.add_argument("--script", required=True, help="剧本文本文件路径")
    parser.add_argument("--character_ref", required=True, help="角色参考图路径")
    parser.add_argument("--workflow", required=True, help="ComfyUI 工作流 JSON 文件路径")
    args = parser.parse_args()
    
    studio = ComicStudioCLI()
    studio.run(args.script, args.character_ref, args.workflow)

if __name__ == "__main__":
    main()