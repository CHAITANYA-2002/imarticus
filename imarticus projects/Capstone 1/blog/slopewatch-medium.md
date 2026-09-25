# I Built an AI to Predict Himalayan Landslides. It Learned to Recognise Tibet Instead.

### Six months, 82 million cell-days, and the quiet mistakes that make a model look brilliant while it learns the wrong lesson.

![99.998% accurate. Completely useless.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-cover.png)

Every monsoon, the news out of Uttarakhand, Himachal and the North East follows the same pattern. A hillside gives way, a highway disappears under mud, and a village is cut off for days. Afterwards someone always asks whether anyone saw it coming.

That question stuck with me, so I spent six months trying to build something that could help answer it: a model that looks at recent rainfall and at the shape of the land, and tells a district which slopes to worry about today.

This post is about how that went. I'll be honest up front: the model I ended up with is useful, but modest. The more interesting story is the five separate times the project fooled me along the way, and how I caught each one. If you build models, or you manage people who do, I think at least one of these will look familiar.

You don't need a machine learning background to follow along. I'll explain the jargon as it comes up.

---

## First, a quick look at the problem

Landslides in this region are overwhelmingly a monsoon event. When I plotted which months landslides were reported in, most states lined up neatly behind the June to September rains.

![Landslides by month for six states. Most follow the monsoon; Kashmir, fed partly by winter storms and snowmelt, is the odd one out.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-seasonality.png)

Kashmir is the exception, and that detail comes back later. For now, the takeaway is simple: rain triggers these slides, and the land decides where they happen.

To turn that into data, I split the Himalayan arc and India's North Eastern Region into a grid of 40,800 squares, each roughly 11 km across. I kept the 22,594 squares with meaningful slope and looked at ten years of days. That's about **82 million "cell-days"**, meaning one square on one day.

For labels I used NASA's Global Landslide Catalog. It started with 11,033 records, and after filtering to my area and time window I had 1,719 landslides.

