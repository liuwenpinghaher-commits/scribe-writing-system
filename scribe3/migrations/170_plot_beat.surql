-- scribe3 · 170_plot_beat.surql · 章级剧情标注（视角已有 focalizer，补动作类型）
--
-- P2「手段不得单一」要落成字段才能卷末核。不设比例闸：只问本卷是否全是同一类。
-- 值是八个字之一：买 / 换 / 骗 / 抢 / 拖 / 揭发 / 结盟 / 背叛。空 = 未标。

DEFINE FIELD IF NOT EXISTS plot_action ON chapter TYPE option<string>;
