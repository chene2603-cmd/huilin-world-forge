from auto_log_wrap import func_log

"""
慧凌世界地形系统 - 世界构建器 v1.0
自动装配：从蓝图目录收集镜头素材，合成最终影片。
依赖 FFmpeg（需已安装并在 PATH 中）。
"""

import json
from pathlib import Path
from typing import List, Optional
import subprocess
import sys

class AssemblyWorkflow:
    """将分镜素材装配为完整视频"""

    def __init__(self, episode_dir: str, output_dir: str = None):
        self.episode_dir = Path(episode_dir)
        if not self.episode_dir.exists():
            raise FileNotFoundError(f"剧集目录不存在: {episode_dir}")
        
        self.output_dir = Path(output_dir) if output_dir else self.episode_dir / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 扫描蓝图并收集素材路径
        self.shots = []
        blueprint_files = sorted(self.episode_dir.glob("*_shot_blueprint.json"))
        for bf in blueprint_files:
            shot_id = bf.stem.replace("_shot_blueprint", "")
            data = self._load_blueprint(bf)
            if data:
                # 推定素材路径（按命名约定）
                image = self.episode_dir / f"{shot_id}.png"
                audio = self.episode_dir / f"{shot_id}_dialogue.wav"
                subtitle = self.episode_dir / f"{shot_id}_subtitle.srt"
                self.shots.append({
                    "shot_id": shot_id,
                    "duration": data.get("DURATION_SEC", 4.0),
                    "image": str(image) if image.exists() else None,
                    "audio": str(audio) if audio.exists() else None,
                    "subtitle": str(subtitle) if subtitle.exists() else None
                })
        print(f"[装配车间] 发现 {len(self.shots)} 个镜头。")

    def _load_blueprint(self, path: Path) -> Optional[dict]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def _run_ffmpeg(self, cmd: List[str], description: str = ""):
        print(f"[FFmpeg] {description}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("  完成。")
        except subprocess.CalledProcessError as e:
            print(f"  错误: {e.stderr}")

    def assemble(self, episode_name: str = "Episode_01") -> Optional[Path]:
        """组装最终视频"""
        if not self.shots:
            print("[装配车间] 没有镜头，装配终止。")
            return None

        # 1. 为每个镜头生成带时长的视频片段（用图片 + 音频）
        clips = []
        for i, shot in enumerate(self.shots):
            shot_id = shot["shot_id"]
            clip_file = self.output_dir / f"{shot_id}_clip.mp4"

            # 如果没有图片，使用黑屏占位
            image_input = shot["image"] or "color=c=black:s=1920x1080"
            duration = shot["duration"]

            # 基础命令：图片转视频片段
            cmd_img = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_input if shot["image"] else "none",
                "-c:v", "libx264",
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-r", "24",
            ]
            if not shot["image"]:
                # 黑屏生成
                cmd_img = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s=1920x1080:d={duration}:r=24",
                    "-c:v", "libx264",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                ]
            cmd_img.append(str(clip_file))
            self._run_ffmpeg(cmd_img, f"{shot_id} 视频片段生成")

            # 如果有音频，混入片段
            if shot["audio"]:
                temp_clip = self.output_dir / f"{shot_id}_temp.mp4"
                clip_file.rename(temp_clip)
                cmd_audio = [
                    "ffmpeg", "-y",
                    "-i", str(temp_clip),
                    "-i", shot["audio"],
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    str(clip_file)
                ]
                self._run_ffmpeg(cmd_audio, f"{shot_id} 混音")
                temp_clip.unlink(missing_ok=True)

            # 如果有字幕，烧录进片段
            if shot["subtitle"]:
                temp_clip = self.output_dir / f"{shot_id}_temp2.mp4"
                clip_file.rename(temp_clip)
                cmd_sub = [
                    "ffmpeg", "-y",
                    "-i", str(temp_clip),
                    "-vf", f"subtitles={shot['subtitle']}:force_style='Fontsize=24,PrimaryColour=&H00FFFFFF,Outline=1'",
                    "-c:a", "copy",
                    str(clip_file)
                ]
                self._run_ffmpeg(cmd_sub, f"{shot_id} 烧录字幕")
                temp_clip.unlink(missing_ok=True)

            clips.append(clip_file)

        # 2. 合并所有片段
        concat_list = self.output_dir / "concat_list.txt"
        with open(concat_list, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip.resolve()}'\n")

        final_video = self.output_dir / f"{episode_name}_FINAL.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(final_video)
        ]
        self._run_ffmpeg(cmd_concat, "合并最终视频")
        concat_list.unlink(missing_ok=True)
        print(f"[装配车间] ✅ 最终视频输出: {final_video}")
        return final_video


if __name__ == "__main__":
    # 默认读取第一层蓝图的剧集目录
    default_ep = "../1_TERRAIN_BLUEPRINTS/Episode_01"
    episode_dir = input(f"剧集目录 (回车默认: {default_ep}): ").strip()
    if not episode_dir:
        episode_dir = default_ep

    try:
        builder = AssemblyWorkflow(episode_dir)
        builder.assemble()
    except Exception as e:
        print(f"[错误] {e}")