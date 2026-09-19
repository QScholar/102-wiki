# Wiki 内容维护指南

这份指南适用于 YUNA102 Wiki 仓库。站点内容的权威来源是 GitHub 仓库 `QScholar/102-wiki` 的 `main` 分支；提交后，GitHub Actions 会先校验配置和内容，再发布到 GitHub Pages。本地服务器每天安全同步一次相同内容。

## 开始之前

每个 Wiki 都位于 `content/<wiki-slug>/`，典型结构如下：

```text
content/jiaoxianting/
├── wiki.json
├── pages/
│   ├── story.md
│   └── quotes.md
└── media/
    ├── gallery/
    ├── markdown/
    └── video/
```

- `wiki.json` 控制标题、封面和栏目。
- `pages/` 保存 Markdown 文章或语录。
- `media/gallery/` 保存图册图片。
- `media/markdown/` 保存文章中引用的图片。
- `media/video/` 保存视频。
- 路径、`id` 和 `slug` 发布后应保持稳定，否则旧链接会失效。

## 如何修改已有 Wiki

### 修改标题、简介或封面

打开目标 Wiki 的 `wiki.json`，修改以下字段：

```json
{
  "title": "焦显庭 Wiki",
  "subtitle": "人物数字档案",
  "description": "收录故事、语录、图册与影像资料",
  "logo": "media/gallery/IMG_20251021_200058.jpg"
}
```

封面可以指向当前 Wiki 的 `media/` 文件，也可以指向站点公共资源，例如 `/static/sakuya-logo.svg`。不要随意修改已经发布的 `id` 和 `slug`。

### 修改文章或语录

直接编辑 `pages/` 中由栏目 `source` 指定的 Markdown 文件。

- `markdown` 类型按普通 Markdown 文章显示。
- `quotes` 类型会把每个 Markdown 段落显示为一张语录卡片；语录之间留一个空行。
- 外部链接和外部图片必须使用 `https://`。

文章图片先上传到 `media/markdown/`，再从 `pages/*.md` 使用相对路径引用：

```markdown
![图片说明](../media/markdown/example.jpg)
```

构建器会自动把它转换为当前 Wiki 的媒体 URL。图片不能引用当前 Wiki `media/` 目录以外的本地文件。

### 添加或替换图册图片

把图片直接上传到栏目 `source` 指定的目录，例如：

```text
content/jiaoxianting/media/gallery/
```

支持 PNG、JPG、JPEG、GIF、WebP 和 BMP。文件按名称排序；可以使用 `01-`、`02-` 等前缀控制顺序。删除文件会使它在下一次部署后从图册消失。

### 添加或替换视频

把视频直接上传到栏目 `source` 指定的目录，例如：

```text
content/jiaoxianting/media/video/
```

支持 MP4、WebM、OGG、MOV 和 AVI。浏览器兼容性优先选择 MP4（H.264/AAC）或 WebM。普通 Git 单文件不能超过 100 MiB。

## 如何添加新栏目

新增栏目只需要准备内容并修改当前 Wiki 的 `wiki.json`，不需要增加 Flask 路由、构建脚本或模板。

### 第一步：创建栏目内容

按照栏目类型创建文件或目录：

| `type` | `source` 应指向 | 用途 |
| --- | --- | --- |
| `markdown` | 一个 Markdown 文件 | 普通文章 |
| `quotes` | 一个 Markdown 文件 | 语录卡片 |
| `gallery` | 一个图片目录 | 自动图册与灯箱 |
| `video` | 一个视频目录 | 视频列表 |

例如，要新增“资料”文章栏目，先创建：

```text
content/jiaoxianting/pages/profile.md
```

### 第二步：注册栏目

在 `wiki.json` 的 `sections` 数组中加入配置：

```json
{
  "id": "profile",
  "name": "资料",
  "icon": "file-text",
  "type": "markdown",
  "source": "pages/profile.md"
}
```

保存并发布后会自动生成：

```text
/jiaoxianting/profile/
```

同时，Wiki 首页会自动出现“资料”标签页。

字段约束：

- `id` 只能包含小写字母、数字和连字符，并且在当前 Wiki 中唯一。
- `name` 是页面上显示的栏目名称。
- `icon` 使用 Lucide 图标名称，例如 `file-text`、`images`、`book-open-text`。
- `type` 必须是当前支持的四种类型之一。
- `source` 必须位于当前 Wiki 目录内，并且文件或目录必须已经存在。
- `sections` 中的排列顺序就是首页标签页顺序。

图册栏目的配置示例：

```json
{
  "id": "works",
  "name": "作品",
  "icon": "image",
  "type": "gallery",
  "source": "media/works"
}
```

视频栏目的配置示例：

```json
{
  "id": "interviews",
  "name": "访谈",
  "icon": "clapperboard",
  "type": "video",
  "source": "media/interviews"
}
```

添加目录型栏目时，即使暂时没有媒体，也要先提交空目录中的占位文件；Git 本身不会保存完全空的目录。占位文件使用不受支持的扩展名即可，页面不会展示它。

## 如何添加一个全新的 Wiki

1. 在 `content/` 下创建使用稳定 slug 命名的新目录。
2. 添加 `wiki.json`、`pages/` 和 `media/`。
3. 在仓库根目录的 `catalog.json` 中注册它。
4. 确保 `catalog.json` 中的 `id` 与新 Wiki 的 `wiki.json` 中的 `id` 完全一致。
5. 执行校验并提交。

注册示例：

```json
{
  "id": "example-person",
  "directory": "content/example-person",
  "enabled": true,
  "featured": false
}
```

`enabled: false` 会让该 Wiki 不参与构建和导航；`featured: true` 会让它在总目录中优先显示。

## 校验与发布

在本地修改时，从 Wiki 仓库根目录执行：

```bash
git pull --ff-only
../.venv/bin/python -m builder.validate
../.venv/bin/python -m unittest discover -s tests -v
git add catalog.json content docs
git commit -m "更新 Wiki 内容"
git push origin main
```

如果仓库拥有自己的 `.venv`，将示例中的 `../.venv/bin/python` 换成 `.venv/bin/python`。

通过 GitHub 网页修改时：

1. 打开要修改的 Markdown 或 JSON 文件。
2. 使用编辑按钮修改，或进入目标媒体目录上传文件。
3. 提交到 `main`。
4. 在仓库的 Actions 页面确认 `Deploy Wiki to GitHub Pages` 成功。
5. 若校验失败，根据 Actions 日志修正后再次提交；失败版本不会覆盖当前线上站点。

发布后检查 Wiki 总目录、目标 Wiki 首页和本次修改的栏目。服务器本地镜像会在每日同步任务执行后更新；需要立即同步时，可在服务器的 Wiki 仓库中运行 `./scripts/sync.sh`。

## 常见失败原因

- JSON 少逗号、多逗号或使用了中文引号。
- 新栏目的 `source` 文件或目录尚未创建。
- `id`、`slug` 重复，或包含大写字母、空格、下划线。
- Markdown 图片路径不在当前 Wiki 的 `media/` 下。
- 外部链接使用了 `http://`。
- 单个媒体文件超过 100 MiB。
- 在服务器工作副本中留下未提交修改，导致安全同步主动停止。
