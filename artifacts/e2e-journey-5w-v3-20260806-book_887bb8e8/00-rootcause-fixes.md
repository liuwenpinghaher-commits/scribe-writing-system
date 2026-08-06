# v3 根因修复

1. director._char_count 兼容 Store.characters() — 旅程不再永卡世界
2. loop max_tokens=8192 + draft 字数驱动
3. orch s3_patch/add_character 真落库 update_record
4. pilot full_check 仅 AI 味 heavy 不硬停（限知/退化仍硬拦）
5. draft_loop 强制重写：空串清 prose（非 NONE）；够长不重复清
6. 串行驱动 v2_serial_pilot.py：唯一证据路径，禁止 prose_pure 灌库