![How NASA's global catalogue narrows to the 1,719 landslides used in this project.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-06-catalogue-funnel-11-033-raw.png)

So: 1,719 landslides spread across 82 million cell-days, or roughly **one landslide per 48,000 cell-days**.

---

## The 99.998% model

That ratio is the single most important number in the project, and it's hard to picture, so here it is drawn out.

![Each dot is one cell on one day. Exactly one had a landslide.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-one-in-48000.png)

My very first model looked at all of that and learned the easiest possible rule: *say "no landslide", always.* It was right 99.998% of the time.

It was also completely useless, because it never warned anyone about anything.

That's why you won't find the word "accuracy" anywhere in my evaluation code. When the thing you care about is this rare, accuracy is worse than unhelpful: it gives a broken model a beautiful score. Instead I used measures that only reward a model for actually finding landslides, which I'll explain as they come up.

There was a practical problem too. Building a table with 82 million rows, each needing 45 days of weather history from a free API that allows about 10,000 calls a day, would have taken decades.

So I borrowed a trick from epidemiology called **case-control sampling**. Keep every real landslide (the "cases"), and pair them with a carefully chosen set of normal days (the "controls"). That took 82 million rows down to 11,955.

![Instead of 82 million rows, keep every landslide and a designed set of comparison days: 11,955 rows in total.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-01-a-full-space-time-panel.png)

There's a catch that's easy to forget. In my sample, about 14% of rows are landslides. In the real world it's 0.002%. So every probability the model produces comes out wildly inflated. The good news is that you can correct for this exactly with a bit of maths at the end, as long as you remember to. I'll come back to that.

---

## Choosing what "no landslide" looks like

This was the part that took the most thought. If you pick your "normal days" at random, you mostly get flat land in the dry season. A model trained to tell those apart from monsoon landslides in the mountains does great, but only because it has learned "mountains in July" versus "plains in January". That isn't landslide prediction; it's a calendar and a map.

So I drew the controls in three groups, each designed to rule out one lazy shortcut.

![Three kinds of comparison day, each holding one thing constant so the model can't cheat with it.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-07-the-three-control-strata-temporal.png)

- **Same place, different day (50%).** The exact same hillside, within 30 days of the same time of year. The question becomes: *why did it fail on this monsoon day and not the hundreds of others?* The terrain is identical, so only the weather can explain it.
- **Same day, different place (30%).** A cell 25 to 300 km away on the same date. *The same storm hit both, so why did only one slope go?*
- **Anywhere, any day (20%).** A random cell and date, to show the model what an ordinary day looks like.

One more rule turned out to matter just as much. Any candidate "no landslide" day within **15 km and 2 days** of a recorded landslide gets thrown out rather than labelled "no".

![The exclusion zone: days close to a reported landslide in space and time are dropped, never labelled "no landslide".](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-08-space-time-exclusion-buffer-around.png)

The reason is that NASA's catalogue only contains landslides that someone *reported*. In remote valleys, plenty go unrecorded. A cell 8 km from a confirmed slide, in the same storm, may well have failed too, and nobody wrote it down. Calling that a "no" would be teaching the model something false. That rule dropped 46,234 cell-days.

---

## The bug that would have shipped

This is the story I most want to tell.

I trained a model and did what you're supposed to do: I checked what it was actually paying attention to. The standard tool for this is called SHAP. It tells you how much each input pushed each prediction up or down.

The top input was `elev_mean`, the average elevation of the cell. And it wasn't a close race; it was **2.3 times** more important than anything else.

Honestly, I nearly moved on. Elevation *sounds* like a reasonable thing to predict landslides with. Higher ground is steeper, colder and more broken up. If I'd shown that chart in a review, I suspect most people would have nodded.

What bothered me was how much it dominated. Everything I'd read says landslides here are driven by rain: weeks of it soaking a slope, then one heavy burst tipping it over. Rain should have been at the top, and it wasn't even close.

So I went digging, and eventually found the problem two steps upstream of where it showed up.

To decide which cells counted as "hilly enough" to model, I used one simple rule: **average slope of at least 5 degrees**. That's a sensible rule, since landslides need slopes. And it clearly does track something real; landslides get more common as slopes get steeper.

![Landslides per 1,000 cells rise steadily with slope, which is why a slope threshold was the obvious filter.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-slope_density.png)

Here's what I missed. **A high plateau can be steep too.** Ladakh and the Tibetan plateau are high, cold, dry, mostly outside the monsoon, and comfortably above 5 degrees of slope. They passed my filter without any trouble.

![The terrain pipeline. The hill filter checks slope only and has no elevation term, so the plateau slips through.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-05-terrain-pipeline-each-dem-tile.png)

Meanwhile, the real landslides sit mostly in the middle altitudes, between 1,000 and 2,000 metres.

![Where the real landslides happen: most sit between 1,000 and 2,000 metres.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-elevation_bands.png)

Put those together and you can guess what happened. My random "normal day" cells were pulled heavily from the plateau. **The median control cell sat at 4,479 m, while the median landslide sat at 1,433 m.** That's a gap of more than three kilometres.

![Before the fix, controls came from far higher ground than landslides. After matching by elevation band, the gap disappears.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-10-before-and-after-elevation-band.png)

The model wasn't learning what makes a slope fail. It was learning to tell Tibet apart from a Himalayan valley. That's easy, it scores well, and it's useless for warning anyone.

### The fix

My first instinct was to change the hill filter. That would have been wrong, because the filter was doing its job: those plateau cells really are steep.

The problem was in how I picked the comparison days. So now every control is matched to the **elevation band** of the landslide it's compared against (500 m bands, give or take one band). The elevation gap went from **+3,046 m to −17 m**, and `elev_mean` fell out of the top 15 inputs altogether.

Here's what the model pays attention to now:

![After the fix: rainfall leads, and terrain appears as roughness rather than altitude.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-shap.png)

Rain on the day comes first, then rain over the last three days, then how many wet days came before. Terrain shows up fourth, and as *roughness* (`slope_std`), not height. That's much closer to what geologists describe.

The part I find most striking: **I didn't change the model at all.** Not a single setting. I only changed how the comparison group was chosen, and the model started answering a completely different question.

### Making sure it never comes back

A fix you can't detect breaking isn't really a fix, so I wrote a test for it. The test builds a small fake world with plateau cells at 4,500 m and slope cells at 1,400 m, **mixed together on the map**.

That mixing is the whole point. If the plateau sat off in its own corner, the distance rules might filter it out by accident and the test would pass for the wrong reason. Mixed together, distance tells you nothing, and only the elevation matching can pass it.

### What I won't claim

It would be tempting to say "and accuracy improved by X after the fix". I'm not going to, because the before and after models were trained and tested on different data, so comparing their scores wouldn't be fair. The only honest before-and-after here is the chart of what the model pays attention to.

---

## The score dropped. The model got better.

A few weeks later I had three times as much weather data (coverage went from 20% of samples to 74%). I retrained, fully expecting the headline score to go up.

It went down, from 0.410 to 0.244.

The score I'm using here is **PR-AUC**. In plain terms, it measures how well the model ranks real landslides above normal days. The catch is that its floor isn't zero: a model that guesses at random scores whatever fraction of your data is landslides. So you can only read it against that baseline.

![Same model, more data: the score fell with the baseline, while every measure that ignores the baseline improved.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-01.png)

Look at the "base rate" row. It fell too, from 0.267 to 0.168, because my weather downloads had fetched landslide rows first, so early on the data was heavier in landslides than it should have been. Measured against its own baseline, the model barely changed (1.54 times better than guessing versus 1.45 times).

Everything that *doesn't* depend on the baseline got better: the probabilities were more trustworthy, and the model caught 40% more landslides at a realistic inspection budget. It even started doing slightly better on regions it had never seen than on future dates in regions it knew, which is exactly what you want.

If I'd reported "the score fell from 0.41 to 0.24 after adding data", every word would have been true and the overall message would have been false. That's why every score in this project is reported with its baseline and a confidence range next to it.

---

## When two models tie, ask a better question

I trained three kinds of model: logistic regression (the simple, classic one), random forest, and XGBoost. Here's how they did on data they'd never seen:

![Precision-recall curves for all three models. The dashed line is what random guessing would score.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-pr_curves.png)

![Three models, side by side. The score ranges overlap; the recall at a fixed budget does not.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-02.png)

By PR-AUC alone, random forest "wins" by 0.0035. But look at the 95% ranges: they overlap almost completely. That difference is noise.

So I asked a more practical question. A district can't inspect every slope; it has a limited number of teams. **If you can only check the top 5% of cells today, what share of the real landslides do you catch?**

![If you can only inspect a fixed share of cells, how many real landslides do you reach?](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-recall_at_budget.png)

Random forest catches 5.3%. XGBoost catches 13.0%, about two and a half times as many. That gap is real.

So my rule became: if models are statistically tied on the headline score, break the tie on how many landslides they catch at a fixed budget. There's one safeguard. The tie-break has to agree on two separate slices of data before it's allowed to decide. They agreed, and XGBoost shipped.

---

## When the model started memorising

Tripling the data caused a different problem. My code let the tree models grow more complex once there were enough landslide examples, with the cut-off set at 500. The extra data pushed me from 465 to 941, so the trees grew deep, and this happened:

```
random_forest   train 0.934   validation 0.241
xgboost         train 0.991   validation 0.214
```

Nearly perfect on data it had seen, poor on data it hadn't. That's memorisation, not learning.

The mistake was counting landslides on their own. What matters is landslides *per input*. With 41 inputs, 941 landslides works out to only about 23 per input, which is thin for a model that can memorise. The rule now uses that ratio, and both tree models got better on unseen data once they were reined in. I worked this out using only the training and validation data, so the final test set stayed untouched.

---

## Fighting an API that fights back

Not every problem was statistical. The biggest time sink was simply downloading weather: each of the 11,955 samples needed 45 days of history, about 38,000 API calls against a limit of roughly 10,000 per day. That's a job that runs for days and has to survive interruptions.

Two things went wrong that I think apply well beyond this project.

**Not every error deserves a retry.** My downloader retried every failure four times, then gave up. That's right for "too many requests" (HTTP 429), because waiting fixes it. But one day it hit a different error, HTTP 400, "bad request", and after four pointless retries it crashed a run with 10,000 good downloads still to go.

The cause turned out to be two steps upstream again. My forecasting step added a few upcoming dates to a shared date table. The sampler read that same table with no end limit, so it happily picked "normal days" from those brand-new dates. The weather archive runs about five days behind real time, and it rightly refused to give me data it hadn't processed yet.

![How a small change in one stage produced a crash three stages later, and the two fixes it needed.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-17-causal-chain-stage-08-appends.png)

A 429 says "not right now". A 400 says "never, the way you asked". Now any 400-type error is logged and skipped, and the run carries on.

**Don't let your cache keys move.** An earlier version saved API calls by merging overlapping date windows for the same cell. It was 21% cheaper. But the saved files were named by their start and end dates, and those merged windows shifted whenever the sample changed.

![Before: merged windows whose edges move when the sample changes. After: each window anchored to its own date.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-16-before-merged-windows-per-cell.png)

When I fixed the elevation bug and rebuilt the sample, nearly every file name changed. **Of 2,190 downloaded windows, 232 were still usable.** Days of API quota, gone, because I'd optimised the wrong thing. Windows are now fixed to their own sample date, and the cache checks whether the *days* it needs exist on disk, whatever file they're in.

---

## How much data is enough? I measured it

"We need more data" is the easiest excuse in machine learning. So I tested it: train on 25%, 40%, 55% and so on of the data, keep the test set fixed, and see how much the score improves each time.

![The learning curve: big gains early, then almost flat. More of the same data won't move the needle much.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-18-learning-curve-re-measured-at.png)

Going from a quarter of the data to all of it added **0.031**. The last big step added 0.003, and the final one actually dipped slightly. The curve has flattened, so more of the same data isn't what's holding the model back.

My favourite detail: this was the *second* time I drew this curve. The first time, with a third of the data, I predicted that tripling it would add somewhere between 0.02 and 0.04. It added 0.031. So when I say finishing the downloads won't change much, that's a prediction this method has already got right once.

---

## So what does it actually do?

After all that, here's the system itself. Four public data sources feed a twelve-stage pipeline into a MySQL database, and a six-screen app sits on top.

![The architecture: four public data sources, a twelve-stage pipeline, a star-schema database, and an app on top.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-02-architecture-four-external-sources-feed.png)

I tested it two ways. First, on time: train on 2007–2013, tune on 2014, and test on 2015–2016, which the model never saw. Second, on place: remove one whole region, train on the rest, and see how it does in the region it has never visited.

![How the model was tested: on future years, and on entire regions left out of training.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-09-validation-design-a-chronological-train.png)

![Scores on regions the model never saw during training, against the test on future years (orange line).](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-region_generalisation.png)

Three of the four regions score close to or above the future-years test, which suggests it has learned conditions rather than memorising places. The North East is the weakest, and that's worth further work.

Here's the honest headline:

![The final numbers on the held-out test years.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/table-03.png)

**It's 1.45 times better than guessing.** That's a real signal, but a modest one, and I'd rather say so plainly than dress it up. The more useful way to read it: if a district inspects its top 10% of cells, it reaches roughly three in every ten landslides. Whether that's worth doing depends on what an inspection costs, and that's a call for a district engineer, not for me.

### One score, three questions

Something I got wrong at first was assuming one number could serve everyone. In practice, the people using this ask three different questions.

![From forecast to decision: one model score becomes a real-world likelihood, a risk band, and a priority list.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/diagram-14-scoring-flow-a-forecast-pull.png)

- **"How likely is this, really?"** This is where the earlier correction comes in. Remember the inflation from sampling? Undo it, and a raw score of 0.23 becomes something like **1 in 6,100**.
- **"How worried should we be?"** Risk bands are set by how many times above normal a cell's risk is, not by the raw score. A fixed rule like "critical above 0.8" would never trigger at all, and the whole map would stay green through a monsoon.
- **"Where do I send my only team?"** A moderate risk above a road and two villages matters more than a severe one in empty forest. So exposure (roads, settlements) is added *after* the model, never as an input. The danger and the consequences are different things, and mixing them hides both.

---

## What it can't do

Every limitation here is also written in the project's model card. A project that only lists its wins is marketing.

**It only sees daily rainfall totals.** This is the biggest limit, and it comes from the data, not the model. Landslides react to how *hard* it rains, often over just a few hours. A three-hour cloudburst and a full day of drizzle can look identical in daily totals and be completely different on a hillside.

To be fair to the data, it isn't useless on rainfall. I ran the classic check researchers use, rainfall intensity against duration, and the pattern matches what the scientific literature reports. Rainfall in the days *before* a landslide also separates clearly: 108 mm before landslides against 66 mm for normal days.

![Rainfall intensity against duration before landslides: the same downward pattern the research literature reports.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/chart-intensity_duration.png)

So the data sees the build-up. What it can't see is the final burst that tips a soaked slope over.

**Each cell is 11 km wide**, which matches the weather data's native resolution, but mountain rain can change a lot within a kilometre or two. The rain that caused a slide may simply not show up in its cell.

**Unreported landslides can't be fully fixed.** The exclusion zone helps, but nothing removes the problem completely.

**It is not an operational warning system.** There's no hourly forecast, no validation against official bulletins, and no human in the loop. It ranks cells for inspection. Calling it more than that would be irresponsible.

---

## What I'd tell you

![Four lessons from six months of building this.](https://raw.githubusercontent.com/CHAITANYA-2002/imarticus/main/imarticus%20projects/Capstone%201/blog/images/card-lessons.png)

**1. A number can be true and still mislead you.** 99.998% accuracy. A score that "dropped" while the model improved. Always ask what a number is being measured against.

**2. The bug usually sits upstream of the symptom.** My strange chart came from a slope filter two stages earlier. My crash came from a date table written by a completely different stage. When a result looks odd, don't just stare at the model; retrace how the data got there.

**3. A fix without a test isn't finished.** And build the test so it can't pass by accident.

**4. Measure your excuses.** "Not enough data" turned into a curve that told me exactly what more data was worth, which was not much. The next real gain will come from sharper rainfall data, not more rows.

The elevation bug is the one I keep thinking about. It would have shipped. It produced a sensible-looking chart, respectable scores, and a model that had quietly learned to recognise Tibet. I only caught it because the number felt too big and I went looking.

That isn't a process. It's luck plus suspicion. I'd like more of the second and less reliance on the first, and I suspect most of us building models would too.

*The full code, data pipeline and model card are on GitHub: [github.com/CHAITANYA-2002/imarticus](https://github.com/CHAITANYA-2002/imarticus). If you work on landslides, disaster risk or rare-event modelling, I'd love to hear where you think this goes wrong.*
