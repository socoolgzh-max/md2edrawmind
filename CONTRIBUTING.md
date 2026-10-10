# 贡献指南

感谢愿意帮忙！这个项目很小，规则也就几条。

## 环境准备

```bash
git clone https://github.com/SoCoolp/md2edrawmind && cd md2edrawmind
pip install -r requirements.txt
npm install
python -m md2edrawmind check        # 应该全绿
```

还需要 Node.js 18+ 和 Chrome/Edge（无头渲染公式）。

## 提交前请跑这三条

```bash
python tests/test_parser.py         # 单元测试（无需浏览器）
python tests/smoke_gui.py 8899      # GUI 闭环（会起一个临时服务）
python -m md2edrawmind convert examples/考研数学-无穷级数.md -o build/check.docx
```

最后一条会用真实样例（94 主题 / 113 公式）跑完整链，是最有效的回归。

## 改动方向建议

| 方向 | 说明 |
| --- | --- |
| **新的目标格式** | XMind / FreeMind `.mm` / OPML 的适配器。注意：它们能否带公式需要**先实测**再写代码 |
| **平台兼容** | 目前路径探测偏 Windows；macOS / Linux 上 Chrome 与 Node 的探测可更完善 |
| **公式渲染质量** | 例如支持多行公式（`aligned` 环境）、矩阵、更大字号的导出 |
| **更好的切分策略** | 现在是贪心装箱；可以按"语义分支"切，而不是纯按数量 |

## 新增"目标软件适配器"的规范

如果你要让本工具支持别的思维导图软件，请**先做实测**并把结论写进 `docs/FINDINGS.md`：

1. 该软件**有哪些本地导入器**（不走云端 AI 的）？
2. 公式以什么形态能存活（图片 / OMML / MathML / 纯文字）？
3. 层级怎么表达（标题级别 / `w:outlineLvl` / 缩进）？
4. 有没有数量、大小、会员限制？

结论要带**具体证据**（导入后的截图、出错提示原文、文件内部片段），这样后来者能直接复用。

## 提交信息

用简短的前缀式提交信息：

```
feat: 支持 XMind 适配器
fix: 修复 PNG 切图在 4K 缩放下的偏移
docs: 补充 FINDINGS 里 Word 导入的层级细节
chore: 升级 mathjax-full
```

## 关于逆向发现

`docs/FINDINGS.md` 里的内容是**行为观测**，不是对软件内部实现的断言。如果你在别的版本上复现结果不同，
欢迎带着版本号与复现步骤提 issue 或 PR 修正——这对项目很有价值。
