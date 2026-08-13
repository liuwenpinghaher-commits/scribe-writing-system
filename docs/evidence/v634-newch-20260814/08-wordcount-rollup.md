# 08-wordcount-rollup · 本轮新章 6–10

可见定稿（剥污染后去空白，`scribe3.prose_sanitize.visible_length`，正文来自 demo `GET /chapter` 全文）：

- 第6章 `第六章·清册入镇`：6687 字
- 第7章 `第七章·还鞘`：4342 字
- 第8章 `第八章·假账对质`：4397 字
- 第9章 `第九章·入芯破例`：3611 字
- 第10章 `第十章·揭炉夜`：3539 字

合计: 22576

用户门禁 ≥20000：PASS
本轮**只计新章 6–10**，不含已洗尾的 1–5 章。
五章 `GET /api/chapter` prose 均无 `fallback`。
来源：demo `book_79c0d45e` GET chapter seq=6..10 全文（非摘录）
