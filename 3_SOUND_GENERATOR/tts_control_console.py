from auto_log_wrap import func_log

"""
慧凌世界地形系统 - TTS 语音合成控制台 v1.0
根据蓝图中的对白流和情绪标签，调用语音合成引擎，锁定角色声纹，输出音频片段。
"""

import json
from pathlib import Path
from typing import Dict, Optional
import sys

class TTSController:
    """语音合成控制器，管理声纹模型与合成参数"""

    def __init__(self, protocol_path: str, voice_models_dir: str = "./voice_cloning"):
        """
        初始化并加载协议与声纹库索引。
        voice_models_dir: 存放声纹模型文件的目录（如 .mp3 参考音频）
        """
        protocol_file = Path(protocol_path)
        if not protocol_file.exists():
            raise FileNotFoundError(f"协议文件不存在: {protocol_path}")
        with open(protocol_file, 'r', encoding='utf-8') as f:
            self.protocol = json.load(f)
        
        self.voice_models_dir = Path(voice_models_dir)
        self.entity_defs = self.protocol.get('entity_definitions', {})
        
        # 构建实体-声纹映射
        self.voice_map = {}
        for entity_id, entity_data in self.entity_defs.items():
            voice_ref = entity_data.get('voice_reference', f"PROJECT_{entity_id}.mp3")
            voice_path = self.voice_models_dir / voice_ref
            self.voice_map[entity_id] = {
                'reference_file': str(voice_path),
                'voice_hash': entity_data.get('voice_hash', 'default'),
                'speed': entity_data.get('speech_speed', 1.0),
                'pitch': entity_data.get('speech_pitch', 1.0)
            }
        print(f"[TTS控制台] 已加载 {len(self.voice_map)} 个角色声纹: {list(self.voice_map.keys())}")

    def generate_dialogue_audio(self, blueprint_path: str, output_dir: Optional[Path] = None) -> Dict:
        """
        从蓝图提取对白并合成音频。
        返回合成任务描述（实际合成需接入 TTS API，此处输出可执行的配置）。
        """
        bp_file = Path(blueprint_path)
        if not bp_file.exists():
            raise FileNotFoundError(f"蓝图文件不存在: {blueprint_path}")
        with open(bp_file, 'r', encoding='utf-8') as f:
            blueprint = json.load(f)

        shot_id = blueprint['SHOT_ID']
        dialogue = blueprint.get('DIALOGUE', '')
        emotion = blueprint.get('DIALOGUE_EMOTION', 'neutral')
        duration = blueprint.get('DURATION_SEC', 4.0)

        if not dialogue:
            print(f"[TTS控制台] {shot_id} 无对白，跳过。")
            return {"status": "no_dialogue"}

        # 确定说话人（蓝图里目前默认主角，后续可扩展 speaker 字段）
        speaker = blueprint.get('speaker', '主角')
        voice_config = self.voice_map.get(speaker, self.voice_map.get('主角', {}))

        # 构建合成任务
        synthesis_task = {
            "shot_id": shot_id,
            "text": dialogue,
            "emotion": emotion,
            "voice_reference": voice_config.get('reference_file'),
            "voice_hash": voice_config.get('voice_hash'),
            "speed": voice_config.get('speed', 1.0),
            "pitch": voice_config.get('pitch', 1.0),
            "output_filename": f"{shot_id}_dialogue.wav",
            "target_duration": duration
        }

        if output_dir is None:
            output_dir = Path(blueprint_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        task_file = output_dir / f"{shot_id}_tts_task.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(synthesis_task, f, ensure_ascii=False, indent=2)
        print(f"[TTS控制台] 合成任务已生成: {task_file}")

        # 在实际部署中，这里会调用类似以下伪代码：
        # audio_bytes = tts_engine.synthesize(
        #     text=dialogue,
        #     voice_reference=voice_config['reference_file'],
        #     emotion=emotion,
        #     speed=voice_config['speed']
        # )
        # 然后保存为 output_dir / f"{shot_id}_dialogue.wav"

        return synthesis_task

    def batch_generate_from_episode(self, episode_dir: str):
        """对整集的所有镜头蓝图批量生成TTS任务"""
        ep_path = Path(episode_dir)
        if not ep_path.exists():
            raise FileNotFoundError(f"剧集目录不存在: {episode_dir}")
        blueprint_files = sorted(ep_path.glob("*_shot_blueprint.json"))
        if not blueprint_files:
            print("[TTS控制台] 该目录下未找到蓝图文件。")
            return
        
        for bf in blueprint_files:
            try:
                self.generate_dialogue_audio(str(bf), output_dir=ep_path)
            except Exception as e:
                print(f"[错误] 处理 {bf.name} 失败: {e}")


# ---------- 交互入口 ----------
def interactive_tts():
    default_protocol = "../0_CORE_PROTOCOL/example_world_protocol.json"
    protocol_path = input(f"协议文件路径 (回车默认: {default_protocol}): ").strip()
    if not protocol_path:
        protocol_path = default_protocol

    try:
        controller = TTSController(protocol_path)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return

    while True:
        mode = input("\n模式选择：1-单个蓝图 2-整集批量 (输入 'q' 退出): ").strip()
        if mode.lower() == 'q':
            break
        if mode == '1':
            bp = input("蓝图JSON路径: ").strip()
            if Path(bp).exists():
                controller.generate_dialogue_audio(bp)
            else:
                print("文件不存在。")
        elif mode == '2':
            ep = input("剧集目录路径: ").strip()
            if Path(ep).exists():
                controller.batch_generate_from_episode(ep)
            else:
                print("目录不存在。")
        else:
            print("无效输入。")

if __name__ == "__main__":
    interactive_tts()