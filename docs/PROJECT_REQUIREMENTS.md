# YUNA102 Index 与 Wiki 工程需求

本文档记录当前已经确认的工程目标、内容模型、发布边界和验收条件，作为后续改造与部署的依据。

## 1. 项目目标

YUNA102 网站最终拆分为三个互不影响、内容来源清晰的运行目标：

| 目标 | 入口 | 职责 |
| --- | --- | --- |
| 本地 Flask | YUNA102 服务器现有入口 | 保留现有首页和 Wiki 访问形式，供服务器本地运行 |
| Cloudflare Pages | `https://102.yuna.team/` | 只发布 YUNA102 Index，不再承载 Wiki 页面 |
| GitHub Pages | `https://102wiki.yuna.team/` | 独立发布可扩展的 Wiki 站点 |

拆分后，Index 与 Wiki 可以分别部署和回滚；GitHub Pages 或 Cloudflare Pages 的部署失败不得影响本地 Flask 服务。

## 2. 内容与代码的权威来源

- Wiki GitHub 仓库的 `main` 分支是 Wiki 内容的唯一权威来源。
- Wiki 内容、配置、构建器、模板、公共静态资源和 GitHub Actions 工作流最终都应位于独立 Wiki 仓库。
- 本地 `/home/yuna/yuna102server/wiki` 是该仓库在服务器上的工作副本。
- 在 GitHub 网页或其他电脑完成修改并推送后，本地通过 `git pull --ff-only` 同步。
- 本地允许编辑，但必须先提交并推送到 GitHub，避免服务器形成长期存在的未提交修改。
- Cloudflare Pages 的 Index 源码继续由主项目管理，不复制 Wiki 内容。

预期的数据流：

```text
GitHub 编辑或本地 Git 编辑
          ↓ push
Wiki 仓库 main
    ├─ GitHub Actions 构建并部署 GitHub Pages
    └─ 本地服务器 git pull，同步给 Flask 使用
```

## 3. 页面与域名规划

### 3.1 GitHub Pages

GitHub Pages 使用独立域名并以 Wiki 总目录作为首页：

```text
https://102wiki.yuna.team/                       # Wiki 总目录
https://102wiki.yuna.team/jiaoxianting/          # 焦显庭 Wiki
https://102wiki.yuna.team/jiaoxianting/story/    # 故事
https://102wiki.yuna.team/jiaoxianting/quotes/   # 语录
https://102wiki.yuna.team/jiaoxianting/gallery/  # 图册
https://102wiki.yuna.team/jiaoxianting/video/    # 视频
```

将来新增 Wiki 时使用新的稳定 slug：

```text
https://102wiki.yuna.team/<wiki-slug>/
```

域名 DNS 和 GitHub Pages Custom domain 稍后配置；静态构建器在域名配置前也必须能通过本地 HTTP 服务器预览。

### 3.2 本地 Flask

本地继续保留现有访问形式，并增加 Wiki 总目录：

```text
/wiki/                         # Wiki 总目录
/wiki/jiaoxianting/            # 现有焦显庭 Wiki
/wiki/jiaoxianting/story/
/wiki/jiaoxianting/quotes/
/wiki/jiaoxianting/gallery/
/wiki/jiaoxianting/video/
```

本地页面保持现有视觉设计和功能，不因 GitHub Pages 拆分而依赖公网服务。

### 3.3 Cloudflare Pages Index

- Cloudflare Pages 只构建和发布 Index。
- `102index.md` 中的 Wiki 总入口指向 `https://102wiki.yuna.team/`。
- 若入口文案明确指向某个 Wiki，可直接链接到对应 slug，例如 `https://102wiki.yuna.team/jiaoxianting/`。
- 本地使用的 `index.md` 继续指向本地 `/wiki/` 或 `/wiki/jiaoxianting/`。
- Cloudflare Pages 上旧的 `/wiki/jiaoxianting/*` 公网地址应永久重定向到新域名的对应页面，避免旧书签失效。

## 4. 多 Wiki 内容模型

当前只有 `jiaoxianting`，但实现不得继续把 Wiki 名称和栏目写死在 Flask 路由或静态构建脚本中。

目标目录结构：

```text
wiki/
├── catalog.json
├── content/
│   ├── jiaoxianting/
│   │   ├── wiki.json
│   │   ├── pages/
│   │   │   ├── story.md
│   │   │   └── quotes.md
│   │   └── media/
│   │       ├── gallery/
│   │       ├── markdown/
│   │       └── video/
│   └── <another-wiki>/
│       ├── wiki.json
│       ├── pages/
│       └── media/
├── builder/
├── templates/
├── static/
└── .github/workflows/pages.yml
```

现有 `wiki/jiaoxianting/` 内容需要在改造时迁移到 `content/jiaoxianting/`；迁移必须保留所有 Markdown、图片、视频和 Git 历史。

## 5. 全局 Wiki 注册表

