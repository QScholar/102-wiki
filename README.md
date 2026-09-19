# YUNA102 Wiki

YUNA102 Wiki 是一个独立、多 Wiki 的内容仓库。`main` 分支是 Wiki 内容的权威来源；同一套配置和模板同时供 GitHub Pages 静态站点与 YUNA102 服务器本地 Flask 镜像使用。

- 线上站点：<https://102wiki.yuna.team/>
- 内容维护指南：<https://102wiki.yuna.team/guide/>
- GitHub 仓库：<https://github.com/QScholar/102-wiki>

## 工作方式

```text
编辑 Markdown、JSON 或媒体
            ↓
        push 到 main
            ↓
  GitHub Actions 校验并构建
       ├─ 发布 GitHub Pages
       └─ 失败时保留上一版本

服务器每日安全同步 origin/main
            ↓
本地 Flask 按请求读取相同内容
```

## 目录结构

```text
.
├── catalog.json                   # 全局 Wiki 注册表
├── CNAME                          # GitHub Pages 自定义域名
├── content/
│   └── <wiki-slug>/
│       ├── wiki.json              # Wiki 元数据与栏目注册
│       ├── pages/                 # Markdown 与语录
│       └── media/
│           ├── gallery/           # 图册图片
│           ├── markdown/          # 正文图片
│           └── video/             # 视频
├── docs/
│   ├── content-guide.md           # 对外发布的内容维护指南
│   └── PROJECT_REQUIREMENTS.md     # 工程需求与验收标准
├── builder/
│   ├── site.py                    # 配置校验、URL 与页面渲染
│   ├── validate.py                # 完整内容校验入口
│   └── build.py                   # 静态站点构建入口
├── templates/                     # Wiki 独立 Jinja 模板
├── static/                        # Wiki CSS、JavaScript、字体和图标
├── tests/                         # 构建器回归测试
├── scripts/sync.sh                # 服务器安全快进同步
└── .github/workflows/pages.yml    # GitHub Pages 自动部署
```

## 内容模型

`catalog.json` 负责注册 Wiki。每个已启用 Wiki 的 `wiki.json` 定义稳定的 `id`、URL `slug`、标题、封面和 `sections`。

当前栏目渲染器支持：

| 类型 | 内容源 | 页面效果 |
| --- | --- | --- |
| `markdown` | 单个 Markdown 文件 | 普通文章 |
| `quotes` | 单个 Markdown 文件 | 段落式语录卡片 |
| `gallery` | 图片目录 | 自动排序图册与灯箱 |
| `video` | 视频目录 | 支持浏览器播放的视频列表 |

栏目和 Wiki 路由由配置自动生成。添加新 Wiki 或新栏目不需要修改 Flask 路由。

## 编辑内容

如何修改标题、封面、文章、语录和媒体，以及如何添加栏目或全新 Wiki，见：

- 网站中的[内容维护指南](https://102wiki.yuna.team/guide/)
- 仓库中的 [`docs/content-guide.md`](docs/content-guide.md)

最短发布流程：

```bash
git pull --ff-only
# 编辑 catalog.json、content/ 或 docs/
python -m builder.validate
python -m unittest discover -s tests -v
git add catalog.json content docs
git commit -m "更新 Wiki 内容"
git push origin main
```

## 本地安装与预览

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m builder.validate
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m builder.build
.venv/bin/python -m http.server 8000 --directory dist
```

访问 `http://127.0.0.1:8000/`。若要模拟 GitHub 项目子路径：

```bash
.venv/bin/python -m builder.build --base-url /102-wiki/
```

构建产物使用目录式 URL，并自动包含 `.nojekyll`、静态资源、媒体和经过校验的 `CNAME`。

## 页面路由

GitHub Pages：

```text
/
/guide/
/<wiki-slug>/
/<wiki-slug>/<section-id>/
/<wiki-slug>/media/<filename>
```

服务器本地 Flask 在这些路径前增加 `/wiki`；经 Caddy 网关访问时再增加 `/index`，例如：

```text
https://102.yuna.team/index/wiki/
https://102.yuna.team/index/wiki/guide/
https://102.yuna.team/index/wiki/jiaoxianting/
```

## 校验规则

构建和 GitHub Actions 会拒绝：

- 缺失或不支持的 `schema_version`；
- 重复或非法的 Wiki `id`、`slug`、栏目 `id`；
- 使用站点保留 slug `guide` 或 `static`；
- 越出仓库或当前 Wiki 的路径；
- 缺失的栏目文件、目录、封面或 Markdown 图片；
- 不支持的栏目类型；
- 使用 `http://` 的 Markdown 外部链接；
- 超过 100 MiB 的媒体文件。

图片支持 PNG、JPG、JPEG、GIF、WebP、BMP；视频支持 MP4、WebM、OGG、MOV、AVI。

## 自动部署

推送 `main` 后，GitHub Actions 按顺序执行：

1. 检出仓库并安装依赖；
2. 运行 `python -m builder.validate`；
3. 读取 GitHub Pages 的基础 URL；
4. 运行 `python -m builder.build`；
5. 上传并部署官方 Pages artifact。

工作流只授予读取内容、写入 Pages 和签发部署 ID token 所需的最小权限。

## 服务器同步

服务器上的工作副本位于 `/home/yuna/yuna102server/wiki`。人工同步使用：

```bash
./scripts/sync.sh
```

脚本会拒绝未提交修改、非 `main` 分支和分叉历史；先在临时 Git 工作树校验 `origin/main`，成功后才执行快进更新。本机还通过用户级 `yuna102-wiki-sync.timer` 每日运行该脚本。

## 安全与公开内容

- 仓库和 Pages 站点均为公开内容，提交前确认文字、图片与视频适合公开。
- 禁止提交 `.env`、令牌、密码、数据库、服务器配置、证书或私钥。
- 外部链接和外部图片必须使用 HTTPS。
- 超过 100 MiB 的文件应改用 Git LFS 或外部对象存储。
- 本地构建产物不得包含服务器绝对路径或认证信息。

完整需求见 [`docs/PROJECT_REQUIREMENTS.md`](docs/PROJECT_REQUIREMENTS.md)。
