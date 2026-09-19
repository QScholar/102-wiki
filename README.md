# YUNA102 Wiki

这是 YUNA102 的独立、多 Wiki 内容仓库。`main` 分支是 Wiki 内容的权威来源；GitHub Actions 会先校验配置与引用，再生成静态站点并发布到 GitHub Pages。

完整工程目标与验收条件见 [`docs/PROJECT_REQUIREMENTS.md`](docs/PROJECT_REQUIREMENTS.md)。

## 目录结构

```text
catalog.json                       # 全局 Wiki 注册表
content/<wiki>/wiki.json           # 单个 Wiki 配置
content/<wiki>/pages/              # Markdown 内容
content/<wiki>/media/gallery/      # 图册
content/<wiki>/media/markdown/     # 正文图片
content/<wiki>/media/video/        # 视频
builder/                           # 校验器和静态构建器
scripts/sync.sh                    # 校验后快进的安全同步脚本
templates/                         # 独立 Jinja 模板
static/                            # 独立前端资源
.github/workflows/pages.yml        # GitHub Pages 自动部署
```

## 本地预览

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m builder.validate
.venv/bin/python -m builder.build
.venv/bin/python -m http.server 8000 --directory dist
```

然后访问 `http://127.0.0.1:8000/`。项目页部署可通过 `--base-url /仓库名/` 验证子路径 URL：

```bash
.venv/bin/python -m builder.build --base-url /wiki-repository/
```

## 添加一个 Wiki

1. 复制 `content/jiaoxianting/` 的目录骨架并换成稳定 slug。
2. 修改新目录内的 `wiki.json`，保证 `id`、`slug` 和栏目 `id` 唯一。
3. 在 `catalog.json` 注册目录。
4. 运行 `python -m builder.validate`。

不需要修改 Flask 路由、构建器或模板。当前支持 `markdown`、`quotes`、`gallery` 和 `video` 四种栏目类型。

## 编辑与发布

```bash
git pull --ff-only
# 编辑 Markdown/JSON 或添加媒体
python -m builder.validate
git add .
git commit -m "更新 Wiki 内容"
git push origin main
```

服务器同步远端内容时使用：

```bash
./scripts/sync.sh
```

脚本会拒绝未提交修改和分叉分支，先在临时 Git 工作树校验远端内容，只有校验通过后才快进本地 `main`。同步失败不会替换当前可用内容。

仓库 Pages 的 Source 应选择 **GitHub Actions**。推送后，工作流会使用官方 Pages Actions 构建和部署。自定义域名准备完成后，在仓库 **Settings → Pages → Custom domain** 中填写 `102wiki.yuna.team`；域名设置不影响默认 `github.io` 地址构建。

仓库根目录的 `CNAME` 会由构建器校验并复制到 Pages 产物，当前值为 `102wiki.yuna.team`。

## 内容约束

- 图册支持 PNG、JPG、JPEG、GIF、WebP、BMP；视频支持 MP4、WebM、OGG、MOV、AVI。
- Markdown 正文图片应存放在当前 Wiki 的 `media/markdown/`，并用相对路径引用。
- 所有外部链接和外部图片必须使用 HTTPS。
- 普通 Git 单文件不得超过 100 MiB；更大的媒体需使用 Git LFS 或外部对象存储。
- 禁止提交 `.env`、令牌、密码、数据库、隧道配置或其他服务器秘密。
