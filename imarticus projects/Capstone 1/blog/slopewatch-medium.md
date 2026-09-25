# Can We See a Himalayan Landslide Coming? I Built a System to Find Out.

### Slopewatch ranks slopes across the Indian Himalaya by daily landslide risk, using only public data. Here's how it works, what it achieves, and the bug I caught before it could fool anyone.

![Check 10% of slopes, reach 29% of landslides: nearly three times better than inspecting at random.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-cover.png)

Every monsoon the news from the hills looks the same. A slope in Uttarakhand gives way. A highway in Himachal disappears under mud. A village in the North East is cut off for days. And afterwards, someone always asks: *could we have seen it coming?*

That question is where this project started. The Smart India Hackathon 2026 has a problem statement on exactly this, PS 26192, *flash flood and landslide early warning*, and I wanted to see how far I could get with public data and honest engineering.

What I built is called **Slopewatch**. Every day it looks at recent rainfall and at the shape of the land, and ranks which slopes across the Indian Himalaya deserve a closer look.

The short version of the result: **if a district can check only one in ten slopes, Slopewatch points them to nearly three times as many real landslides as picking at random.** Getting there meant designing around a few traps that make a model look good for the wrong reasons, and this post walks through each one.

I've written it for two kinds of reader. If you've never trained a model, you can follow the whole thing; I explain every term when it shows up. If you do this for a living, look for the short **"For the technical readers"** notes. They carry the details.

---

## Rain pulls the trigger. The land decides where.

Before building anything, I wanted to see the problem with my own eyes. So I plotted which months landslides get reported in, state by state.

