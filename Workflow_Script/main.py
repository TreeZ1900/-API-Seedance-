#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seedance 2.0 视频制作流水线
完整工作流: 剧本 → 人设图 → 分镜图 → 视频
"""

import os, json, time, re, shutil
import requests
from pathlib import Path
from datetime import datetime

# 官方 SDK（需先安装: pip install 'volcengine-python-sdk[ark]'）
try:
    from volcenginesdkarkruntime import Ark
    _SDK = True
except ImportError:
    _SDK = False

# TOS 对象存储 SDK（需先安装: pip install tos）
try:
    import tos as _tos_lib
    _TOS = True
except ImportError:
    _TOS = False

# 配置
ARK_API_KEY  = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 视频模型：doubao-seedance-2-0-260128（高质量）或 doubao-seedance-2-0-fast-260128（快速）
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "doubao-seedance-2-0-260128")
# 图片模型（人设图/分镜图，独立于 Seedance）
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415")

# TOS 对象存储配置（用于将本地图片转为公网 URL 后传给 Seedance）
TOS_BUCKET   = os.getenv("TOS_BUCKET", "")
TOS_REGION   = os.getenv("TOS_REGION", "cn-beijing")
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "tos-cn-beijing.volces.com")


# TOS 上传

def upload_to_tos(local_path: Path) -> str:
    """
    将本地文件上传到 TOS，返回公网可访问的 URL。
    若 TOS 未配置，以 file:// 路径占位（Seedance 不接受，仅供开发调试）。
    """
    if not (_TOS and TOS_BUCKET):
        print(f"    [未配置 TOS] 本地路径: {local_path}  (视频生成时将失败，请配置 TOS_BUCKET)")
        return str(local_path.absolute())

    ak = os.getenv("TOS_ACCESS_KEY")
    sk = os.getenv("TOS_SECRET_KEY")
    client = _tos_lib.TosClientV2(ak=ak, sk=sk, endpoint=TOS_ENDPOINT, region=TOS_REGION)

    key = f"seedance/{datetime.now().strftime('%Y%m%d')}/{local_path.name}"
    client.put_object_from_file(bucket=TOS_BUCKET, key=key, file_path=str(local_path))

    url = f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{key}"
    print(f"    ✓ 已上传 TOS: {url}")
    return url


# 图片生成（Seedream，人设图/分镜图）

def api_generate_image(prompt: str, width: int, height: int) -> Path:
    """调用图片生成接口，返回本地临时文件路径"""
    resp = requests.post(
        f"{ARK_BASE_URL}/images/generations",
        headers={"Authorization": f"Bearer {ARK_API_KEY}", "Content-Type": "application/json"},
        json={"model": IMAGE_MODEL, "prompt": prompt, "size": f"{width}x{height}", "n": 1},
        timeout=60
    )
    resp.raise_for_status()
    image_url = resp.json()["data"][0]["url"]

    data = requests.get(image_url, timeout=120).content
    tmp = Path(f"_tmp_{int(time.time()*1000)}.png")
    tmp.write_bytes(data)
    return tmp


# 视频生成（Seedance 2.0，官方 SDK）

def api_generate_video(
    prompt: str,
    duration: int,
    image_urls: list = None,
    video_urls: list = None,
    audio_urls: list = None
) -> Path:
    """
    调用 Seedance 2.0 生成视频。
    素材必须为公网可访问的 URL（Seedance 不支持 base64）。
    """
    if not _SDK:
        raise RuntimeError("请先安装官方 SDK: pip install 'volcengine-python-sdk[ark]'")

    client = Ark(base_url=ARK_BASE_URL, api_key=ARK_API_KEY)

    # 按官方格式构建 content 数组
    content = [{"type": "text", "text": prompt}]

    for url in (image_urls or []):
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})

    for url in (video_urls or []):
        content.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})

    for url in (audio_urls or []):
        content.append({"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"})

    print(f"    提交任务...")
    result = client.content_generation.tasks.create(
        model=VIDEO_MODEL,
        content=content,
        generate_audio=True,
        ratio="16:9",
        duration=min(duration, 15),
        watermark=True
    )
    task_id = result.id
    print(f"    任务 ID: {task_id}")

    # 轮询（官方建议每 30 秒查一次，状态字段: status，终止值: succeeded / failed）
    for i in range(120):
        time.sleep(30)
        get_result = client.content_generation.tasks.get(task_id=task_id)
        status = get_result.status
        print(f"    [{i+1}] 状态: {status}")

        if status == "succeeded":
            video_url = get_result.output.video_url
            data = requests.get(video_url, timeout=300).content
            tmp = Path(f"_tmp_{int(time.time()*1000)}.mp4")
            tmp.write_bytes(data)
            return tmp

        if status == "failed":
            raise RuntimeError(f"视频生成失败: {getattr(get_result, 'error', '未知')}")

    raise TimeoutError("视频生成超时（1 小时）")


# 引用解析

def parse_references(prompt: str, assets: dict) -> dict:
    """
    解析提示词中的 @引用，返回分类的 URL 列表。

    assets 格式: {"角色名": "https://...", "分镜图": "https://...", ...}
    返回: {"images": [...], "videos": [...], "audios": [...]}
    """
    refs = {"images": [], "videos": [], "audios": []}

    for name in set(re.findall(r'@([\w一-龥]+)', prompt)):
        if name not in assets:
            continue
        url = assets[name]
        low = url.lower()
        if any(low.endswith(e) for e in ('.png', '.jpg', '.jpeg', '.webp')):
            refs["images"].append(url)
            print(f"    ✓ 引用图片 @{name}")
        elif any(low.endswith(e) for e in ('.mp4', '.mov', '.avi')):
            refs["videos"].append(url)
            print(f"    ✓ 引用视频 @{name}")
        elif any(low.endswith(e) for e in ('.mp3', '.wav')):
            refs["audios"].append(url)
            print(f"    ✓ 引用音频 @{name}")
        else:
            # TOS 路径或无扩展名时，默认按图片处理
            refs["images"].append(url)
            print(f"    ✓ 引用素材 @{name}（按图片处理）")

    return refs


# 交互确认

def confirm_or_retry(file_path: Path, step_name: str):
    """返回 True=确认 / False=重新生成 / 'edit'=编辑提示词"""
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"  文件: {file_path.absolute()}")
    print(f"{'='*60}")
    while True:
        choice = input("  [c]确认继续 / [r]重新生成 / [e]编辑提示词 > ").strip().lower()
        if choice in ('c', 'r', 'e'):
            return True if choice == 'c' else (False if choice == 'r' else 'edit')
        print("  无效输入，请输入 c/r/e")


#  流水线

def workflow_pipeline(script_path: str, output_dir: str = "output"):
    """完整视频制作流水线"""

    if not ARK_API_KEY:
        raise ValueError("请设置环境变量 ARK_API_KEY")

    script    = json.loads(Path(script_path).read_text(encoding='utf-8'))
    proj_name = script.get("project_name", "未命名项目")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root      = Path(output_dir) / f"{proj_name}_{timestamp}"
    char_dir  = root / "1_characters"
    story_dir = root / "2_storyboards"
    video_dir = root / "3_videos"

    for d in (char_dir, story_dir, video_dir):
        d.mkdir(parents=True, exist_ok=True)

    (root / "script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # assets 字典存储 URL（TOS 或本地路径），供 @引用解析使用
    characters  = {}   # {"角色名": url}
    storyboards = []   # 按顺序存 URL
    videos      = []

    print(f"\n 项目: {proj_name}")
    print(f" 输出: {root.absolute()}\n")

    #  步骤 1：人设图
    print("=" * 60)
    print("【步骤 1/3】生成人设图")
    print("=" * 60)

    for i, char in enumerate(script.get("characters", []), 1):
        name   = char["name"]
        prompt = char["prompt"]
        print(f"\n({i}/{len(script['characters'])}) {name}")

        while True:
            try:
                tmp   = api_generate_image(prompt, char.get("width", 512), char.get("height", 768))
                final = char_dir / f"{name}.png"
                shutil.move(str(tmp), str(final))

                action = confirm_or_retry(final, f"人设图 - {name}")
                if action == 'edit':
                    prompt = char["prompt"] = input("  新提示词: ").strip() or prompt
                    continue
                if action:
                    characters[name] = upload_to_tos(final)
                    break
                # False → 重新生成，继续循环
            except Exception as e:
                print(f"  生成失败: {e}")
                if input("  [r]重试 / [s]跳过 > ").strip().lower() != 'r':
                    break

    print(f"\n人设图完成，共 {len(characters)} 个")

    #  步骤 2：分镜图
    print("\n" + "=" * 60)
    print("【步骤 2/3】生成分镜图")
    print("=" * 60)

    for i, scene in enumerate(script.get("storyboards", []), 1):
        sid    = scene.get("scene_id", i)
        prompt = scene["prompt"]
        print(f"\n({i}/{len(script['storyboards'])}) 分镜 #{sid}")

        while True:
            try:
                tmp   = api_generate_image(prompt, scene.get("width", 1024), scene.get("height", 576))
                final = story_dir / f"scene_{sid:03d}.png"
                shutil.move(str(tmp), str(final))

                action = confirm_or_retry(final, f"分镜 #{sid}")
                if action == 'edit':
                    prompt = scene["prompt"] = input("  新提示词: ").strip() or prompt
                    continue
                if action:
                    storyboards.append(upload_to_tos(final))
                    break
            except Exception as e:
                print(f"  生成失败: {e}")
                if input("  [r]重试 / [s]跳过 > ").strip().lower() != 'r':
                    break

    print(f"\n分镜图完成，共 {len(storyboards)} 个")

    #  步骤 3：视频
    print("\n" + "=" * 60)
    print("【步骤 3/3】生成视频")
    print("=" * 60)

    for i, scene in enumerate(script.get("storyboards", []), 1):
        sid      = scene.get("scene_id", i)
        prompt   = scene["prompt"]
        duration = scene.get("duration", 5)
        print(f"\n({i}/{len(script['storyboards'])}) 视频 #{sid}  {duration}s")

        while True:
            try:
                # 组合可引用的资源：人设图 URL + 当前分镜图 URL + 音频文件
                all_assets = dict(characters)
                if i <= len(storyboards):
                    all_assets["分镜图"] = storyboards[i - 1]

                audio_file = scene.get("audio")
                if audio_file and Path(audio_file).exists():
                    all_assets["背景音乐"] = upload_to_tos(Path(audio_file))

                refs = parse_references(prompt, all_assets)

                # 分镜图始终作为第一个 image 参考（提升画面一致性）
                if i <= len(storyboards) and storyboards[i-1] not in refs["images"]:
                    refs["images"].insert(0, storyboards[i - 1])

                tmp   = api_generate_video(prompt, duration, refs["images"], refs["videos"], refs["audios"])
                final = video_dir / f"video_{sid:03d}.mp4"
                shutil.move(str(tmp), str(final))

                action = confirm_or_retry(final, f"视频 #{sid}")
                if action == 'edit':
                    prompt = scene["prompt"] = input("  新提示词: ").strip() or prompt
                    continue
                if action:
                    videos.append(str(final))
                    break
            except Exception as e:
                print(f"  生成失败: {e}")
                import traceback; traceback.print_exc()
                if input("  [r]重试 / [s]跳过 > ").strip().lower() != 'r':
                    break

    print(f"\n视频完成，共 {len(videos)} 个")

    #  汇总日志
    log = {
        "project": proj_name,
        "generated_at": datetime.now().isoformat(),
        "characters": characters,
        "storyboards": storyboards,
        "videos": videos
    }
    (root / "workflow.log").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n全部完成！")
    print(f"输出目录: {root.absolute()}")


# CLI 入口

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("""
╔═══════════════════════════════════════════════════════════╗
║   Seedance 2.0 视频制作流水线                             ║
╚═══════════════════════════════════════════════════════════╝

