# Automation Blueprints
Automation Blueprints are ready-to-run automations. Pick one, fill in a couple of fields, and Hermes schedules it as a cron job — no cron syntax required.
Every blueprint works from **every surface** :
  * **Dashboard / desktop app** — open the Cron page, switch to the **Blueprints** tab, fill the form, and click _Schedule it_.
  * **CLI, TUI, and messengers** — type `/blueprint <name>` (e.g. `/blueprint morning-brief`) and Hermes asks you for what it needs, one question at a time, then schedules it. The name match is forgiving — a prefix or near-spelling resolves. Power users can skip the questions by passing values inline: `/blueprint morning-brief time=08:00`.
  * **Desktop app** — click **Send to App** on any blueprint and it opens with the command pre-loaded in your composer.

Blueprints never schedule anything silently — you always confirm before the job is created. Manage created jobs anytime with `/cron`.
### Morning briefing
daily at 08:00
A short daily briefing: today's calendar, weather, and anything urgent waiting on you.
dailybriefing
`/blueprint morning-brief time=08:00 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/morning-brief?time=08%3A00&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Important-mail monitor
every 30 minutes
Check your inbox periodically and ping you ONLY about mail that actually needs attention.
emailmonitor
`/blueprint important-mail interval_min=30 criteria="needs a reply today, is from my manager or family, or mentions a deadline" deliver=origin`Copy
[Send to App ↗](hermes://blueprint/important-mail?interval_min=30&criteria=needs+a+reply+today%2C+is+from+my+manager+or+family%2C+or+mentions+a+deadline&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Weekly review
sunday at 18:00
A weekly recap: what got done, what's still open, and what's coming up.
weeklyreview
`/blueprint weekly-review time=18:00 day=sunday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/weekly-review?time=18%3A00&day=sunday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Workday start reminder
weekdays at 09:00
A weekday nudge with your agenda and top priorities.
dailyfocus
`/blueprint workday-start time=09:00 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/workday-start?time=09%3A00&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Custom reminder
everyday at 14:00
A recurring reminder in your own words, on your schedule.
reminder
`/blueprint custom-reminder what="take a break and stretch" time=14:00 recurrence=everyday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/custom-reminder?what=take+a+break+and+stretch&time=14%3A00&recurrence=everyday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Evening wind-down
daily at 21:00
An end-of-day check-in: tomorrow's calendar at a glance and anything you should prep tonight.
dailyevening
`/blueprint evening-winddown time=21:00 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/evening-winddown?time=21%3A00&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Topic news digest
weekdays at 18:00
A recurring digest on a topic you care about — deduped against what was already sent, so only genuinely new items land.
digestresearch
`/blueprint news-digest topic="AI and technology" time=18:00 recurrence=weekdays count=5 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/news-digest?topic=AI+and+technology&time=18%3A00&recurrence=weekdays&count=5&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Bills & renewals reminder
everyday at 10:00
A heads-up before a recurring payment, subscription renewal, or due date — so nothing auto-charges by surprise.
reminderfinance
`/blueprint bill-renewal-watch what="my streaming subscription renews soon" time=10:00 recurrence=everyday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/bill-renewal-watch?what=my+streaming+subscription+renews+soon&time=10%3A00&recurrence=everyday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Habit check-in
everyday at 20:00
A recurring nudge to keep a habit on track and reflect on whether you did it.
habitwellbeing
`/blueprint habit-checkin habit="20 minutes of reading" time=20:00 recurrence=everyday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/habit-checkin?habit=20+minutes+of+reading&time=20%3A00&recurrence=everyday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Hydration & movement nudge
weekdays, every hour
A periodic nudge during the day to drink water, stand up, and stretch.
wellbeingfocus
`/blueprint hydration-move interval_hours=1 start_hour=9 end_hour=17 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/hydration-move?interval_hours=1&start_hour=9&end_hour=17&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Weekly meal plan
sunday at 17:00
A weekly meal plan plus a consolidated grocery list, tuned to your diet and how much time you have to cook.
weeklyfood
`/blueprint meal-plan diet="no restrictions" meals="dinner only" effort=quick time=17:00 day=sunday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/meal-plan?diet=no+restrictions&meals=dinner+only&effort=quick&time=17%3A00&day=sunday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Daily learning drip
weekdays at 08:30
One bite-sized lesson a day on a topic you want to learn, building progressively over time.
learningdaily
`/blueprint learn-daily topic="Spanish vocabulary" time=08:30 recurrence=weekdays deliver=origin`Copy
[Send to App ↗](hermes://blueprint/learn-daily?topic=Spanish+vocabulary&time=08%3A30&recurrence=weekdays&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### Gratitude & reflection prompt
everyday at 21:30
A gentle evening prompt to reflect on the day and note what went well.
wellbeingreflection
`/blueprint gratitude-journal time=21:30 recurrence=everyday deliver=origin`Copy
[Send to App ↗](hermes://blueprint/gratitude-journal?time=21%3A30&recurrence=everyday&deliver=origin)or paste the command into the CLI, TUI, or any messenger
### On-this-day discovery
daily at 07:30
A daily dose of curiosity: a notable historical event, fact, or word for the day.
dailycuriosity
`/blueprint on-this-day flavor="on this day in history" time=07:30 deliver=origin`Copy
[Send to App ↗](hermes://blueprint/on-this-day?flavor=on+this+day+in+history&time=07%3A30&deliver=origin)or paste the command into the CLI, TUI, or any messenger
## Writing your own[​](https://hermes-agent.nousresearch.com/docs/reference/automation-blueprints-catalog#writing-your-own "Direct link to Writing your own")
A blueprint is just a skill with a `metadata.hermes.blueprint` block in its `SKILL.md` frontmatter. See [Creating Skills → Automation Blueprints](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills) for the slot schema and how to publish one.
