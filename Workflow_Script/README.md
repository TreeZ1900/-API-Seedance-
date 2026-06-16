#  Seedance 2.0 视频制作流水线工具

基于火山引擎官方 SDK 的完整视频制作自动化工具，支持：**人设生成 → 分镜绘制 → 视频合成**

##  核心改进

与官方示例代码相比，本工具提供以下增强功能：

###  自动化流水线
- **官方示例**：每次只能生成单个视频，需手动管理素材 URL
- **本工具**：一键完成「人设图 → 分镜图 → 视频」完整流程，自动管理素材关联

###  交互式确认
- **官方示例**：提交后只能等待结果，不满意需重新编写代码
- **本工具**：每一步完成后可预览、重新生成或编辑提示词，无需重跑整个流程

###  智能引用语法
- **官方示例**：需手动在 `content` 数组中配置每个素材的 URL 和 role
- **本工具**：使用 `@角色名` 语法自动解析引用，自动上传 TOS 并组装请求

###  目录自动整理
- **官方示例**：生成的视频需手动下载和分类
- **本工具**：按项目名和时间戳分类保存所有中间产物（人设/分镜/视频）

###  错误恢复
- **官方示例**：任何步骤失败需从头开始
- **本工具**：失败时可重试或跳过单个步骤，不影响已完成内容

---

##  安装与准备

###  1. 安装 Python

**Windows 用户**：
1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.8 或更高版本
3. 安装时勾选 "Add Python to PATH"

**验证安装**：
```bash
python --version
# 应显示: Python 3.x.x
```

###  2. 安装依赖包

在项目目录下打开命令行，依次执行：

```bash
# 必需依赖（视频生成）
pip install volcengine-python-sdk[ark]

# 必需依赖（图片生成）
pip install requests

# 推荐依赖（TOS 对象存储，用于将图片转为公网 URL）
pip install tos
```

**一键安装**（复制整段）：
```bash
pip install volcengine-python-sdk[ark] requests tos
```

###  3. 注册并开通服务

#### 步骤 1：注册火山引擎账号
访问 https://www.volcengine.com 完成注册

#### 步骤 2：账户充值
- 进入「费用中心」充值token
- 或购买 Seedance 2.0 资源包

#### 步骤 3：开通模型服务
1. 进入「火山方舟」控制台：https://console.volcengine.com/ark
2. 找到 Doubao Seedance 2.0 模型并点击「开通」
3. 找到 Doubao Seedream 3.0 图片生成模型并开通（用于生成人设图/分镜图）

#### 步骤 4：获取 API Key
1. 在火山方舟控制台点击「API Key 管理」
2. 点击「创建 API Key」
3. 复制并保存 API Key（务必妥善保管，不要泄露）

#### 步骤 5：配置 TOS 对象存储（推荐）
Seedance 2.0 要求图片素材必须是公网可访问的 URL，需要使用 TOS 对象存储。

1. 进入「对象存储 TOS」控制台：https://console.volcengine.com/tos
2. 创建存储桶（Bucket）：
   - 点击「创建存储桶」
   - 存储桶名称：如 `my-seedance-assets`
   - 区域：选择「华北2（北京）」
   - 访问权限：选择「公共读」（重要！）
3. 获取访问密钥：
   - 点击右上角用户名 → 「密钥管理」
   - 创建新的 Access Key 和 Secret Key
   - 复制并保存

###  4. 配置环境变量

**Windows 命令行**：
```cmd
set ARK_API_KEY=你的API_Key
set TOS_BUCKET=你的存储桶名称
set TOS_ACCESS_KEY=你的TOS_Access_Key
set TOS_SECRET_KEY=你的TOS_Secret_Key
```

**Windows PowerShell**：
```powershell
$env:ARK_API_KEY="你的API_Key"
$env:TOS_BUCKET="你的存储桶名称"
$env:TOS_ACCESS_KEY="你的TOS_Access_Key"
$env:TOS_SECRET_KEY="你的TOS_Secret_Key"
```

**macOS/Linux**：
```bash
export ARK_API_KEY="你的API_Key"
export TOS_BUCKET="你的存储桶名称"
export TOS_ACCESS_KEY="你的TOS_Access_Key"
export TOS_SECRET_KEY="你的TOS_Secret_Key"
```

**永久配置（可选）**：
- Windows：在「系统属性 → 环境变量」中添加
- macOS/Linux：将 export 命令添加到 `~/.bashrc` 或 `~/.zshrc`

---

##  快速开始

###  1. 创建剧本文件

创建 `my_script.json`：

```json
{
  "project_name": "我的第一个视频",
  "characters": [
    {
      "name": "主角小明",
      "prompt": "一个穿着蓝色T恤的少年，短发，微笑，动漫风格，全身像",
      "width": 512,
      "height": 768
    }
  ],
  "storyboards": [
    {
      "scene_id": 1,
      "prompt": "@主角小明 站在教室门口，阳光透过窗户洒进来，暖色调",
      "duration": 5
    },
    {
      "scene_id": 2,
      "prompt": "@主角小明 转身走进教室，镜头从左向右平移30度",
      "duration": 8
    }
  ]
}
```