用法:
  python main.py <剧本.json> [输出目录]

环境变量（必需）:
  ARK_API_KEY     - 火山方舟 API Key
  IMAGE_MODEL     - 图片模型（默认: doubao-seedream-3-0-t2i-250415）
  VIDEO_MODEL     - 视频模型（默认: doubao-seedance-2-0-260128）

环境变量（TOS 上传，推荐配置）:
  TOS_BUCKET      - TOS 存储桶名称
  TOS_REGION      - TOS 区域（默认: cn-beijing）
  TOS_ACCESS_KEY  - TOS Access Key
  TOS_SECRET_KEY  - TOS Secret Key

依赖安装:
  pip install 'volcengine-python-sdk[ark]'   # 视频生成（必需）
  pip install requests                        # 图片生成（必需）
  pip install tos                             # TOS 上传（推荐）

剧本格式 (JSON):
{
  "project_name": "项目名称",
  "characters": [
    {"name": "主角", "prompt": "...", "width": 512, "height": 768}
  ],
  "storyboards": [
    {"scene_id": 1, "prompt": "@主角 站在...", "duration": 5, "audio": "bgm.mp3"}
  ]
}

交互命令:
  c - 确认继续  r - 重新生成  e - 编辑提示词  s - 跳过（出错时）

注意:
  - 视频时长 4~15 秒
  - Seedance 不接受 base64，图片需上传至 TOS 获取公网 URL
  - 不支持上传真人人脸素材
        """)
        sys.exit(0)

    script_file = sys.argv[1]
    output_dir  = sys.argv[2] if len(sys.argv) > 2 else "output"

    if not Path(script_file).exists():
        print(f"剧本文件不存在: {script_file}")
        sys.exit(1)

    try:
        workflow_pipeline(script_file, output_dir)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
