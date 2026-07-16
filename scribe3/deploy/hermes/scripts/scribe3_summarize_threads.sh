#!/bin/bash
# P2 夜间摘要兜底:对每本书跑线程摘要压缩(幂等,阈值内秒过)。
# --no-agent 哨兵:空 stdout=静默成功;只有失败才输出(hermes 送达提醒)。
set -u
B="${SCRIBE3_API:-http://127.0.0.1:3321}"
fails=""
works=$(curl -sf --max-time 20 "$B/works" | python3 -c "import sys,json;print(' '.join(w['slug'] for w in json.load(sys.stdin)))" 2>/dev/null) || works=""
for w in main $works; do
  r=$(curl -sf --max-time 300 -X POST "$B/maintenance/summarize-threads?work=$w") || { fails="$fails $w:curl失败"; continue; }
  errs=$(echo "$r" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d.get('errors') or {}))" 2>/dev/null || echo "?")
  [ "$errs" != "0" ] && fails="$fails $w:${errs}个线程摘要失败"
done
[ -n "$fails" ] && echo "scribe3 夜间摘要兜底有失败:$fails(详见后端日志与线程 summary_error 红字)"
exit 0