`catalog.json` 只描述整个 Wiki 站点和已启用的 Wiki，不保存运行环境 URL：

```json
{
  "schema_version": 1,
  "title": "YUNA102 Wiki",
  "description": "YUNA102 数字档案与知识集合",
  "wikis": [
    {
      "id": "jiaoxianting",
      "directory": "content/jiaoxianting",
      "enabled": true,
      "featured": true
    }
  ]
}
```

约束：

- `id` 必须唯一且稳定。
- `directory` 必须位于 Wiki 仓库内部，禁止 `..` 路径穿越。
- `enabled: false` 的 Wiki 不参与页面生成和导航展示。
- 可以有多个推荐 Wiki；`featured` 只控制总目录的展示优先级。
- 配置必须包含 `schema_version`，为以后迁移保留兼容能力。

## 6. 单个 Wiki 配置

每个 Wiki 使用独立的 `wiki.json`：

```json
{
  "schema_version": 1,
  "id": "jiaoxianting",
  "slug": "jiaoxianting",
  "title": "焦显庭 Wiki",
  "subtitle": "人物数字档案",
  "description": "收录故事、语录、图册与影像资料",
  "logo": "/static/sakuya-logo.svg",
  "theme": "archive",
  "sections": [
    {
      "id": "story",
      "name": "故事",
      "icon": "book-open-text",
      "type": "markdown",
      "source": "pages/story.md"
    },
    {
      "id": "quotes",
      "name": "语录",
      "icon": "message-square-quote",
      "type": "quotes",
      "source": "pages/quotes.md"
    },
    {
      "id": "gallery",
      "name": "图册",
      "icon": "images",
      "type": "gallery",
      "source": "media/gallery"
    },
    {
      "id": "video",
      "name": "视频",
      "icon": "clapperboard",
      "type": "video",
      "source": "media/video"
    }
  ]
}
```

配置要求：

- `slug` 只能使用小写字母、数字和连字符，并在全部 Wiki 中唯一。
- `id` 和 `slug` 发布后不得随意修改，避免已有链接失效。
- 栏目 `id` 在单个 Wiki 中唯一。
- 配置只声明内容和展示方式，不保存 `/wiki/...` 或完整域名。
- 本地 Flask 和 GitHub Pages 构建器根据运行环境生成 URL。
- `source` 必须位于当前 Wiki 目录内部。
- 不支持的 `type`、缺失文件和非法路径必须让构建失败并给出明确错误，不能静默生成空页面。

## 7. 栏目渲染类型

第一阶段必须支持现有四种类型：

| 类型 | 输入 | 输出 |
| --- | --- | --- |
| `markdown` | 单个 Markdown 文件 | 普通文章页面 |
| `quotes` | 单个 Markdown 文件 | 语录卡片页面 |
| `gallery` | 图片目录 | 自动排序的图册与灯箱 |
| `video` | 视频目录 | 自动排序的视频列表 |

渲染器需要通过类型注册表选择，不能再为每个 Wiki 或栏目增加一套硬编码函数。将来可以增加 `timeline`、`links`、`files` 等类型，而不改变现有配置格式。

当前媒体兼容范围：

- 图片：PNG、JPG、JPEG、GIF、WebP、BMP。
- 视频：MP4、WebM、OGG、MOV、AVI。
- GitHub 普通 Git 单文件上限为 100 MiB；更大的文件需要 Git LFS 或外部对象存储。

## 8. 路由与 URL 生成

本地 Flask 改为通用路由：

```text
/wiki/
/wiki/<wiki_slug>/
/wiki/<wiki_slug>/<section_id>/
/wiki/<wiki_slug>/media/<path:filename>
```

GitHub Pages 静态构建器生成：

```text
/
/<wiki_slug>/
/<wiki_slug>/<section_id>/
/<wiki_slug>/media/<path:filename>
```

URL 生成必须遵循以下原则：

- 配置数据与部署路径解耦。
- 页面链接统一由路由辅助函数或静态构建上下文生成。
- 输出目录使用 `index.html`，确保目录形式 URL 可访问。
- 文件名中的空格和中文必须正确进行 URL 编码。
- Markdown 中的外部图片 URL保持原样；本地相对图片映射到当前 Wiki 的媒体目录。
- 页面不得依赖 Flask 会话、数据库或服务端认证才能在 GitHub Pages 上运行。

## 9. GitHub 编辑与自动部署

Wiki 仓库需要支持以下日常流程：

1. 用户在 GitHub 网页、Git 客户端或本地服务器编辑 Markdown/JSON/媒体文件。
2. 修改提交到 `main`。
3. GitHub Actions 校验 JSON、路径、slug 和引用文件。
4. 校验通过后运行独立静态构建器。
5. 构建产物通过 GitHub Pages 官方 Actions 发布。
6. 部署失败时保留上一版本，不发布不完整产物。

构建器必须能在仓库根目录独立运行，不得依赖：

