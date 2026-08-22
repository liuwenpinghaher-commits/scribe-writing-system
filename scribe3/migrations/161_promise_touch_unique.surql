-- PRM-02: 同章同 ingest 不得重复记伏笔触碰。
DEFINE INDEX IF NOT EXISTS uniq_promise_touch_ingest
    ON promise_touch FIELDS promise_id, chapter, ingest_seq UNIQUE;
