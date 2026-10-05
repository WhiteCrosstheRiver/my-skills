# 第 4 层:3B1B 风格 Manim 讲解视频(可选层)

## 3B1B 是什么,为什么它适合 LLM 生成

3Blue1Brown:YouTube 数学科普频道,作者 Grant Sanderson。特征:

- **黑底画面**。公式和图形在纯黑上变形,无任何杂物。
- **一次只动一个东西**。其余全部静止或淡出。观众的注意力不需要分配。
- **画面贴旁白**。旁白说到哪,画面动到哪。没有"先看懂画面,再听解释"的时差。
- **全部是 Python 代码**(Manim 库)。这是 Karpathy 看好它的原因:LLM 写脚手架 = 写 Python。

三个特征就是三条设计规则。分镜时逐条对照。

## 流程

1. **分镜脚本**(从第 1 层稿子派生):逐句列 `旁白 | 画面动作 | 时长`。
   一句旁白 ≤ 25 字。一个画面动作只对应一句旁白。两句旁白之间,画面保持静止或缓慢淡出。
2. **TTS 先行**:先出音频,拿真实时长,动画节奏贴音频排。
   ```bash
   pip install edge-tts
   edge-tts --voice zh-CN-YunxiNeural --text "..." --write-media n01.mp3
   ```
   备选:piper(离线)。ffmpeg 合成音轨。
3. **Manim 渲染**:每句旁白一个场景段。宁多勿长。逐段对照分镜检查。

## Manim 骨架(ManimCE;从这里改,不要从零写)

```python
from manim import *

config.background_color = "#000000"   # 3B1B 铁律:纯黑底
FONT = "Noto Sans SC"                  # 中文必须指定,否则方块

class Intro(Scene):
    def construct(self):
        t = Text("为什么粒子不会粘在一起?", font=FONT, font_size=36)
        self.play(Write(t), run_time=1.5)
        self.wait(0.8)
        self.play(t.animate.scale(0.6).to_edge(UP))   # 讲到下一个话题才动它

        f = MathTex(r"V(r) = 4\varepsilon[(\sigma/r)^{12} - (\sigma/r)^6]")
        self.play(FadeIn(f, shift=UP*0.3), run_time=1.2)
        self.wait(1)
```

## 常见坑(Flash 级模型高发,按命中率排序)

- **库版本**:ManimCE(社区版,`pip install manim`,import manim)与 3b1b 的 ManimGL
  (import manimlib)API 不同。默认按 ManimCE 写。报 `ModuleNotFoundError: manimlib`,
  就是库用错了。
- **中文字体**:`Text` 必须传 `font=FONT`。`MathTex` 里的中文用不了,中文一律走 `Text`。
- **LaTeX**:MathTex 需要本机 LaTeX 环境。用户没装,就全部 `Text` + Unicode(π、σ、ᵣ)。
  不要现场让用户装 LaTeX。
- **Write 的限制**:只接受 VMobject(Text/MathTex 可以,Surface/ImageMobject 不行)。
- **时长**:写死 `run_time` 会跟音频脱节。用音频实际时长减 0.3s,留呼吸感。
- **画面过载**:一次 play 只动一个对象。想同时动两个,先问分镜里是不是两句旁白。

## 交付

- `Desktop/<概念名>-video/`:分镜 .md、脚本 .py、旁白 mp3、最终 mp4。
- 首渲后逐句检查:画面动作对应旁白、无中文乱码、无画面过载。返工 3–5 轮属正常预期。
- 视频里出现的每个公式仍以第 1 层稿子为准。做视频时发现稿子有错:先改稿,再改视频。
