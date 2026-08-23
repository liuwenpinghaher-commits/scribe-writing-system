let meta = #{
    name: "tonglu-mentor-extract",
    description: "从乱世铜炉全文多轮抽出写作参照：切章、分批章卡、五面透镜、合成、缺口再抽",
    when_to_use: "要把乱世铜炉拆成以后写书能翻的参照，一次抽不完就换 pass/start 再跑",
    phases: [
        #{ title: "Index", detail: "切章索引" },
        #{ title: "Chapter-cards", detail: "分批章卡" },
        #{ title: "Lenses", detail: "五面透镜" },
        #{ title: "Synthesize", detail: "合成参照本" },
        #{ title: "Gaps", detail: "缺口补抽" },
    ],
};

let index_schema = #{
    "type": "object",
    "required": ["ok", "chapter_count", "index_path"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "chapter_count": #{ "type": "integer" },
        "index_path": #{ "type": "string" },
        "first_title": #{ "type": "string" },
        "last_title": #{ "type": "string" },
        "titles": #{
            "type": "array",
            "maxItems": 40,
            "items": #{ "type": "string" },
        },
    },
};

let card_schema = #{
    "type": "object",
    "required": ["ok", "path", "title"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "path": #{ "type": "string" },
        "title": #{ "type": "string" },
        "turned": #{ "type": "boolean" },
        "place": #{ "type": "string" },
    },
};

let lens_schema = #{
    "type": "object",
    "required": ["ok", "path", "lens"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "path": #{ "type": "string" },
        "lens": #{ "type": "string" },
        "evidence_n": #{ "type": "integer" },
    },
};

let synth_schema = #{
    "type": "object",
    "required": ["ok", "path"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "path": #{ "type": "string" },
        "gap_count": #{ "type": "integer" },
        "can_stop": #{ "type": "boolean" },
    },
};

fn as_str(x) {
    if type_of(x) == "string" { x } else { "" }
}

fn as_int(x, fallback) {
    if type_of(x) == "int" { x } else { fallback }
}

let source = "/home/admin/projects/scribe-writing-system/docs/worlds/乱世铜炉-全文.md";
let out_dir = "/home/admin/projects/scribe-writing-system/docs/worlds/乱世铜炉-拆文";
let prompts = out_dir + "/PROMPTS.md";
let pass = "index";
let start = 0;
let count = 8;
if args != () {
    if args.source != () { source = as_str(args.source); }
    if args.out_dir != () { out_dir = as_str(args.out_dir); }
    if args.pass != () { pass = as_str(args.pass); }
    if args.start != () { start = as_int(args.start, 0); }
    if args.count != () { count = as_int(args.count, 8); }
}
if count < 1 { count = 1; }
if count > 8 { count = 8; }
if source == "" { pause("verification", "Pass args.source — 乱世铜炉全文路径。"); }

let do_index = pass == "index" || pass == "all";
let do_cards = pass == "chapters" || pass == "all";
let do_lenses = pass == "lenses" || pass == "all";
let do_synth = pass == "synthesize" || pass == "all";
let do_gaps = pass == "gaps" || pass == "all";
if !do_index && !do_cards && !do_lenses && !do_synth && !do_gaps {
    pause("verification", "Pass args.pass = index | chapters | lenses | synthesize | gaps | all");
}

let index_path = out_dir + "/00-index.md";
let chapter_count = 0;
let titles = [];

if do_index {
    phase("Index");
    let ip = "";
    ip += "你在给以后写书做参照的切章索引。必须用 read_file 和 grep 打开原文，禁止凭记忆。\n";
    ip += "原文路径： " + source + "\n";
    ip += "先完整读文件 " + prompts + " 里「第 0 轮 · 切章索引」一节，严格按那节做。\n";
    ip += "把 Markdown 表写到 " + index_path + "（列：序号、标题、起始行、结束行、大约字数）。引子序号 0。\n";
    ip += "同一章的上/中/下/补各算一节。正文里有人提到第几章的不要当成章题。\n";
    ip += "返回 chapter_count、index_path、first_title、last_title，以及 titles 前 40 个标题（超了也只返回 40，并在文件里写全）。\n";
    ip += "ok=true 仅当你已经用工具读过原文并写了索引文件。\n";
    let ir = agent(ip, #{
        label: "index",
        capability_mode: "read-write",
        output_schema: index_schema,
    });
    if ir == () || !ir.success || ir.output == () || ir.output.ok != true {
        complete(#{ summary: "切章索引没做成", pass: pass, ok: false });
    }
    chapter_count = as_int(ir.output.chapter_count, 0);
    index_path = as_str(ir.output.index_path);
    if ir.output.titles != () { titles = ir.output.titles; }
    log("index sections=" + chapter_count.to_string());
}

