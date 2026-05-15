from auto_log_wrap import func_log

"""
慧凌世界地形系统 - 稳定性扫描器 v1.0
对照核心协议，对最终成品（或中间产物）进行多维度校验，
输出扫描日志，确保世界构建无偏离。
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import sys

class WorldStabilityScanner:
    """世界稳定性校验器"""

    def __init__(self, protocol_path: str):
        protocol_file = Path(protocol_path)
        if not protocol_file.exists():
            raise FileNotFoundError(f"协议文件不存在: {protocol_path}")
        with open(protocol_file, 'r', encoding='utf-8') as f:
            self.protocol = json.load(f)
        self.logs = []
        self.warnings = 0
        self.errors = 0
        print(f"[扫描器] 已加载协议: {self.protocol.get('world_name', '未命名世界')}")

    def log_info(self, msg: str):
        self.logs.append(f"[INFO] {msg}")

    def log_warning(self, msg: str):
        self.logs.append(f"[WARNING] {msg}")
        self.warnings += 1

    def log_error(self, msg: str):
        self.logs.append(f"[ERROR] {msg}")
        self.errors += 1

    # ----------------- 实体视觉一致性扫描 -----------------
    def scan_entity_visual_consistency(self, blueprint_path: str, generated_image_path: str):
        """
        检查生成图片是否与实体定义中的视觉哈希匹配。
        实际实现需调用视觉相似度模型（如 CLIP），此处为校验框架。
        """
        blueprint = self._load_json(blueprint_path)
        if not blueprint:
            self.log_error(f"蓝图无法加载: {blueprint_path}")
            return

        entity_defs = self.protocol.get('entity_definitions', {})
        if not entity_defs:
            self.log_info("协议中未定义实体，跳过视觉一致性扫描。")
            return

        shot_id = blueprint.get('SHOT_ID', Path(blueprint_path).stem)
        image_path = Path(generated_image_path)
        if not image_path.exists():
            self.log_warning(f"{shot_id}: 生成图片不存在 {generated_image_path}，无法扫描视觉一致性。")
            return

        # 模拟：读取实体定义中的视觉哈希，与图片进行对比
        # 在实际部署中，此处调用视觉模型：
        # for entity_id, entity_data in entity_defs.items():
        #     visual_hash = entity_data.get('visual_hash', '')
        #     similarity = clip_model.compare(image_path, visual_hash)
        #     if similarity < 0.8:
        #         self.log_error(f"{shot_id}: 实体 '{entity_id}' 视觉不一致，相似度 {similarity}")
        #     else:
        #         self.log_info(f"{shot_id}: 实体 '{entity_id}' 视觉一致 ({similarity})")
        self.log_info(f"{shot_id}: 视觉一致性扫描已执行（需接入视觉模型以完整校验）。")

    # ----------------- 声纹一致性扫描 -----------------
    def scan_voice_consistency(self, audio_path: str, expected_speaker: str):
        """
        检查音频文件中的声纹是否匹配协议定义。
        实际需声纹比对模型（如 Speaker Verification）。
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            self.log_warning(f"音频文件不存在: {audio_path}，无法进行声纹校验。")
            return

        voice_config = self.protocol.get('entity_definitions', {}).get(expected_speaker, {})
        expected_voice_hash = voice_config.get('voice_hash', '')
        if not expected_voice_hash:
            self.log_info(f"角色 '{expected_speaker}' 未定义声纹，跳过。")
            return

        # 模拟比对
        self.log_info(f"音频 '{audio_file.name}' 声纹与角色 '{expected_speaker}' 比对完成（需接入声纹模型）。")

    # ----------------- 字幕同步扫描 -----------------
    def scan_subtitle_sync(self, subtitle_path: str, expected_duration: float):
        """
        检查字幕文件时间轴是否与蓝图时长匹配。
        """
        sub_file = Path(subtitle_path)
        if not sub_file.exists():
            self.log_warning(f"字幕文件不存在: {subtitle_path}")
            return

        shot_id = sub_file.stem.replace("_subtitle", "")
        last_end = 0.0
        try:
            with open(sub_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                if '-->' in line:
                    parts = line.strip().split('-->')
                    if len(parts) == 2:
                        end_time_str = parts[1].strip()
                        # 格式 HH:MM:SS,mmm
                        h, m, s = end_time_str.split(':')
                        s, ms = s.split(',')
                        end_sec = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
                        last_end = max(last_end, end_sec)
            # 字幕结束时间不应超过镜头时长+1秒容差
            if last_end > expected_duration + 1.0:
                self.log_warning(f"{shot_id}: 字幕结束时间 ({last_end}s) 超出镜头时长 ({expected_duration}s)。")
            else:
                self.log_info(f"{shot_id}: 字幕同步正常。")
        except Exception as e:
            self.log_error(f"{shot_id}: 字幕解析异常: {e}")

    # ----------------- 蓝图-视频时长一致性扫描 -----------------
    def scan_duration_consistency(self, episode_dir: str):
        """
        对比所有蓝图的时长合计与最终视频实际时长（需最终视频文件）。
        """
        ep_path = Path(episode_dir)
        blueprint_files = sorted(ep_path.glob("*_shot_blueprint.json"))
        total_blueprint_duration = 0.0
        for bf in blueprint_files:
            bp = self._load_json(bf)
            if bp:
                total_blueprint_duration += bp.get('DURATION_SEC', 0)
        
        # 寻找最终视频
        final_videos = list(ep_path.glob("**/*FINAL.mp4"))
        if not final_videos:
            self.log_info("未找到最终视频文件，跳过时长对比。")
            return
        video_path = final_videos[0]
        # 使用 ffprobe 获取时长
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True, check=True
            )
            video_duration = float(result.stdout.strip())
            diff = abs(video_duration - total_blueprint_duration)
            if diff > 2.0:  # 允许2秒误差
                self.log_warning(f"最终视频时长 ({video_duration}s) 与蓝图合计 ({total_blueprint_duration}s) 偏差 {diff:.1f}s。")
            else:
                self.log_info(f"时长一致: 视频 {video_duration}s, 蓝图合计 {total_blueprint_duration}s。")
        except Exception as e:
            self.log_warning(f"无法获取视频时长: {e}")

    # ----------------- 协议字段完整性扫描 -----------------
    def scan_protocol_completeness(self, blueprint_path: str):
        """
        检查蓝图是否包含协议要求的必填字段。
        """
        blueprint = self._load_json(blueprint_path)
        if not blueprint:
            return
        required_fields = ['SHOT_ID', 'VISUAL_PROMPT_BASE', 'DURATION_SEC']
        for field in required_fields:
            if field not in blueprint:
                self.log_error(f"{Path(blueprint_path).name}: 缺少必填字段 '{field}'")

    # ----------------- 全项扫描入口 -----------------
    def full_scan(self, episode_dir: str):
        """
        对剧集目录执行所有扫描。
        """
        print("[扫描器] 开始全项稳定性扫描...\n")
        ep_path = Path(episode_dir)
        if not ep_path.exists():
            self.log_error(f"剧集目录不存在: {episode_dir}")
            return

        blueprint_files = sorted(ep_path.glob("*_shot_blueprint.json"))
        for bf in blueprint_files:
            shot_id = bf.stem.replace("_shot_blueprint", "")
            self.log_info(f"--- 扫描 {shot_id} ---")

            # 协议字段完整性
            self.scan_protocol_completeness(str(bf))

            # 视觉一致性（假设图片与蓝图同名但扩展名为.png）
            image_path = ep_path / f"{shot_id}.png"
            if image_path.exists():
                self.scan_entity_visual_consistency(str(bf), str(image_path))
            else:
                self.log_warning(f"{shot_id}: 图片素材缺失。")

            # 声纹一致性（假设音频为 shot_id_dialogue.wav）
            audio_path = ep_path / f"{shot_id}_dialogue.wav"
            if audio_path.exists():
                # 从蓝图中获取说话人（如果定义了 speaker 字段）
                bp = self._load_json(bf)
                speaker = bp.get('speaker', '主角') if bp else '主角'
                self.scan_voice_consistency(str(audio_path), speaker)

            # 字幕同步
            subtitle_path = ep_path / f"{shot_id}_subtitle.srt"
            bp = self._load_json(bf)
            expected_dur = bp.get('DURATION_SEC', 4.0) if bp else 4.0
            if subtitle_path.exists():
                self.scan_subtitle_sync(str(subtitle_path), expected_dur)

        # 时长对比（需要最终视频）
        self.scan_duration_consistency(episode_dir)

        # 打印汇总
        print("\n========== 扫描报告 ==========")
        for log in self.logs:
            print(log)
        print(f"\n总计: 错误 {self.errors}, 警告 {self.warnings}")
        if self.errors == 0 and self.warnings == 0:
            print("[扫描器] ✅ 世界稳定，所有系统符合核心协议。")
        else:
            print("[扫描器] ⚠️ 发现偏离，请核查上述问题。")

    def _load_json(self, path) -> Optional[Dict]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None


if __name__ == "__main__":
    default_ep = "../1_TERRAIN_BLUEPRINTS/Episode_01"
    episode_dir = input(f"待扫描剧集目录 (回车默认: {default_ep}): ").strip()
    if not episode_dir:
        episode_dir = default_ep

    default_protocol = "../0_CORE_PROTOCOL/example_world_protocol.json"
    protocol_path = input(f"协议文件路径 (回车默认: {default_protocol}): ").strip()
    if not protocol_path:
        protocol_path = default_protocol

    try:
        scanner = WorldStabilityScanner(protocol_path)
        scanner.full_scan(episode_dir)
    except Exception as e:
        print(f"[错误] {e}")