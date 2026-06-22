# CCWS Image Generation Skill Installer

这是 CCWS 生图 Codex Skill 的一键安装包。

它会安装 `ccws-image-generation` 技能，用 CCWSPro 的 `gpt-image-2` 接管 Codex 中所有 AI 生图、图片编辑、图生图、局部修改、背景替换等任务。

## 使用方式

从 [Releases](https://github.com/xiaofengtongxue-lab/ccws-codex-image-skill/releases) 下载对应版本的安装包。

当前版本：

```text
ccws-image-generation-installer.zip
```

解压后把整个文件夹交给 AI，或在解压目录运行：

```bash
python3 install.py --yes
```

Windows PowerShell:

```powershell
py -3 .\install.py --yes
```

## 安装流程

安装器会按顺序执行：

1. 检查本地生图技能。如果除了官方 `imagegen` 之外还有其他生图技能，会建议先卸载或移走，避免触发冲突；用户也可以继续安装。
2. 检查 `CCWS_IMAGE_API_KEY`。如果当前环境没有配置，会停止安装，不写入技能文件。
3. 安装 `ccws-image-generation` 技能。
4. 提示用户新开 Codex 会话或重启 Codex 后再生图。

## API Key

请到 CCWSPro 控制台创建生图分组 API KEY，并确保令牌包含：

```text
model: gpt-image-2
```

然后配置环境变量：

```bash
export CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
```

Windows PowerShell:

```powershell
$env:CCWS_IMAGE_API_KEY="你的 CCWSPro 令牌"
```

不要把 API KEY 发到聊天里。

## 版本

当前版本：`1.0.0`

压缩包 SHA256：

```text
b891152a15527fecc62197fa148a7595916b62673acd80da39ca2f5fc4848b17
```
