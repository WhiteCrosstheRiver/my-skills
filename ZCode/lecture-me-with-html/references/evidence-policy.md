# Evidence Policy — Claim Ledger 是唯一事实源

## Claim 格式(dossier 内)

```text
C017
Claim : 对线性算符 L 与指定(齐次)边界条件,Green 函数满足 L G = δ。
Type  : definition | theorem | interpretation | application | historical | numeric
来源  : S3, S5, S9
置信  : high | medium | low
假设  : 线性;边界齐次
用于  : P07, P08
```

## 规则

1. **先立 Claim,再写页面。** 页面文字、图、例题、quiz 都是对 Claim 的派生与呈现。
2. 页面里每一条:定义/定理/数值/历史事实/产业事实,都应能指回一个 C 编号。
   写稿时在草稿里标注 [C017],构建前删除标注(或保留在 HTML 注释里)。
3. **禁止派生层新增事实。** 写页面时"顺手"补的数字、年份、系数,一律先回 dossier 立案。
4. 置信 medium/low 的 Claim:页面措辞必须弱化("据报道/近似/一种说法"),
   或直接不进正文。
5. Type=numeric 的 Claim 必须附验证记录(见 math-policy 的验证清单),
   数值 sanity 不过的例子不得进 Lecture。
6. 历史性 Claim(谁、哪年、在哪):至少一个 Tier A/B 来源;年份写错 = 严重事故。
