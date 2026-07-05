-- scribe3 · 054_arc_anchor.surql · 角色弧光:静态锚(Weiland 五要素)+ 里程碑表 + lie_belief 标量
DEFINE FIELD IF NOT EXISTS ghost ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS lie ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS truth ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS want ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS need ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS arc_type ON character TYPE option<string>;
DEFINE FIELD IF NOT EXISTS private_agenda ON character TYPE option<string>;
DEFINE TABLE IF NOT EXISTS arc_plan SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS character_id ON arc_plan TYPE string;
DEFINE FIELD IF NOT EXISTS beat_name ON arc_plan TYPE string;
DEFINE FIELD IF NOT EXISTS target_chapter ON arc_plan TYPE int;
DEFINE FIELD IF NOT EXISTS lie_belief_target ON arc_plan TYPE option<int>;
DEFINE FIELD IF NOT EXISTS trigger_event ON arc_plan TYPE option<string>;
DEFINE FIELD IF NOT EXISTS lie_belief ON char_state TYPE option<int>;
-- 028 的 change_type ASSERT 白名单不含 'belief',lie_belief 位移记录以 change_type='belief' 落
-- char_state,须 OVERWRITE 扩白名单(仅加值,存量数据不受影响)
DEFINE FIELD OVERWRITE change_type ON char_state TYPE string
    ASSERT $value IN ['ability','relation','personality','composite','belief'];