if do_cards {
    phase("Chapter-cards");
    if titles.len() == 0 {
        let rp = "";
        rp += "读 " + index_path + " 。用 read_file，不要凭记忆。\n";
        rp += "返回 chapter_count，以及从序号 " + start.to_string() + " 起最多 " + count.to_string() + " 个标题，放进 titles。\n";
        rp += "index_path 仍填 " + index_path + "。ok=true 仅当读到了表。\n";
        let rr = agent(rp, #{
            label: "reload-index",
            capability_mode: "read-only",
            output_schema: index_schema,
        });
        if rr != () && rr.success && rr.output != () && rr.output.titles != () {
            titles = rr.output.titles;
            chapter_count = as_int(rr.output.chapter_count, titles.len());
        }
    }
    if titles.len() == 0 {
        complete(#{ summary: "没有章题可做卡，先跑 pass=index", pass: pass, ok: false });
    }
    let jobs = [];
    let n = titles.len();
    if n > count { n = count; }
    log("chapter-cards batch start=" + start.to_string() + " n=" + n.to_string());
    let i = 0;
    while i < n {
        let title = as_str(titles[i]);
        let seq = start + i;
        let outp = out_dir + "/章卡/" + seq.to_string() + ".md";
        let cp = "";
        cp += "你在给以后写书做一节章卡。必须用 read_file 读原文，禁止凭记忆、禁止编地理和人物。\n";
        cp += "先读 " + prompts + " 里「第 1 轮 · 章卡」一节，严格按那节的项写。\n";
        cp += "原文：" + source + "\n索引：" + index_path + "\n";
        cp += "这一节序号 " + seq.to_string() + " ，标题：" + title + "\n";
        cp += "按索引起止行去读这一节，不要读全书。写到 " + outp + "\n";
        cp += "ok=true 仅当文件已写且每条都有书证或写明正文未写到。path 填写入路径，title 填章题。turned=这场戏有没有翻。place=主要地点。\n";
        jobs.push(#{
            prompt: cp,
            label: "card-" + seq.to_string(),
            capability_mode: "read-write",
            output_schema: card_schema,
        });
        i += 1;
    }
    let cards = parallel(jobs);
    let ok_n = 0;
    for c in cards {
        if c != () && c.success && c.output != () && c.output.ok == true { ok_n += 1; }
    }
    log("cards ok=" + ok_n.to_string() + "/" + n.to_string());
}

if do_lenses {
    phase("Lenses");
    let lenses = [
        "2A 世界有多大|透镜-世界.md|世界",
        "2B 群像与钱路|透镜-群像.md|群像",
        "2C 人怎么被看见|透镜-出场.md|出场",
        "2D 话与说书|透镜-说书.md|说书",
        "2E 戏怎么翻、热怎么切、章与章怎么换花样|透镜-节奏.md|节奏",
    ];
    let ljobs = [];
    for spec in lenses {
        let lp = "";
        lp += "你在给以后写书抽一面透镜。必须用 read_file 再读原文抽样，至少五处书证，不能只靠章卡脑补。\n";
        lp += "先读 " + prompts + " ，只做其中这一面：" + spec + "\n";
        lp += "原文：" + source + "\n章卡目录：" + out_dir + "/章卡/\n索引：" + index_path + "\n";
        lp += "把这一面写到 " + out_dir + "/ 下，文件名按提示指定。\n";
        lp += "ok=true 仅当文件已写且书证来自原文。lens 填这一面短名。evidence_n 填书证条数。path 填写入路径。\n";
        ljobs.push(#{
            prompt: lp,
            label: "lens-" + spec.sub_string(0, 2),
            capability_mode: "read-write",
            output_schema: lens_schema,
        });
    }
    let lres = parallel(ljobs);
    let lok = 0;
    for x in lres {
        if x != () && x.success && x.output != () && x.output.ok == true { lok += 1; }
    }
    log("lenses ok=" + lok.to_string() + "/5");
}

if do_synth {
    phase("Synthesize");
    let sp = "";
    sp += "合成参照本。只准用已经落盘的章卡和透镜，缺的写「这一轮还没抽到」。\n";
    sp += "先读 " + prompts + " 里「第 3 轮 · 合成参照本」。\n";
    sp += "目录：" + out_dir + "\n写到 " + out_dir + "/参照本.md\n";
    sp += "ok=true 仅当参照本已写。path 填该路径。\n";
    let sr = agent(sp, #{
        label: "synthesize",
        capability_mode: "read-write",
        output_schema: synth_schema,
    });
    if sr == () || !sr.success || sr.output == () || sr.output.ok != true {
        log("synthesize failed");
    }
}

if do_gaps {
    phase("Gaps");
    let gp = "";
    gp += "对照参照本和章卡找缺口。先读 " + prompts + " 里「第 4 轮 · 缺口补抽」。\n";
    gp += "目录：" + out_dir + "\n写到 " + out_dir + "/缺口.md\n";
    gp += "没有新缺口则 can_stop=true、gap_count=0。ok=true 仅当缺口文件已写。\n";
    let gr = agent(gp, #{
        label: "gaps",
        capability_mode: "read-write",
        output_schema: synth_schema,
    });
    if gr != () && gr.success && gr.output != () {
        complete(#{
            summary: "本轮结束",
            pass: pass,
            ok: true,
            can_stop: gr.output.can_stop,
            gap_count: gr.output.gap_count,
            out_dir: out_dir,
        });
    }
}

complete(#{
    summary: "本轮结束 pass=" + pass,
    pass: pass,
    ok: true,
    chapter_count: chapter_count,
    out_dir: out_dir,
});
