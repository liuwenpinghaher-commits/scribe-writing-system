let meta = #{
    name: "tonglu-mentor-extract",
    description: "从乱世铜炉全文多轮抽出写作参照：切章校验、分批章卡、透镜串行、文风、合成、缺口",
    when_to_use: "要把乱世铜炉拆成以后写书能翻的参照，一次抽不完就换 pass/start/lens 再跑",
    phases: [
        #{ title: "Index", detail: "切章索引加校验" },
        #{ title: "Chapter-cards", detail: "按序号分批章卡" },
        #{ title: "Lenses", detail: "透镜串行，一面一次" },
        #{ title: "Style", detail: "文风细读" },
        #{ title: "Synthesize", detail: "合成参照本" },
        #{ title: "Gaps", detail: "缺口" },
        #{ title: "Trace", detail: "硬事实对回原文" },
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
        "duplicate_blocks": #{ "type": "integer" },
        "thin_n": #{ "type": "integer" },
        "issues": #{ "type": "string" },
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
        "start_line": #{ "type": "integer" },
        "end_line": #{ "type": "integer" },
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
        "issues": #{ "type": "string" },
    },
};

fn as_str(x) {
    if type_of(x) == "string" { x } else { "" }
}

fn as_int(x, fallback) {
    if type_of(x) == "int" { x } else { fallback }
}

fn agent_ok(r) {
    r != () && r.success && r.output != () && r.output.ok == true
}

fn iron_prefix(source, prompts, out_dir) {
    let p = "";
    p += "你在给以后写别的书抽作法，不是写读后感，不是给这本做情节缩写。\n";
    p += "必须用工具：read_file、grep。禁止凭记忆。禁止把全文一次性读进对话，也禁止按页把三万多行翻完。切章用 grep 章题；章卡和透镜按索引行号只读那一节。\n";
    p += "原文路径：";
    p += source;
    p += "\n提示文件：";
    p += prompts;
    p += "\n产出目录：";
    p += out_dir;
    p += "\n没在正文里发生的事，写「正文未写到」。不许补地名人名官职钱数路程。\n";
    p += "每一条能指到场面：标题 + 行号 + 不超过四十字的原句。指不出就删。\n";
    p += "只换词、堆词、点名一个世界词就能交差的句子，删掉重写。\n";
    p += "禁止主题升华、字数配额、机制词清单、把人写成职能标签、用至少N个当写好。\n";
    p += "打开书先问自己：这一节是谁的日子、发生哪一件、读完世界怎么变。问不清就再读，不要开始写。\n";
    p
}

fn lens_file(name) {
    if name == "世界" { "透镜-世界.md" }
    else if name == "群像" { "透镜-群像.md" }
    else if name == "出场" { "透镜-出场.md" }
    else if name == "说书" { "透镜-说书.md" }
    else if name == "节奏" { "透镜-节奏.md" }
    else if name == "伏笔" { "透镜-伏笔.md" }
    else if name == "人物" { "透镜-人物.md" }
    else if name == "线索" { "透镜-线索.md" }
    else if name == "开篇" { "透镜-开篇.md" }
    else { "" }
}

fn lens_heading(name) {
    if name == "世界" { "2A 世界有多大" }
    else if name == "群像" { "2B 群像与钱路" }
    else if name == "出场" { "2C 人怎么被看见" }
    else if name == "说书" { "2D 话与说书" }
    else if name == "节奏" { "2E 戏怎么翻、热怎么切、章与章怎么换花样" }
    else if name == "伏笔" { "2F 伏笔怎么埋怎么收" }
    else if name == "人物" { "2G 人整本书怎么变" }
    else if name == "线索" { "2H 主线、旁人的日子、暗账" }
    else if name == "开篇" { "2I 前几节凭什么让人接着看" }
    else { "" }
}

let source = "/home/admin/projects/scribe-writing-system/docs/worlds/乱世铜炉-全文.md";
let out_dir = "/home/admin/projects/scribe-writing-system/docs/worlds/乱世铜炉-拆文";
let prompts = out_dir + "/PROMPTS.md";
let pass = "index";
let start = 0;
let count = 4;
let force = 0;
let lens = "";
if args != () {
    if args.source != () { source = as_str(args.source); }
    if args.out_dir != () { out_dir = as_str(args.out_dir); }
    if args.pass != () { pass = as_str(args.pass); }
    if args.start != () { start = as_int(args.start, 0); }
    if args.count != () { count = as_int(args.count, 4); }
    if args.force != () { force = as_int(args.force, 0); }
    if args.lens != () { lens = as_str(args.lens); }
}
if count < 1 { count = 1; }
if count > 8 {
    log("count cap 8, was " + count.to_string());
    count = 8;
}
if source == "" { pause("verification", "Pass args.source — 乱世铜炉全文路径。"); }