- `/home/yuna/yuna102server` 中 Wiki 仓库之外的文件；
- 本地 Flask 服务；
- 服务器密码、数据库或 `.env`；
- Cloudflare Pages 的构建产物。

GitHub Pages 的自定义域名通过仓库设置和构建时生成的 `CNAME` 管理。域名尚未启用时，构建流程不得因此失败。

## 10. 本地同步要求

初期支持人工同步：

```bash
cd /home/yuna/yuna102server/wiki
git pull --ff-only
```

后续可以增加 systemd timer 或 GitHub webhook 自动同步，但必须满足：

- 只允许快进更新，不自动合并冲突。
- 检测到本地未提交修改时停止同步并记录错误。
- 拉取完成后先校验配置，再让 Flask 使用新内容。
- 同步失败不得删除或覆盖当前可用内容。
- Markdown 和媒体更新应在下一次请求时可见。
- `catalog.json` 和 `wiki.json` 应按请求加载或使用文件修改时间缓存，正常内容同步不应要求重启 Flask。

## 11. Index 与 Wiki 的构建边界

主项目需要把现有静态构建拆分：

- Cloudflare Pages 构建只输出 Index 所需 HTML、CSS、JavaScript 和公共资源。
- Cloudflare Pages 输出中不再复制 Wiki 图片、视频和页面。
- Wiki GitHub 仓库自行生成完整 Wiki 静态站点。
- 本地 Flask 仍可同时提供 Index 和 Wiki。
- 两套构建可以共享视觉规范，但不得通过跨仓库相对路径才能成功构建。

## 12. 安全与发布约束

- Wiki Pages 是公开网站，发布前必须确认文字、图片、视频适合公开并已取得必要授权。
- Wiki 仓库不得包含 `.env`、令牌、数据库、隧道配置、服务器密码或其他部署秘密。
- 不得直接公开整个 `/home/yuna/yuna102server` 项目。
- 构建输出中不得泄露本地绝对路径、调试信息或认证配置。
- 外部链接使用 HTTPS。
- GitHub Actions 使用最小权限：读取仓库内容、写入 Pages、签发 Pages 部署所需的 ID token。
- 域名配置完成后启用 HTTPS，并保持 `102.yuna.team` 与 `102wiki.yuna.team` 的 Cookie、认证和安全边界相互独立。

## 13. 兼容与迁移要求

- 现有 `/wiki/jiaoxianting/` 本地地址继续工作。
- 现有 Markdown、图片和视频全部迁移，不能丢失。
- Cloudflare Pages 上的旧 Wiki URL重定向到新域名。
- 若栏目 slug 调整，需要建立永久重定向。
- 改造期间允许旧 Flask Wiki 与新 GitHub Pages 并行验证。
- 新站验证完成前不删除旧页面或旧部署产物。

## 14. 验收标准

第一阶段完成时应满足：

- `102.yuna.team` 的 Cloudflare Pages 版本只包含 Index。
- Index 中公网 Wiki 链接指向 `https://102wiki.yuna.team/` 或具体 Wiki 地址。
- `102wiki.yuna.team/` 显示 Wiki 总目录。
- `102wiki.yuna.team/jiaoxianting/` 及四个现有栏目正常显示。
- 中文文件名、图片灯箱、视频播放、主题切换在静态站点中正常工作。
- 在 GitHub 修改 Markdown 并提交后，GitHub Pages 自动更新。
- 本地执行 `git pull --ff-only` 后，相同内容能在本地 Flask Wiki 中访问。
- 新增一个测试 Wiki 只需要新增内容目录和注册配置，不需要增加 Flask 路由。
- GitHub Actions 能阻止无效配置、缺失内容和非法路径进入生产部署。
- 旧公网 Wiki 地址能跳转到新域名的对应页面。

## 15. 实施顺序

1. 建立新的目录结构和配置校验器。
2. 将焦显庭 Wiki 内容迁移到 `content/jiaoxianting/`。
3. 把 Flask Wiki 路由改为通用多 Wiki 路由。
4. 制作可独立运行的静态构建器和 Wiki 总目录。
5. 添加 GitHub Actions 构建、校验和 Pages 部署。
6. 拆分 Cloudflare Pages 的 Index 构建并更新公网链接。
7. 并行验证本地 Flask、Cloudflare Pages 和 GitHub Pages。
8. 配置 `102wiki.yuna.team` DNS、自定义域名和 HTTPS。
9. 添加旧 URL 重定向。
10. 根据需要启用本地自动同步。

## 16. 尚待确定

以下参数不阻塞代码结构设计，但需要在正式发布前确认：

- GitHub 账号或组织名称。
- Wiki 仓库最终名称与公开/私有属性。
- GitHub Pages 临时默认地址。
- `102wiki.yuna.team` 的 DNS 配置时间。
- 本地采用人工同步、systemd timer 还是 GitHub webhook。
- 超过 100 MiB 的未来媒体使用 Git LFS 还是外部对象存储。
