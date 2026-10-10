# 常见问题（FAQ）

## 为什么公式在导图里是图片，不能像公式对象那样编辑？

因为 EdrawMind 的 **Word 导入器不解析 OMML**（Word 原生公式），会把公式拍平成字符：

```
\lim_{n \to \infty} S_n = S   →   limn→∞Sn=S
```

它自己的**原生公式对象**（`.emmx` 里存的是 MathML + PNG）只能在软件内部用「插入公式」生成，
而那个入口是**会员功能**，且它的对话框对 UI Automation 不可见（无法可靠自动化）。
详见 [FINDINGS.md](FINDINGS.md)。所以图片是当前唯一"导进去就看得见"的形态。

## 导入后公式变成了"批注/便签"，怎么办？

这是它的一个行为：**一条主题里公式夹在文字中间时，后面的元素会被当成批注**。
用默认模式即可避免——本工具会**把公式统一挪到主题末尾**：

```bash
python -m md2edrawmind convert 笔记.md            # 默认 --mix tail
```

## 提示"只能导入 50 个主题"，怎么办？

免费版对 **Word/HTML/Markdown 导入**限制 50 个主题。用自动切分：

```bash
python -m md2edrawmind convert 笔记.md --limit 46
```

会输出 `笔记-第1部分.docx`、`笔记-第2部分.docx`… 分别导入。
注意：`--mix tail` 会让每条公式单独占一个主题，主题数会比原文多（例如 94 → 192）。

## 为什么不用 HTML 导入？它的"智能解析"看起来也能出公式？

那条路走的是**云端 AI 解析**（`/ai/pptParse/parseFile`），实测会有三个问题：
**简体被转成繁体**、层级塌成平铺、公式变成标签。所以本项目只用本地导入（Word）。

## 哪些公式语法支持？

公式交给 **MathJax v3** 渲染，和 EdrawMind 自带的 EdrawMath 是同一套 TeX 引擎。
`\lim \sum \frac \int \sqrt \implies \left( \right)` 等常规写法都没问题；
`aligned` 等**多行环境**目前不支持（会按一行渲染），欢迎提 PR。

## 转换失败/很慢，怎么排查？

```bash
python -m md2edrawmind check        # 先看环境是否齐（Node / Chrome / mathjax-full）
```

- 卡在"渲染公式"：通常是浏览器没找到或被杀软拦了无头进程，试试手动执行一次 Chrome 无头截图；
- 报 `找不到 Node.js`：装 Node 18+；
- pip 安装后报 `mathjax-full 缺失`：执行 `md2edrawmind install-tools`；
- 公式很长被截断：调大 `tools/render.js` 里的 `--window-size` 高度。

## 导出 PDF 有水印？

图片形式的公式在 **PNG/JPG 导出没有水印**，但 **PDF 导出会带软件的试用水印**——这是软件策略，工具无法绕过。

## 能支持 XMind / MindManager / Obsidian 吗？

需要**先实测**目标软件能接受什么形态的公式（见 [CONTRIBUTING.md](../CONTRIBUTING.md)），
欢迎开 [Format 请求](https://github.com/socoolgzh-max/md2edrawmind/issues/new?template=format_request.md) 并附上你的实测结论。