let do_index = pass == "index" || pass == "all";
let do_cards = pass == "chapters" || pass == "all";
let do_lenses = pass == "lenses";
let do_style = pass == "style";
let do_synth = pass == "synthesize";
let do_gaps = pass == "gaps";
let do_trace = pass == "trace";
if !do_index && !do_cards && !do_lenses && !do_style && !do_synth && !do_gaps && !do_trace {
    pause("verification", "Pass args.pass = index | chapters | lenses | style | synthesize | gaps | trace | all");
}

let index_path = out_dir + "/00-index.md";
let chapter_count = 0;
let failed_seqs = [];
let cards_ok = 0;
let cards_n = 0;
let dup_n = 0;

if do_index {
    phase("Index");
    let ip = iron_prefix(source, prompts, out_dir);
    ip += "先完整读提示文件里「第 0 轮 · 切章索引」一节，严格按那节做。文件缺失也按下面做。\n";
    ip += "把 Markdown 表写到 ";
    ip += index_path;
    ip += "\nforce=";
    ip += force.to_string();
    ip += " 。force 不是 1 且索引已合格则不要覆盖，仍返回 chapter_count。\n";
    ip += "切章只用 grep 找章题，read_file 只抽标题前后两三行。禁止通读全文，禁止读节身。\n";
    ip += "正传第四十三章是心机（约 L18769）。回绕里第四十三章选择是前传重贴。空壳仍占序号。免费外篇单独成节。\n";
    ip += "ok=true 仅当你已经用 grep 找到章题并写了索引（或合格跳过）。chapter_count=正表节数。\n";
    let ir = agent(ip, #{
        label: "index",
        capability_mode: "read-write",
        output_schema: index_schema,
    });
    if !agent_ok(ir) {
        complete(#{ summary: "切章索引没做成", pass: pass, ok: false });
    }
    chapter_count = as_int(ir.output.chapter_count, 0);
    if ir.output.index_path != () {
        let ipath = as_str(ir.output.index_path);
        if ipath != "" { index_path = ipath; }
    }
    let sp = iron_prefix(source, prompts, out_dir);
    sp += "你在找切章错误。先完整读提示文件里「同轮 · 索引校验」。\n";
    sp += "读已经落盘的 ";
    sp += index_path;
    sp += "\n用 grep 抽查原文标题行。禁止通读全文，禁止读节身。\n";
    sp += "chapter_count 必须是你交卷时正表的节数。duplicate_blocks=疑似重贴块数。\n";
    let sr = agent(sp, #{
        label: "index-skeptic",
        capability_mode: "read-write",
        output_schema: index_schema,
    });
    if !agent_ok(sr) {
        complete(#{ summary: "切章校验没做成", pass: pass, ok: false, index_path: index_path });
    }
    chapter_count = as_int(sr.output.chapter_count, chapter_count);
    dup_n = as_int(sr.output.duplicate_blocks, 0);
    log("index sections=" + chapter_count.to_string() + " dups=" + dup_n.to_string());
    if dup_n > 0 {
        await_user("user", "索引标了重贴。看 00-index.md 三句说明。继续抽卡请 resume，要重切请改完再跑 pass=index force=1");
    }
}