###  2. 运行脚本

```bash
# 使用示例剧本
python main.py example_script.json

# 使用自己的剧本
python main.py my_script.json

# 指定输出目录
python main.py my_script.json ./output
```

###  3. 交互操作

脚本运行时会在每个步骤提示：

```
============================================================
  人设图 - 主角小明
  文件: C:\...\1_characters\主角小明.png
============================================================
  [c]确认继续 / [r]重新生成 / [e]编辑提示词 > 
```

**操作说明**：
- 输入 `c` 并回车：确认当前结果，进入下一步
- 输入 `r` 并回车：不满意，重新生成当前内容
- 输入 `e` 并回车：修改提示词后重新生成
- 输入 `s` 并回车：（出错时）跳过当前项

---

##  剧本格式详解

### JSON 结构

```json
{
  "project_name": "项目名称",
  "characters": [...],
  "storyboards": [...]
}
```

### `characters` 字段（人设图）

```json
{
  "name": "角色名称",           // 用于后续 @引用，必需
  "prompt": "角色描述",         // 生成提示词，必需
  "width": 512,                 // 可选，默认 512
  "height": 768                 // 可选，默认 768
}
```

**示例**：
```json
{
  "name": "小猫咪",
  "prompt": "一只可爱的橘色小猫，圆圆的眼睛，毛茸茸，卡通风格"
}
```

### `storyboards` 字段（分镜图 + 视频）

```json
{
  "scene_id": 1,                          // 场景编号，必需
  "prompt": "场景描述，支持 @引用",        // 必需
  "duration": 5,                          // 视频时长（秒），4~15，必需
  "width": 1024,                          // 分镜图宽度，可选，默认 1024
  "height": 576,                          // 分镜图高度，可选，默认 576
  "audio": "path/to/bgm.mp3"              // 背景音频，可选
}
```

**示例**：
```json
{
  "scene_id": 1,
  "prompt": "@主角小明 和 @小猫咪 在花园里玩耍，镜头缓缓推进",
  "duration": 8,
  "audio": "happy_bgm.mp3"
}
```

###  @引用语法

在 `prompt` 中使用 `@角色名` 自动引用之前生成的人设图：

```json
"prompt": "@主角小明 站在海边，@小猫咪 在脚边"
```

脚本会自动：
1. 识别 `@主角小明` 和 `@小猫咪`
2. 查找对应的人设图 URL
3. 添加到视频生成请求的 `reference_image` 中

---

##  输出结构

```
output/
└── 我的第一个视频_20260614_143025/
    ├── script.json              # 原始剧本副本
    ├── 1_characters/            # 人设图
    │   ├── 主角小明.png
    │   └── 小猫咪.png
    ├── 2_storyboards/           # 分镜图
    │   ├── scene_001.png
    │   ├── scene_002.png
    │   └── scene_003.png
    ├── 3_videos/                # 最终视频
    │   ├── video_001.mp4
    │   ├── video_002.mp4
    │   └── video_003.mp4
    └── workflow.log             # 生成日志（JSON 格式）
```

---

##  高级配置

###  环境变量完整列表

```bash
# 必需
ARK_API_KEY=your_api_key              # 火山方舟 API Key

# TOS 上传（推荐）
TOS_BUCKET=your_bucket                # TOS 存储桶名称
TOS_ACCESS_KEY=your_ak                # TOS Access Key
TOS_SECRET_KEY=your_sk                # TOS Secret Key
TOS_REGION=cn-beijing                 # TOS 区域，默认北京
TOS_ENDPOINT=tos-cn-beijing.volces.com # TOS 端点，默认自动生成

# 模型选择（可选）
VIDEO_MODEL=doubao-seedance-2-0-260128          # 视频模型（高质量）
# VIDEO_MODEL=doubao-seedance-2-0-fast-260128   # 快速版本（省钱）
IMAGE_MODEL=doubao-seedream-3-0-t2i-250415      # 图片生成模型
```

###  模型选择

**视频模型**：
- `doubao-seedance-2-0-260128`（默认）：最高质量，约 1 元/秒
- `doubao-seedance-2-0-fast-260128`：快速版本，质量稍低，成本更低

**图片模型**：
- `doubao-seedream-3-0-t2i-250415`（默认）：标准文生图模型

---

##  提示词技巧

###  人设图提示词

关键点：
- 明确风格：动漫风格、写实风格、卡通风格
- 描述细节：服装、发型、表情、姿势
- 指定视角：全身像、半身像、特写

**示例**：
```
一个穿着白色连衣裙的女孩，长发飘逸，温柔微笑，全身像，动漫风格，柔和光线，高清
```

###  分镜图/视频提示词

