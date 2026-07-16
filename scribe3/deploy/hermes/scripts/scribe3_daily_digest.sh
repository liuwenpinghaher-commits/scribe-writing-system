#!/bin/bash
# P2 每日创作摘报:逐书生成摘报(写 chief_digest,决策收件箱消费)。
# --no-agent 哨兵:空 stdout=静默成功;失败才输出(hermes 送达提醒)。
set -u
B="${SCRIBE3_API:-http://127.0.0.1:3321}"
fails=""
works=$(curl -sf --max-time 20 "$B/works" | python3 -c "import sys,json;print(' '.join(w['slug'] for w in json.load(sys.stdin)))" 2>/dev/null) || works=""
for w in main $works; do
  r=$(curl -sf --max-time 120 -X POST "$B/maintenance/daily-digest?work=$w") || { fails="$fails $w:curl失败"; continue; }
  e=$(echo "$r" | python3 -c "import sys,json;print(json.load(sys.stdin).get('error') or '')" 2>/dev/null)
  [ -n "$e" ] && fails="$fails $w:$e"
done
[ -n "$fails" ] && echo "scribe3 每日摘报有失败源:$fails(摘报已产出,缺项在收件箱红字)"
exit 0