![Share of each state's landslides by month. Most follow the June–September monsoon. Kashmir, fed partly by winter storms and snowmelt, is the odd one out.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-seasonality.png)

Almost everything lines up behind the monsoon. That told me what the model would need: **rainfall** (what the sky has been doing) and **terrain** (which slopes can fail at all).

To turn the map into something a computer can work with, I laid a grid over the Himalayan arc and the North East: 40,800 squares, each about 11 km across. I kept the 22,594 squares that are actually hilly, and looked at ten years of days, 2007 to 2016.

For "what really happened", I used NASA's Global Landslide Catalog. It started with 11,033 records worldwide; filtering to my region and years left 1,719 landslides.

![How NASA's global catalogue narrows down to the 1,719 landslides this project learns from.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-06-catalogue-funnel-11-033-raw.png)

---

## The first trap: 99.998% accuracy

22,594 squares × 3,653 days is about **82 million square-days**. Only 1,719 of them had a landslide. That's roughly **one in 48,000**.

It's hard to feel how small that is, so here it is drawn out:

![Each dot is one square on one day. Exactly one of them had a landslide.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-one-in-48000.png)

Train a model naively on data like this and it finds the laziest rule possible: *always say "no landslide".* It's right 99.998% of the time.

And it's useless, because it never warns anyone about anything.

That's why the word "accuracy" doesn't appear anywhere in how I judge this system. When the thing you care about is this rare, accuracy rewards a model for ignoring it.

There was a practical wall, too. Checking 45 days of weather for all 82 million square-days, with a free weather service that allows about 10,000 requests a day, would have taken decades.

So I borrowed a trick from medicine. When doctors study a rare disease, they don't examine the whole population. They take every patient who has it (the **cases**) and compare them against a carefully chosen group who don't (the **controls**). I did the same: keep every landslide, add a designed set of "normal" days, and 82 million rows become **11,955**.

![Instead of 82 million rows: every landslide, plus a designed set of comparison days.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-01-a-full-space-time-panel.png)

> **For the technical readers:** this is case-control sampling. The sample is about 14% positive against a true rate near 0.002%, so every raw score is inflated by roughly four orders of magnitude. It's exactly recoverable with a log-odds prior correction at scoring time, but only if you remember to apply it.

---

## Picking the right "normal days"

This part took more thought than any model.

If you pick normal days at random, you mostly get flat land in the dry season. A model can separate those from monsoon landslides in the mountains very easily, by learning "mountain in July" versus "plain in January". That isn't predicting landslides; it's reading a calendar and a map.

So every normal day is chosen to remove one of those shortcuts:

![Three kinds of comparison day. Each one holds something constant so the model can't cheat with it.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-07-the-three-control-strata-temporal.png)

- **Same hillside, different day (half of them).** Same square, same time of year, a different date. *Why did this slope fail on this monsoon day, and not on hundreds of others?* The land is identical, so the answer has to be the weather.
- **Same day, different hillside (30%).** A square 25–300 km away on the same date. *The same storm hit both, so why did only one slope go?*
- **Any hillside, any day (20%).** A reminder of what an ordinary day looks like.

One more rule mattered just as much. NASA's catalogue only lists landslides that someone *reported*, and in remote valleys many never are. So any "normal day" within **15 km and two days** of a known landslide is thrown away rather than labelled "no". A slope that probably failed unseen shouldn't be taught to the model as a safe one.

![The exclusion zone: days near a reported landslide in place and time are dropped, never labelled safe.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-08-space-time-exclusion-buffer-around.png)

---

## The bug I caught before it shipped

This is the story I most want to tell.

After training, I asked the model the most useful question you can ask one: *what are you actually paying attention to?* (Engineers use a tool called SHAP for this. It scores how much each input pushed each prediction.)

The top answer was **elevation**, the average height of the square. And it wasn't close: elevation mattered **2.3 times** more than anything else.

I nearly moved on. Elevation *sounds* like a sensible landslide predictor. Higher ground is steeper, colder and more broken. Show that chart in a meeting and most people would nod.

What bothered me was how completely it dominated. Everything I'd read says Himalayan landslides are a rain story: weeks of rain soak a slope, then one heavy burst tips it. Rain should have been on top.

So I went digging, and found the cause two steps before the model ever ran.

To decide which squares count as "hilly", I used one simple rule: **average slope of at least 5 degrees**. That's reasonable; landslides need slopes, and they clearly get more common as the ground gets steeper:

![Landslides per 1,000 squares rise with slope, which is why a slope threshold looked like the obvious filter.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-slope_density.png)

Here's what I missed: **a high plateau can be steep too.** Ladakh and the Tibetan plateau are high, cold, dry, mostly outside the monsoon, and comfortably above 5 degrees. They sailed straight through my filter.

![The terrain step. The hill filter checks slope only, with no elevation term, so the plateau slips through.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-05-terrain-pipeline-each-dem-tile.png)

Real landslides, meanwhile, cluster in the middle heights:

![Where real landslides happen: mostly between 1,000 and 2,000 metres.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-elevation_bands.png)

Put those together. My random "normal day" squares came heavily from the plateau: **their median height was 4,479 m, against 1,433 m for real landslides.** That's a gap of more than three kilometres.

![Before the fix, comparison squares sat far higher than landslides. After matching by height band, the gap disappears.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-10-before-and-after-elevation-band.png)

The model wasn't learning why slopes fail. **It had learned to tell Tibet apart from a Himalayan valley.** Easy to learn, great-looking scores, and no use to anyone living under a hillside.

### The fix

The filter was fine; those plateau squares really are steep. The mistake was in how I picked the comparisons. Now each normal day is drawn from the **same height band** as the landslide it's compared with. The height gap went from **+3,046 m to −17 m**, and elevation dropped out of the top 15 inputs entirely.

Here's what the model pays attention to now:

![After the fix: rainfall leads, and terrain appears as roughness rather than height.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-shap.png)

Rain on the day comes first, then rain over the last three days, then how many wet days came before. Terrain shows up fourth, as *roughness*, not height. That's the story geologists tell.

And the part I still find remarkable: **I didn't touch the model.** Not one setting. I only changed who it was compared against, and it started answering a completely different question.

> **For the technical readers:** controls are matched to 500 m elevation bands (±1 band), and background draws anchor on a case cell first. A regression test builds a synthetic world with 4,500 m plateau cells and 1,400 m slope cells *interleaved in space*, so distance rules can't pass it by accident. Only band matching can. I deliberately don't report a before/after PR-AUC here: the two models saw different samples and different test splits, so the SHAP ranking is the only fair comparison.

---

## The score dropped, and the model got better

Later I had three times as much weather data. I retrained, expecting the score to go up. It went **down**, from 0.410 to 0.244.

That looks like a disaster, and it isn't. The score I use (**PR-AUC**) measures how well real landslides get ranked above normal days, and its "random guessing" baseline isn't zero. It equals the share of landslides in your data. As the data grew, that share fell, so the whole scale moved down with it.

![Same model, more data. The score fell along with its baseline, while every measure that ignores the baseline improved.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-01.png)

Measured against its own baseline, the model barely changed: 1.54× better than guessing before, 1.45× after. Meanwhile, everything that doesn't depend on the baseline improved. Its probabilities got more trustworthy, it caught **40% more landslides** at a realistic inspection budget, and it began doing slightly better on regions it had never seen.

If I'd written "score fell from 0.41 to 0.24 after adding data", every word would have been true and the message would have been false. So every score in this project now travels with its baseline and a confidence range.

---

## When two models tie, ask a better question

I tried three kinds of model: a simple classic one (logistic regression) and two tree-based ones (random forest and XGBoost).

![All three models on data they never saw. The dashed line is what random guessing would score.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-pr_curves.png)

![Side by side. The score ranges overlap almost completely; recall at a fixed budget does not.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-02.png)

On the headline score, random forest "wins" by 0.0035, but their ranges overlap almost entirely. That difference is noise.

So I asked what a district actually needs to know. They can't inspect every slope; they have a few teams. **If you can check only the top 5% of squares today, what share of the real landslides do you catch?**

![If you can inspect only a fixed share of squares, how many real landslides do you reach?](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-recall_at_budget.png)

Random forest catches 5.3%. XGBoost catches 13.0%, two and a half times as many. That's the one that shipped.

> **For the technical readers:** models whose PR-AUC confidence intervals overlap the leader's are treated as tied, and the tie breaks on recall at budget. That only counts if validation and test agree on the winner; otherwise it falls back to the PR-AUC leader. Tripling the data also pushed the tree models into memorising (train PR-AUC 0.99, validation 0.21). The capacity gate had been counting positives (941), when what matters is events per variable: 941 across 41 features is only about 23. The gate now uses EPV, and held-out scores improved.

---

## The boring problems that ate the most time

Not everything was statistics. The biggest time sink was simply downloading weather: 11,955 samples × 45 days of history, about 38,000 requests against a limit of roughly 10,000 a day. It's a job that runs for days and has to survive crashes.

**Lesson one: not every error deserves a retry.** My downloader retried every failure four times, then quit. That's right for "too many requests", because waiting fixes it. But one day it hit "bad request" (HTTP 400), retried pointlessly, and killed a run with 10,000 good downloads still to go.

The cause was, again, somewhere else entirely. The forecasting step had added a few upcoming dates to a shared date table. The sampler read that table with no end limit, picked "normal days" from those brand-new dates, and the weather archive, which runs about five days behind, rightly refused.

![One small change in one stage, a crash in another, and the two fixes it needed.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-17-causal-chain-stage-08-appends.png)

**Lesson two: don't let your saved files move.** An earlier version merged overlapping date ranges to save 21% of requests. But saved files were named by their dates, and the merged ranges shifted whenever the sample changed. After the elevation fix rebuilt the sample, **only 232 of 2,190 saved downloads were still usable.** Days of quota gone, because I'd optimised the wrong thing.

![Before: merged windows whose edges move when the sample changes. After: each window pinned to its own date.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-16-before-merged-windows-per-cell.png)

---

## "We need more data." Do we, though?

That's the easiest excuse in machine learning, so I tested it. I trained on growing slices of the data, from a quarter up to all of it, and watched how the score changed.

![The learning curve: big gains early, then almost flat.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-18-learning-curve-re-measured-at.png)

Going from a quarter of the data to all of it added **0.031**. The last step added almost nothing. The curve has flattened. More of the same data won't help much; *better* data will.

My favourite detail: I'd drawn this curve once before, on a third of the data, and predicted that tripling it would add between 0.02 and 0.04. It added 0.031. A method that correctly predicts its own future is one I'm willing to trust.

---

## What it looks like in use

All of this ends up in an app with six screens, built for two people. One is the **district officer** deciding where to send a team this morning. The other is the **field officer** standing on a broken road with one bar of signal.

The **risk map** draws every square at its real size rather than as a dot, because an 11 km square isn't one hillside and the map shouldn't pretend it is. Hover over one and you see its district, its real-world chance of failure, the main reason it's flagged, and what sits downhill. The **districts** view ranks where teams are needed, and **cell detail** explains a single square in plain language.

The **model** screen answers "how good is it?" before anyone has to ask, and puts the baseline right next to the headline score, so the number can never be read out of context:

![The Model screen in the running app: the headline score, its baseline, the lift over guessing, and recall at a 5% budget, with a plain-language note on how to read them.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/demo-model.png)

The **field report** screen is for the person standing on the road. They can log a crack, slope movement or a blocked road with no internet at all. It also says plainly that nothing uploads automatically yet. An early version promised the report "will sync when the network is available", and nothing did. For a safety tool, admitting you're a prototype beats overpromising.

![The Field report screen: a geo-tagged observation form that works offline, with an honest note that reports stay on the device for now.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/demo-field-report.png)

Behind the screens there's a proper data pipeline: four public data sources, twelve stages, and a MySQL warehouse.

![The architecture: four public data sources, a twelve-stage pipeline, a warehouse, and the app on top.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-02-architecture-four-external-sources-feed.png)

### One number, three questions

Different people ask different things of the same score, so the app answers three separate questions:

![From one model score to three answers: a real-world chance, an urgency band, and a priority list.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-14-scoring-flow-a-forecast-pull.png)

- **"How likely is this, really?"** Remember the inflation from the medical-study trick? Undo it, and a raw score of 0.23 becomes roughly **1 in 29,000**. That's small, but real.
- **"How worried should we be?"** Urgency bands are based on *how many times above normal* a square is running, such as "5× normal, inspect today". A fixed cut-off like "critical above 0.8" would never trigger, and the map would stay green all monsoon.
- **"Where do I send my only team?"** A moderate risk above a road and two villages outranks a severe risk in empty forest. Roads and settlements are added *after* the model, never inside it, because danger and consequences are different things.

---

## How good is it, honestly?

I tested it two ways. **On time:** train on 2007–2013, tune on 2014, then test on 2015–2016, which it had never seen. **On place:** remove a whole region, train on the rest, and test on the region it never visited.

![Testing on future years, and on whole regions left out of training.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-09-validation-design-a-chronological-train.png)

![Scores on regions the model never trained on, against the future-years test (orange line).](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-region_generalisation.png)

Three of the four regions score close to or above the future-years test. That suggests it learned *conditions*, not *places*. The North East is the weakest of the four.

![The final numbers, on the held-out test years.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-03.png)

**In one line: check the top 10% of squares and you reach 28.7% of the landslides, nearly three times the 10% you'd reach at random.** At a 5% budget it's 2.6 times random; at 20% it's 2.3 times. On the stricter all-thresholds measure it's 1.45 times better than guessing, and I'd rather state that plainly too. The main ceiling is the rainfall data, not the method, which is the next section.

---

## What it can't do

**It only sees daily rain totals.** This is the biggest limit, and it comes from the data, not the model. A three-hour cloudburst and a full day of drizzle can have the same daily total and completely different effects on a hillside.

To be fair to the data, it does capture the *build-up*. Rain in the days before a landslide separates clearly (108 mm before landslides against 66 mm on normal days), and the classic intensity-versus-duration check matches what researchers report:

![Rainfall intensity against duration before landslides: the same downward pattern the research literature describes.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-intensity_duration.png)

What it can't see is the final burst that tips a soaked slope over.

**Each square is 11 km wide.** Mountain rain can change within a kilometre, so the rain that caused a slide may not show up in its square.

**Unreported landslides can't be fully fixed.** The exclusion zone helps; nothing removes the problem entirely.

**It is not an official warning system.** No hourly forecasts, no validation against government bulletins, no human in the loop. It's a prototype that ranks slopes for inspection, and the app says so on every screen.

---

## What's next

- **Race it against a plain rainfall rule.** Landslide scientists have long ranked slopes simply by how much it has rained. Beating random guessing is one bar; beating that rule is the one that really justifies a model. The comparison is now built into the pipeline, scored on the same test years, and its result is the next thing I'll publish.
- **Hourly rainfall.** The single biggest lever on accuracy, for the reason above.
- **The North East.** It's the weakest region, and the one I most want to improve.
- **An online demo,** so anyone can click around the map instead of reading about it.

---

## What I'd tell you

![Four lessons from building Slopewatch.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-lessons.png)

**1. A number can be true and still mislead you.** 99.998% accuracy. A score that "dropped" while the model improved. Always ask what a number is measured against.

**2. The bug usually sits upstream of the symptom.** A strange chart came from a slope filter two steps earlier. A crash came from a date table written by a completely different stage. When something looks off, retrace how the data was made.

**3. A fix without a test isn't finished.** And the test should be impossible to pass by accident.

**4. Measure your excuses.** "Not enough data" became a curve that showed exactly what more data was worth: not much. The next real gain will come from sharper rainfall data, not more rows.

The elevation bug is the one I keep coming back to. It produced a sensible-looking chart and respectable scores, the kind of result that ships in plenty of projects. Catching it came down to one habit: don't accept a result until you understand *why* it's true. That habit, and the test that locks the fix in place, are as much the output of this project as the model itself.

If you're building something where the rare event is the one that matters, whether that's landslides, fraud, equipment failure or disease, I hope some of this saves you a few weeks.

*The code, pipeline and model card are open on GitHub: [github.com/CHAITANYA-2002/imarticus](https://github.com/CHAITANYA-2002/imarticus). If you work on landslides, disaster risk or rare-event modelling, I'd love to hear from you, and feedback on where to take it next is very welcome.*