关键点：
- 具体描述动作：`镜头从左向右平移30度`（不要用模糊词如"摇镜"）
- 说明光线和色调：`暖色调`、`柔和光线`、`日落时分`
- 明确时序：`2-4秒：...，4-6秒：...`
- 使用 @引用：自动继承角色外观

**示例**：
```
@主角小明 站在海边，海浪拍打沙滩，日落时分，镜头从远景推到近景特写，暖色调，画面稳定
```

###  运镜术语

| 术语 | 说明 | 示例 |
|------|------|------|
| 推镜 | 镜头向前推进 | `镜头从远景推到近景` |
| 拉镜 | 镜头向后拉远 | `镜头从特写拉到全景` |
| 平移 | 水平移动 | `镜头从左向右平移30度` |
| 跟随 | 跟随主体移动 | `镜头跟随人物行走` |
| 固定机位 | 镜头不动 | `固定机位，人物从左走到右` |

---

##  注意事项

###  限制与规范

1. **视频时长**：4~15 秒（超过会自动截断为 15 秒）
2. **图片尺寸**：建议宽高 < 2048px，过大会超时
3. **音频格式**：仅支持 MP3 和 WAV
4. **人脸限制**：不支持上传真人写实人脸素材（平台合规要求）
5. **并发限制**：
   - 个人账户：最大 3 并发
   - 企业账户：最大 10 并发

###  生成速度

- 图片生成：约 10~30 秒/张
- 视频生成：约 30~60 秒/每 5 秒视频（取决于复杂度）
- 完整流水线（2 个角色 + 3 个分镜场景）：预计 10~20 分钟

###  费用估算

- 视频生成：约 **1 元/秒**（5 秒视频约 5 元）
- 图片生成：根据火山方舟实际定价（通常几分钱/张）
- 示例项目（2 角色 + 3 个 5 秒视频）：约 **15~20 元**

---

##  常见问题

###  Q1: 提示 "请先安装官方 SDK"
**A**: 运行以下命令安装依赖：
```bash
pip install volcengine-python-sdk[ark]
```

###  Q2: 提示 "未配置 TOS"，视频生成失败
**A**: Seedance 2.0 要求图片素材必须是公网 URL。请按照「安装与准备 → 步骤 5」配置 TOS 对象存储。

###  Q3: 视频生成失败，提示审核不通过
**A**: 检查提示词是否包含敏感内容，或是否上传了真人人脸素材。

###  Q4: 生成速度很慢
**A**: 
- 视频生成是异步任务，5 秒视频通常需要 30~60 秒
- 可切换到 `doubao-seedance-2-0-fast-260128` 快速模型
- 减少视频时长和分镜数量

###  Q5: 如何跳过某个失败的步骤
**A**: 出错时输入 `s` 跳过当前项，但注意：
- 跳过人设图：后续分镜和视频无法引用该角色
- 跳过分镜图：对应的视频仍会尝试生成（但缺少画面参考）

###  Q6: 能否使用本地图片而不上传 TOS
**A**: 不能。Seedance 2.0 API 要求图片必须是公网可访问的 URL，不接受 base64 或本地路径。

###  Q7: 生成的视频有水印
**A**: 代码中 `watermark=True` 是默认设置。如需去除水印，需在火山方舟控制台申请商业授权。

---

##  技术架构

###  工作流程

```
用户剧本 (JSON)
    ↓
【步骤 1】生成人设图
    ├─ 调用 Seedream 3.0 图片模型
    ├─ 下载到本地
    ├─ 上传到 TOS 获取公网 URL
    └─ 用户确认 (c/r/e)
    ↓
【步骤 2】生成分镜图
    ├─ 解析 @引用，关联人设图 URL
    ├─ 调用 Seedream 3.0 图片模型
    ├─ 上传到 TOS
    └─ 用户确认
    ↓
【步骤 3】生成视频
    ├─ 解析 @引用（人设 + 分镜 + 音频）
    ├─ 调用 Seedance 2.0 视频模型（官方 SDK）
    ├─ 轮询任务状态（每 30 秒）
    └─ 用户确认
    ↓
输出整理（按目录分类）
```

###  与官方 API 的对应关系

| 功能 | 本工具函数 | 官方 API |
|------|-----------|---------|
| 图片生成 | `api_generate_image()` | `/api/v3/images/generations` |
| 视频生成 | `api_generate_video()` | `client.content_generation.tasks.create()` |
| 任务查询 | 内置于 `api_generate_video()` | `client.content_generation.tasks.get()` |
| TOS 上传 | `upload_to_tos()` | TOS SDK |

---

##  参考资料

- [Seedance 2.0 官方文档](https://www.volcengine.com/docs/6791/1319426)
- [火山方舟控制台](https://console.volcengine.com/ark)
- [TOS 对象存储文档](https://www.volcengine.com/docs/6349/74828)
- [提示词优化技能](https://console.volcengine.com/ark)

---

##  许可证

MIT License
