-- SL1 · migration 132: storyline.craft_only — only true notes enter write inject
-- Missing field reads as true (compat); new creates default true.
DEFINE FIELD IF NOT EXISTS craft_only ON storyline TYPE option<bool>;
