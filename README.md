# 感悟论语

传统文化对现代生活的启示

田冀焕 著

本书由个人博客「止于至善」（https://jihuan-tian.github.io/）的文章整理而成，供下载与阅读。排版稿开本为大32开，140mm × 203mm。

许可协议为知识共享署名-非商业性使用-禁止演绎 4.0 国际（CC BY-NC-ND 4.0）：不得修改，不得用于商业目的。详见 [`LICENSE`](LICENSE)。

阅读本：[`感悟论语.pdf`](https://github.com/jihuan-tian/ganwu-lunyu/releases/download/v1.0/ganwu-lunyu.pdf)

## 如何编译

需要 XeLaTeX，以及下列开源字体：

- 思源宋体 Noto Serif CJK（正文）
- TeX Gyre Pagella（西文，随 TeX Live 提供）
- 文鼎 PL 简中楷 AR PL UKai（引文）

在 Debian / Ubuntu 上可以安装：

```bash
sudo apt install texlive-xetex texlive-lang-chinese texlive-latex-extra \
  fonts-noto-cjk fonts-arphic-ukai python3-pil
```

然后：

```bash
make
```

`make` 会绘制卷首的水墨草木，并编译出 `感悟论语.pdf`。若要从原稿重新生成各卷正文，用 `make from-odt`（会覆盖 `chapters/` 里已改过的文件）。只改版式、不改图时，也可以直接：

```bash
latexmk -xelatex main.tex
```

## 版式

- 封面与尾页用浅茶色底。卷首页以松、竹、梅等草木为饰，并系于《论语》成句。松对应「岁寒，然后知松柏之后凋也」（《论语·子罕》）。
- 各卷单独成页，配一株草木和一句《论语》：
  - 品性与修养：松柏
  - 学习与科研：绿竹（《诗·卫风·淇奥》，「如切如磋，如琢如磨」）
  - 职场：梅（「磨而不磷，涅而不缁」）
  - 习惯：桃夭（《诗·周南》，「性相近也，习相远也」）
  - 家庭：荇菜（《诗·周南·关雎》）
  - 生活与社会：木瓜（《诗·卫风·木瓜》）
  - 论语学习与解读：唐棣之华（《论语·子罕》所引）
- 每一章另起一页，只有章名，不再配图。草木图只出现在各卷的卷首页。
- 引文用楷体，左侧一缕朱线。页眉外侧为书名或篇名，页码在下脚外侧。

原稿里的孔子像与石书照片，分别放在卷首。

## 文件

| 文件 | 作用 |
| --- | --- |
| `main.tex` | 版式、封面、页眉页脚 |
| `chapters/` | 卷首与每一卷各自的正文 |
| `artwork/` | 松、竹、梅与诗经草木 |
| `figures/` | 原稿中的插图 |
| `tools/odt_to_tex.py` | 把 `感悟论语.odt` 转为 `body.tex` |
| `tools/generate_artwork.py` | 绘制卷首植物 |

## Build (English)

```bash
make
```

This produces `感悟论语.pdf` with XeLaTeX. Body text is Noto Serif CJK, Latin is TeX Gyre Pagella, and classical quotations are AR PL UKai. All three are freely licensed open fonts. The book itself is CC BY-NC-ND 4.0; see `LICENSE`.