if do_cards {
    phase("Chapter-cards");
    if chapter_count < 1 {
        let rp = iron_prefix(source, prompts, out_dir);
        rp += "读 ";
        rp += index_path;
        rp += " 。用 read_file，不要凭记忆。\n";
        rp += "返回 chapter_count=正表节数。不要返回 titles 清单。index_path 仍填该路径。ok=true 仅当读到了表。\n";
        let rr = agent(rp, #{
            label: "reload-index",
            capability_mode: "read-only",
            output_schema: index_schema,
        });
        if agent_ok(rr) {
            chapter_count = as_int(rr.output.chapter_count, 0);
            if rr.output.index_path != () {
                let ipath2 = as_str(rr.output.index_path);
                if ipath2 != "" { index_path = ipath2; }
            }
        }
    }
    if chapter_count < 1 {
        complete(#{ summary: "没有章题可做卡，先跑 pass=index", pass: pass, ok: false });
    }
    let n = count;
    let remain_after_start = chapter_count - start;
    if remain_after_start < 1 {
        complete(#{
            summary: "start 已超过正表节数",
            pass: pass,
            ok: false,
            start: start,
            chapter_count: chapter_count,
        });
    }
    if n > remain_after_start { n = remain_after_start; }
    let remain = n;
    let b = budget();
    if b != () && b.remaining != () {
        remain = as_int(b.remaining, n);
    }
    if remain < 1 {
        complete(#{ summary: "预算不够抽卡", pass: pass, ok: false, chapter_count: chapter_count });
    }
    if n > remain {
        log("budget cut cards " + n.to_string() + " -> " + remain.to_string());
        n = remain;
    }
    if n < 1 {
        complete(#{ summary: "本批卡数为 0，不发空面板", pass: pass, ok: false });
    }
    log("chapter-cards batch start=" + start.to_string() + " n=" + n.to_string() + " of " + chapter_count.to_string());
    let jobs = [];
    let i = 0;
    while i < n {
        let seq = start + i;
        let outp = out_dir + "/章卡/" + seq.to_string() + ".md";
        let cp = iron_prefix(source, prompts, out_dir);
        cp += "先读提示文件里「第 1 轮 · 章卡」，严格按那节的项写。\n";
        cp += "索引：";
        cp += index_path;
        cp += "\n你只做序号 ";
        cp += seq.to_string();
        cp += " 的那一节。先读索引找到标题和起止行，再按行号只读这一节。不要读全书。\n写到 ";
        cp += outp;
        cp += "\nforce=";
        cp += force.to_string();
        cp += "\nok=true 仅当文件已写（或合格跳过）且你按索引起止行读过这一节。path 填写入路径，title 填章题。turned=这场戏有没有翻。place=主要地点。\n";
        jobs.push(#{
            prompt: cp,
            label: "card-" + seq.to_string(),
            capability_mode: "read-write",
            output_schema: card_schema,
        });
        i += 1;
    }
    if jobs.len() < 1 {
        complete(#{ summary: "本批卡数为 0，不发空面板", pass: pass, ok: false });
    }
    let cards = parallel(jobs);
    let ci = 0;
    for c in cards {
        let seqc = start + ci;
        if c != () && c.success && c.output != () && c.output.ok == true {
            cards_ok += 1;
        } else {
            failed_seqs.push(seqc);
        }
        ci += 1;
    }
    cards_n = n;
    log("cards ok=" + cards_ok.to_string() + "/" + n.to_string());
}

if do_lenses {
    phase("Lenses");
    let all_lenses = ["世界", "群像", "出场", "说书", "节奏", "伏笔", "人物", "线索", "开篇"];
    let wanted = [];
    if lens == "" {
        for nm in all_lenses { wanted.push(nm); }
    } else {
        let found = false;
        for nm in all_lenses {
            if lens == nm {
                found = true;
                wanted.push(nm);
            }
        }
        if !found {
            pause("verification", "args.lens 只能是 世界 / 群像 / 出场 / 说书 / 节奏 / 伏笔 / 人物 / 线索 / 开篇。空=本轮串行做完全部。");
        }
    }
    if wanted.len() < 1 {
        complete(#{ summary: "没有要跑的透镜，不发空面板", pass: pass, ok: false });
    }
    let lok = 0;
    for nm in wanted {
        let fname = lens_file(nm);
        let head = lens_heading(nm);
        let outp = out_dir + "/" + fname;
        let lp = iron_prefix(source, prompts, out_dir);
        lp += "你只做这一面透镜：";
        lp += head;
        lp += "（短名 ";
        lp += nm;
        lp += "）。先读提示文件里这一面的全文，严格按那面问的戏写。\n";
        lp += "索引：";
        lp += index_path;
        lp += "\n章卡目录：";
        lp += out_dir;
        lp += "/章卡/\n必须再读原文抽样，不能只靠章卡。禁止通读全文。\n写到 ";
        lp += outp;
        lp += "\nforce=";
        lp += force.to_string();
        lp += "\nok=true 仅当文件已写且书证来自原文。lens 填短名。evidence_n 填书证条数。path 填写入路径。\n";
        let lr = agent(lp, #{
            label: "lens-" + nm,
            capability_mode: "read-write",
            output_schema: lens_schema,
        });
        if agent_ok(lr) {
            lok += 1;
            log("lens=" + nm + " ok");
        } else {
            log("lens=" + nm + " failed");
        }
    }
    complete(#{
        summary: "透镜本轮结束",
        pass: pass,
        ok: lok > 0,
        lenses_ok: lok,
        lenses_n: wanted.len(),
        out_dir: out_dir,
    });
}

