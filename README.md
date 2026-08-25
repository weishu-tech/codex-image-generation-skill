# Custom Image Generation Skill Installer

这是一个不绑定具体品牌的 Codex 生图 Skill macOS / Windows 一键安装包。

它会安装 `custom-image-generation`，通过支持 `gpt-image-2` 的兼容 API 完成 AI 生图、图片编辑、图生图、局部修改和背景替换等任务。

## 一键安装

从 [Releases](https://github.com/xiaofengtongxue-lab/codex-image-generation-skill/releases) 下载并解压：

```text
image-generation-installer.zip
```

- macOS：双击 `install-macos.command`
- Windows：双击 `install-windows.bat`

安装过程中只要求输入两项：

1. API 地址（必填，不提供默认值），例如 `https://api.example.com`
2. 支持 `model: gpt-image-2` 的 API Key

API 地址末尾没有精确的 `/v1` 时，安装器会自动补充；已经带有 `/v1` 时不会重复添加。API Key 使用隐藏输入，不会回显。安装完成后重启 Codex，或新开一个 Codex 任务即可使用。

从旧版升级时，安装器会自动备份旧 Skill，并在新的通用配置尚不存在时沿用旧配置中的 API 地址和 API Key。旧名称只保留在迁移逻辑中，不再作为产品名称展示。

## 一键卸载

在解压后的安装包目录中运行：

- macOS：双击 `uninstall-macos.command`
- Windows：双击 `uninstall-windows.bat`

卸载器会先列出本次将删除的准确路径，然后只询问一次是否继续；直接回车或输入其他内容会取消，不删除任何文件。卸载时不需要再次输入 API 地址或 API Key。

确认后会删除：

1. 当前生效的 `custom-image-generation` Skill，包括标准用户目录和已设置的 `CODEX_HOME`
2. 保存 API 地址和 API Key 的 `image-generation.json`
3. 安装器自动安装的专用 CPython `3.12.10`

卸载器不会修改系统 Python、`PATH`、其他 Skill 或其他应用文件，也不会删除安装升级时生成的 `skill-backups` 历史备份。卸载完成后请重启 Codex，或新开一个 Codex 任务。

## 安装后使用

重启 Codex 或新建任务后，直接用自然语言描述生图、修图需求即可。Codex 会自动调用 `custom-image-generation`，通常不需要手动输入命令。

生成新图片：

```text
帮我生成一张雨夜上海街头的电影感照片，横版 16:9，高清，画面中不要出现文字。
```

修改已有图片时，可以在任务中上传图片，或提供本地图片路径：

```text
请把这张图片的背景改成雪山，人物、姿势、服装和面部保持不变。
```

需要明确指定 Skill 时，可以这样说：

```text
使用 $custom-image-generation 生成一张童话森林插画，横版，暖色调。
```

生成结果通常保存在当前项目的 `output/custom-image-generation/` 目录，Codex 会返回生成文件的路径；在 Codex 桌面版中也可以直接预览图片。

如果提示缺少 API 地址或 API Key，请重新运行一键安装器。不要把 API Key 发送到聊天中。接口调用失败时，请保留完整错误信息，并在售后群咨询。

无需预先安装 Python 3。安装器会自动下载官方 CPython `3.12.10`，安装到当前用户的专用目录，不要求管理员权限，不修改 `PATH`，也不会替换系统 Python。

Python 下载依次尝试：

1. 清华大学开源软件镜像站
2. 华为云镜像站
3. npmmirror
4. Python 官方源

每个下载文件都必须通过内置的固定 SHA256 校验；macOS 安装包还会验证 Python Software Foundation 的 Apple 签名。校验失败的文件不会被执行或解压。

固定校验值：

```text
macOS universal2  python-3.12.10-macos11.pkg       8373e58da4ea146b3eb1c1f9834f19a319440b6b679b06050b1f9ee3237aa8e4
Windows x64       python-3.12.10-embed-amd64.zip   4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3
Windows ARM64     python-3.12.10-embed-arm64.zip   3065efc3d382d1cda66757ac71ade11904fa6e350f5a97eb74811acd71ba5532
```

## 安装位置

全新安装默认写入当前 Codex 用户级技能目录：

```text
~/.agents/skills/custom-image-generation
```

如果已经安装在 `~/.codex/skills/custom-image-generation`，安装器会在原位置升级，避免产生两个同名技能。设置了 `CODEX_HOME` 时会遵循该目录。

配置文件保存在当前用户目录：

```text
macOS:  ~/Library/Application Support/Codex Image Generation/image-generation.json
Windows: %APPDATA%\Codex Image Generation\image-generation.json
```

专用 Python 运行时保存在：

```text
macOS:  ~/Library/Application Support/Codex Image Generation/Python/3.12.10
Windows: %LOCALAPPDATA%\Codex Image Generation\Python\3.12.10
```

macOS 上由安装器新建的配置目录会限制为当前用户，配置文件权限为 `0600`；Windows 上继承当前用户的 AppData 权限。不要把 API Key 发到聊天或提交到 Git。

## 命令行安装（已有 Python 3 时可选）

在解压目录运行：

```bash
python3 install.py --yes
```

Windows PowerShell:

```powershell
py -3 .\install.py --yes
```

交互终端同样只询问 API 地址和 API Key。自动化安装可以使用 `--non-interactive --api-url ... --api-key ...`，但 API Key 可能出现在进程参数中，仅建议用于受控测试。

## 版本

当前版本：`2.0.0`

压缩包 SHA256：

```text
0a537b5ae3dcf0814909bf57117997e8ff4bb4f1829285b8a1596687ad1b9ad9
```