if do_style {
    phase("Style");
    let outp = out_dir + "/透镜-文风.md";
    let stp = iron_prefix(source, prompts, out_dir);
    stp += "先读提示文件里「第 2J 轮 · 文风细读」，严格按那节做。\n";
    stp += "索引：";
    stp += index_path;
    stp += "\n写到 ";
    stp += outp;
    stp += "\nforce=";
    stp += force.to_string();
    stp += "\nok=true 仅当文件已写且你按索引抽样读过原文。lens=文风。path 填写入路径。\n";
    let str = agent(stp, #{
        label: "style",
        capability_mode: "read-write",
        output_schema: lens_schema,
    });
    if !agent_ok(str) {
        complete(#{ summary: "文风没做成", pass: pass, ok: false });
    }
    complete(#{ summary: "文风已写", pass: pass, ok: true, path: outp, out_dir: out_dir });
}

if do_synth {
    phase("Synthesize");
    let outp = out_dir + "/参照本.md";
    let syp = iron_prefix(source, prompts, out_dir);
    syp += "先读提示文件里「第 3 轮 · 合成参照本」。只准用已经落盘的章卡和透镜，缺的写「这一轮还没抽到」。\n";
    syp += "目录：";
    syp += out_dir;
    syp += "\n写到 ";
    syp += outp;
    syp += "\nok=true 仅当参照本已写。path 填该路径。can_stop=false。\n";
    let syr = agent(syp, #{
        label: "synthesize",
        capability_mode: "read-write",
        output_schema: synth_schema,
    });
    if !agent_ok(syr) {
        complete(#{ summary: "参照本没做成", pass: pass, ok: false });
    }
    complete(#{ summary: "参照本已写", pass: pass, ok: true, path: outp, out_dir: out_dir });
}

if do_gaps {
    phase("Gaps");
    let outp = out_dir + "/缺口.md";
    let gp = iron_prefix(source, prompts, out_dir);
    gp += "先读提示文件里「第 4 轮 · 缺口」。本轮独占写缺口文件。\n";
    gp += "目录：";
    gp += out_dir;
    gp += "\n写到 ";
    gp += outp;
    gp += "\n没有新缺口且文末约四张卡已在则 can_stop=true、gap_count=0。ok=true 仅当缺口文件已写。\n";
    let gr = agent(gp, #{
        label: "gaps",
        capability_mode: "read-write",
        output_schema: synth_schema,
    });
    if !agent_ok(gr) {
        complete(#{ summary: "缺口没做成", pass: pass, ok: false });
    }
    complete(#{
        summary: "缺口已写",
        pass: pass,
        ok: true,
        path: outp,
        can_stop: gr.output.can_stop,
        gap_count: gr.output.gap_count,
        out_dir: out_dir,
    });
}

if do_trace {
    phase("Trace");
    let outp = out_dir + "/参照本.md";
    let tp = iron_prefix(source, prompts, out_dir);
    tp += "先读提示文件里「第 5 轮 · 硬事实回溯」。只改参照本，不要写缺口文件。\n";
    tp += "参照本：";
    tp += outp;
    tp += "\n原文：";
    tp += source;
    tp += "\nok=true 仅当你对抽出的硬说法做过 grep。path 填参照本路径。\n";
    let tr = agent(tp, #{
        label: "trace",
        capability_mode: "read-write",
        output_schema: synth_schema,
    });
    if !agent_ok(tr) {
        complete(#{ summary: "回溯没做成", pass: pass, ok: false });
    }
    complete(#{
        summary: "硬事实已对回原文",
        pass: pass,
        ok: true,
        path: outp,
        gap_count: tr.output.gap_count,
        out_dir: out_dir,
    });
}

let next_start = start + cards_n;
let overall_ok = true;
if do_cards { overall_ok = cards_ok > 0; }
complete(#{
    summary: "本轮结束",
    pass: pass,
    ok: overall_ok,
    chapter_count: chapter_count,
    cards_ok: cards_ok,
    cards_n: cards_n,
    next_start: next_start,
    failed_seqs: failed_seqs,
    duplicate_blocks: dup_n,
    index_path: index_path,
    out_dir: out_dir,
});
