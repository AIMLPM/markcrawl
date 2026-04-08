# Extraction Quality Comparison

<!-- style: v2, 2026-04-08 -->

Markcrawl produces the cleanest Markdown of all 8 tools: 100% content signal, 4 words of preamble per page, and 1% repeat rate. The next closest tool on content signal is firecrawl (85%), but firecrawl's low consensus scores (29% precision, 34% recall) indicate it extracts a different subset of content than the other 7 tools agree on. For RAG pipelines, less preamble and lower repeat rates translate directly into cleaner chunks and better retrieval.

## Methodology

Four automated quality metrics — no LLM or human review needed:

1. **Junk phrases** — known boilerplate strings (nav, footer, breadcrumbs) found in output
2. **Preamble [1]** — average words per page appearing *before* the first heading.
   Nav chrome (version selectors, language pickers, prev/next links) lives here.
   A tool with a high preamble count is injecting site chrome into every chunk.
3. **Cross-page repeat rate** — fraction of sentences that appear on >50% of pages.
   Real content appears on at most a few pages; nav text repeats everywhere.
   High repeat rate = nav boilerplate polluting every chunk in the RAG index.
4. **Cross-tool consensus** — precision (how much output is agreed real content?)
   and recall (how much agreed content did this tool capture?).

> **Why preamble + repeat rate matter for RAG:** A tool that embeds 200 words of
> nav chrome before each article degrades retrieval in two ways: (1) chunks contain
> irrelevant tokens that dilute semantic similarity, and (2) the same nav sentences
> match queries on every page, flooding results with false positives.

## Summary: RAG readiness at a glance

For RAG pipelines, **clean output matters more than comprehensive output.**
A tool that includes 1,000 words of nav chrome per page pollutes every
chunk in the vector index, degrading retrieval for every query.

| Tool | Content signal | Preamble [1] | Repeat rate | Junk/page | Precision | Recall |
|---|---|---|---|---|---|---|
| **markcrawl** | **100%** | **4** | **1%** | **0.5** | **100%** | **83%** |
| firecrawl | 85% | 324 | 0% | 2.5 | 29% | 34% |
| scrapy+md | 81% | 220 | 2% | 1.1 | 100% | 92% |
| crawlee | 77% | 270 | 2% | 1.7 | 100% | 96% |
| colly+md | 77% | 262 | 2% | 1.7 | 100% | 95% |
| playwright | 77% | 266 | 2% | 1.7 | 100% | 96% |
| crawl4ai | 70% | 387 | 3% | 1.0 | 100% | 86% |
| crawl4ai-raw | 70% | 390 | 3% | 1.0 | 100% | 86% |

**[1]** Avg words per page before the first heading (nav chrome).


**Key takeaway:** markcrawl achieves 100% content signal with only 4 words of preamble per page -- compared to 390 for crawl4ai-raw. Its recall is lower (83% vs 96%) because it strips nav, footer, and sponsor content that other tools include. For RAG use cases, this trade-off favors markcrawl: every chunk in the vector index is pure content, with no boilerplate to dilute embeddings or pollute retrieval results.

Cleaner output does not necessarily produce better retrieval -- see [RETRIEVAL_COMPARISON.md](RETRIEVAL_COMPARISON.md) for how all tools perform similarly on hit rate. But it does produce better LLM answers -- see [ANSWER_QUALITY.md](ANSWER_QUALITY.md). See [METHODOLOGY.md](METHODOLOGY.md) for the full test setup.

> **Content signal** = percentage of output that is content (not preamble nav chrome).
> Higher is better. A tool with 100% content signal has zero nav/header pollution.
> **Repeat rate** = fraction of phrases appearing on >50% of pages (boilerplate).
> **Junk/page** = known boilerplate phrases detected per page.

## quotes-toscrape

| Tool | Avg words | Preamble [1] | Repeat rate | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|---|---|
| **markcrawl** | **216** | **0** | **1%** | **1** | **2.8** | **0.0** | **100%** | **100%** |
| crawl4ai | 224 | 0 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| crawl4ai-raw | 224 | 0 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| scrapy+md | 224 | 0 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| crawlee | 227 | 3 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| colly+md | 227 | 3 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| playwright | 227 | 3 | 2% | 1 | 2.8 | 0.0 | 100% | 100% |
| firecrawl | 203 | 23 | 1% | 1 | 0.9 | 0.0 | 50% | 50% |

**[1]** Avg words per page before the first heading (nav chrome). Values >50 likely indicate nav/boilerplate problems.

<details>
<summary>Sample output — first 40 lines of <code>quotes.toscrape.com/tag/deep-thoughts/page/1</code></summary>

This shows what each tool outputs at the *top* of the same page.
Nav boilerplate appears here before the real content starts.

**markcrawl**
```
# [Quotes to Scrape](/)

[Login](/login)

### Viewing tag: [deep-thoughts](/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
by Albert Einstein
[(about)](/author/Albert-Einstein)

Tags:
[change](/tag/change/page/1/)
[deep-thoughts](/tag/deep-thoughts/page/1/)
[thinking](/tag/thinking/page/1/)
[world](/tag/world/page/1/)

## Top Ten tags

[love](/tag/love/)

[inspirational](/tag/inspirational/)

[life](/tag/life/)

[humor](/tag/humor/)

[books](/tag/books/)

[reading](/tag/reading/)

[friendship](/tag/friendship/)

[friends](/tag/friends/)

[truth](/tag/truth/)

[simile](/tag/simile/)
```

**crawl4ai**
```
#  [Quotes to Scrape](https://quotes.toscrape.com/)
[Login](https://quotes.toscrape.com/login)
### Viewing tag: [deep-thoughts](https://quotes.toscrape.com/tag/deep-thoughts/page/1/)
“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.” by Albert Einstein [(about)](https://quotes.toscrape.com/author/Albert-Einstein)
Tags: [change](https://quotes.toscrape.com/tag/change/page/1/) [deep-thoughts](https://quotes.toscrape.com/tag/deep-thoughts/page/1/) [thinking](https://quotes.toscrape.com/tag/thinking/page/1/) [world](https://quotes.toscrape.com/tag/world/page/1/)
## Top Ten tags
[love](https://quotes.toscrape.com/tag/love/) [inspirational](https://quotes.toscrape.com/tag/inspirational/) [life](https://quotes.toscrape.com/tag/life/) [humor](https://quotes.toscrape.com/tag/humor/) [books](https://quotes.toscrape.com/tag/books/) [reading](https://quotes.toscrape.com/tag/reading/) [friendship](https://quotes.toscrape.com/tag/friendship/) [friends](https://quotes.toscrape.com/tag/friends/) [truth](https://quotes.toscrape.com/tag/truth/) [simile](https://quotes.toscrape.com/tag/simile/)
Quotes by: [GoodReads.com](https://www.goodreads.com/quotes)
Made with ❤ by [Zyte](https://www.zyte.com)
```

**crawl4ai-raw**
```
#  [Quotes to Scrape](https://quotes.toscrape.com/)
[Login](https://quotes.toscrape.com/login)
### Viewing tag: [deep-thoughts](https://quotes.toscrape.com/tag/deep-thoughts/page/1/)
“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.” by Albert Einstein [(about)](https://quotes.toscrape.com/author/Albert-Einstein)
Tags: [change](https://quotes.toscrape.com/tag/change/page/1/) [deep-thoughts](https://quotes.toscrape.com/tag/deep-thoughts/page/1/) [thinking](https://quotes.toscrape.com/tag/thinking/page/1/) [world](https://quotes.toscrape.com/tag/world/page/1/)
## Top Ten tags
[love](https://quotes.toscrape.com/tag/love/) [inspirational](https://quotes.toscrape.com/tag/inspirational/) [life](https://quotes.toscrape.com/tag/life/) [humor](https://quotes.toscrape.com/tag/humor/) [books](https://quotes.toscrape.com/tag/books/) [reading](https://quotes.toscrape.com/tag/reading/) [friendship](https://quotes.toscrape.com/tag/friendship/) [friends](https://quotes.toscrape.com/tag/friends/) [truth](https://quotes.toscrape.com/tag/truth/) [simile](https://quotes.toscrape.com/tag/simile/)
Quotes by: [GoodReads.com](https://www.goodreads.com/quotes)
Made with ❤ by [Zyte](https://www.zyte.com)
```

**scrapy+md**
```
# [Quotes to Scrape](/)

[Login](/login)

### Viewing tag: [deep-thoughts](/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
by Albert Einstein
[(about)](/author/Albert-Einstein)

Tags:
[change](/tag/change/page/1/)
[deep-thoughts](/tag/deep-thoughts/page/1/)
[thinking](/tag/thinking/page/1/)
[world](/tag/world/page/1/)

## Top Ten tags

[love](/tag/love/)

[inspirational](/tag/inspirational/)

[life](/tag/life/)

[humor](/tag/humor/)

[books](/tag/books/)

[reading](/tag/reading/)

[friendship](/tag/friendship/)

[friends](/tag/friends/)

[truth](/tag/truth/)

[simile](/tag/simile/)

Quotes by: [GoodReads.com](https://www.goodreads.com/quotes)
```

**crawlee**
```
Quotes to Scrape



# [Quotes to Scrape](/)

[Login](/login)

### Viewing tag: [deep-thoughts](/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
by Albert Einstein
[(about)](/author/Albert-Einstein)

Tags:
[change](/tag/change/page/1/)
[deep-thoughts](/tag/deep-thoughts/page/1/)
[thinking](/tag/thinking/page/1/)
[world](/tag/world/page/1/)

## Top Ten tags

[love](/tag/love/)

[inspirational](/tag/inspirational/)

[life](/tag/life/)

[humor](/tag/humor/)

[books](/tag/books/)

[reading](/tag/reading/)

[friendship](/tag/friendship/)

[friends](/tag/friends/)

[truth](/tag/truth/)
```

**colly+md**
```
Quotes to Scrape



# [Quotes to Scrape](/)

[Login](/login)

### Viewing tag: [deep-thoughts](/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
by Albert Einstein
[(about)](/author/Albert-Einstein)

Tags:
[change](/tag/change/page/1/)
[deep-thoughts](/tag/deep-thoughts/page/1/)
[thinking](/tag/thinking/page/1/)
[world](/tag/world/page/1/)

## Top Ten tags

[love](/tag/love/)

[inspirational](/tag/inspirational/)

[life](/tag/life/)

[humor](/tag/humor/)

[books](/tag/books/)

[reading](/tag/reading/)

[friendship](/tag/friendship/)

[friends](/tag/friends/)

[truth](/tag/truth/)
```

**playwright**
```
Quotes to Scrape



# [Quotes to Scrape](/)

[Login](/login)

### Viewing tag: [deep-thoughts](/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.”
by Albert Einstein
[(about)](/author/Albert-Einstein)

Tags:
[change](/tag/change/page/1/)
[deep-thoughts](/tag/deep-thoughts/page/1/)
[thinking](/tag/thinking/page/1/)
[world](/tag/world/page/1/)

## Top Ten tags

[love](/tag/love/)

[inspirational](/tag/inspirational/)

[life](/tag/life/)

[humor](/tag/humor/)

[books](/tag/books/)

[reading](/tag/reading/)

[friendship](/tag/friendship/)

[friends](/tag/friends/)

[truth](/tag/truth/)
```

**firecrawl**
```
[Quotes to Scrape](http://quotes.toscrape.com/)

================================================

[Login](http://quotes.toscrape.com/login)

### Viewing tag: [deep-thoughts](http://quotes.toscrape.com/tag/deep-thoughts/page/1/)

“The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.” by Albert Einstein [(about)](http://quotes.toscrape.com/author/Albert-Einstein)

Tags: [change](http://quotes.toscrape.com/tag/change/page/1/)
 [deep-thoughts](http://quotes.toscrape.com/tag/deep-thoughts/page/1/)
 [thinking](http://quotes.toscrape.com/tag/thinking/page/1/)
 [world](http://quotes.toscrape.com/tag/world/page/1/)

Top Ten tags
------------

[love](http://quotes.toscrape.com/tag/love/) [inspirational](http://quotes.toscrape.com/tag/inspirational/) [life](http://quotes.toscrape.com/tag/life/) [humor](http://quotes.toscrape.com/tag/humor/) [books](http://quotes.toscrape.com/tag/books/) [reading](http://quotes.toscrape.com/tag/reading/) [friendship](http://quotes.toscrape.com/tag/friendship/) [friends](http://quotes.toscrape.com/tag/friends/) [truth](http://quotes.toscrape.com/tag/truth/) [simile](http://quotes.toscrape.com/tag/simile/)
```

</details>

<details>
<summary>Per-page word counts and preamble [1]</summary>

| URL | markcrawl words / preamble [1] | crawl4ai words / preamble [1] | crawl4ai-raw words / preamble [1] | scrapy+md words / preamble [1] | crawlee words / preamble [1] | colly+md words / preamble [1] | playwright words / preamble [1] | firecrawl words / preamble [1] |
|---|---|---|---|---|---|---|---|---|
| quotes.toscrape.com | 271 / 0 | 282 / 0 | 282 / 0 | 282 / 0 | 285 / 3 | 285 / 3 | 285 / 3 | 271 / 271 |
| quotes.toscrape.com/author/Albert-Einstein | 621 / 0 | 629 / 0 | 629 / 0 | 629 / 0 | 632 / 3 | 632 / 3 | 632 / 3 | 621 / 5 |
| quotes.toscrape.com/author/J-K-Rowling | 650 / 0 | 658 / 0 | 658 / 0 | 658 / 0 | 661 / 3 | 661 / 3 | 661 / 3 | 650 / 5 |
| quotes.toscrape.com/login | — | — | — | — | — | — | — | 7 / 7 |
| quotes.toscrape.com/tag/abilities/page/1 | 46 / 0 | 54 / 0 | 54 / 0 | 54 / 0 | 57 / 3 | 57 / 3 | 57 / 3 | 46 / 5 |
| quotes.toscrape.com/tag/be-yourself/page/1 | 46 / 0 | 54 / 0 | 54 / 0 | 54 / 0 | 57 / 3 | 57 / 3 | 57 / 3 | — |
| quotes.toscrape.com/tag/change/page/1 | — | — | — | — | — | — | — | 53 / 5 |
| quotes.toscrape.com/tag/choices/page/1 | — | — | — | — | — | — | — | 46 / 5 |
| quotes.toscrape.com/tag/deep-thoughts/page/1 | 53 / 0 | 61 / 0 | 61 / 0 | 61 / 0 | 64 / 3 | 64 / 3 | 64 / 3 | 53 / 5 |
| quotes.toscrape.com/tag/edison/page/1 | 45 / 0 | 53 / 0 | 53 / 0 | 53 / 0 | 56 / 3 | 56 / 3 | 56 / 3 | — |
| quotes.toscrape.com/tag/friends | 305 / 0 | 313 / 0 | 313 / 0 | 313 / 0 | 316 / 3 | 316 / 3 | 316 / 3 | — |
| quotes.toscrape.com/tag/friendship | 158 / 0 | 166 / 0 | 166 / 0 | 166 / 0 | 169 / 3 | 169 / 3 | 169 / 3 | — |
| quotes.toscrape.com/tag/humor | 284 / 0 | 295 / 0 | 295 / 0 | 295 / 0 | 298 / 3 | 298 / 3 | 298 / 3 | — |
| quotes.toscrape.com/tag/inspirational/page/1 | — | — | — | — | — | — | — | 484 / 5 |
| quotes.toscrape.com/tag/life | 498 / 0 | 509 / 0 | 509 / 0 | 509 / 0 | 512 / 3 | 512 / 3 | 512 / 3 | — |
| quotes.toscrape.com/tag/life/page/1 | — | — | — | — | — | — | — | 498 / 5 |
| quotes.toscrape.com/tag/live/page/1 | — | — | — | — | — | — | — | 59 / 5 |
| quotes.toscrape.com/tag/miracle/page/1 | — | — | — | — | — | — | — | 59 / 5 |
| quotes.toscrape.com/tag/miracles/page/1 | 59 / 0 | 67 / 0 | 67 / 0 | 67 / 0 | 70 / 3 | 70 / 3 | 70 / 3 | 59 / 5 |
| quotes.toscrape.com/tag/paraphrased/page/1 | 69 / 0 | 77 / 0 | 77 / 0 | 77 / 0 | 80 / 3 | 80 / 3 | 80 / 3 | — |
| quotes.toscrape.com/tag/simile | 76 / 0 | 84 / 0 | 84 / 0 | 84 / 0 | 87 / 3 | 87 / 3 | 87 / 3 | — |
| quotes.toscrape.com/tag/thinking/page/1 | — | — | — | — | — | — | — | 85 / 5 |
| quotes.toscrape.com/tag/world/page/1 | 53 / 0 | 61 / 0 | 61 / 0 | 61 / 0 | 64 / 3 | 64 / 3 | 64 / 3 | 53 / 5 |

</details>

## books-toscrape

| Tool | Avg words | Preamble [1] | Repeat rate | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|---|---|
| **markcrawl** | **299** | **8** | **0%** | **0** | **1.8** | **0.0** | **100%** | **97%** |
| crawl4ai | 518 | 181 | 1% | 0 | 11.2 | 0.0 | 100% | 99% |
| crawl4ai-raw | 518 | 181 | 1% | 0 | 11.2 | 0.0 | 100% | 99% |
| scrapy+md | 403 | 103 | 1% | 0 | 1.8 | 0.0 | 100% | 97% |
| crawlee | 412 | 112 | 1% | 0 | 1.8 | 0.0 | 100% | 98% |
| colly+md | 412 | 112 | 1% | 0 | 1.8 | 0.0 | 100% | 98% |
| playwright | 412 | 112 | 1% | 0 | 1.8 | 0.0 | 100% | 98% |
| firecrawl | 328 | 328 | 0% | 0 | 0.0 | 0.0 | 61% | 84% |

**[1]** Avg words per page before the first heading (nav chrome). Values >50 likely indicate nav/boilerplate problems.

**Reading the numbers:**
**markcrawl** produces the cleanest output with 8 words of preamble per page, while **firecrawl** injects 328 words of nav chrome before content begins. The word count gap (299 vs 518 avg words) is largely explained by preamble: 181 words of nav chrome account for ~35% of crawl4ai's output on this site.

<details>
<summary>Sample output — first 40 lines of <code>books.toscrape.com/catalogue/the-coming-woman-a-novel-based-on-the-life-of-the-infamous-feminist-victoria-woodhull_993/index.html</code></summary>

This shows what each tool outputs at the *top* of the same page.
Nav boilerplate appears here before the real content starts.

**markcrawl**
```
* [Home](../../index.html)
* [Books](../category/books_1/index.html)
* [Default](../category/books/default_15/index.html)
* The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

£17.93

In stock (19 available)


---

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

## Product Description

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

## Product Information

|  |  |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
| Availability | In stock (19 available) |
| Number of reviews | 0 |

## Products you recently viewed

* ### [The Dirty Little Secrets ...](../the-dirty-little-secrets-of-getting-your-dream-job_994/index.html "The Dirty Little Secrets of Getting Your Dream Job")

  £33.34

  In stock
```

**crawl4ai**
```
[Books to Scrape](https://books.toscrape.com/index.html) We love being scraped!
  * [Home](https://books.toscrape.com/index.html)
  * [Books](https://books.toscrape.com/catalogue/category/books_1/index.html)
  * [Default](https://books.toscrape.com/catalogue/category/books/default_15/index.html)
  * The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull


![The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull](https://books.toscrape.com/media/cache/97/36/9736132a43b8e6e3989932218ef309ed.jpg)
# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull
£17.93
* * *
**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.
## Product Description
"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more
## Product Information  
| UPC  | e72a5dfc7e9267b2  |  
| --- | --- |  
| Product Type  | Books  |  
| Price (excl. tax)  | £17.93  |  
| Price (incl. tax)  | £17.93  |  
| Tax  | £0.00  |  
| Availability  | In stock (19 available)  |  
| Number of reviews  | 0  |  
## Products you recently viewed
  * [![The Dirty Little Secrets of Getting Your Dream Job](https://books.toscrape.com/media/cache/92/27/92274a95b7c251fea59a2b8a78275ab4.jpg)](https://books.toscrape.com/catalogue/the-dirty-little-secrets-of-getting-your-dream-job_994/index.html)
### [The Dirty Little Secrets ...](https://books.toscrape.com/catalogue/the-dirty-little-secrets-of-getting-your-dream-job_994/index.html "The Dirty Little Secrets of Getting Your Dream Job")
£33.34
Add to basket
  * [![The Requiem Red](https://books.toscrape.com/media/cache/68/33/68339b4c9bc034267e1da611ab3b34f8.jpg)](https://books.toscrape.com/catalogue/the-requiem-red_995/index.html)
### [The Requiem Red](https://books.toscrape.com/catalogue/the-requiem-red_995/index.html "The Requiem Red")
£22.65
Add to basket
  * [![Sapiens: A Brief History of Humankind](https://books.toscrape.com/media/cache/be/a5/bea5697f2534a2f86a3ef27b5a8c12a6.jpg)](https://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html)
### [Sapiens: A Brief History ...](https://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html "Sapiens: A Brief History of Humankind")
£54.23
Add to basket
  * [![Sharp Objects](https://books.toscrape.com/media/cache/32/51/3251cf3a3412f53f339e42cac2134093.jpg)](https://books.toscrape.com/catalogue/sharp-objects_997/index.html)
### [Sharp Objects](https://books.toscrape.com/catalogue/sharp-objects_997/index.html "Sharp Objects")
£47.82
Add to basket
```

**crawl4ai-raw**
```
[Books to Scrape](https://books.toscrape.com/index.html) We love being scraped!
  * [Home](https://books.toscrape.com/index.html)
  * [Books](https://books.toscrape.com/catalogue/category/books_1/index.html)
  * [Default](https://books.toscrape.com/catalogue/category/books/default_15/index.html)
  * The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull


![The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull](https://books.toscrape.com/media/cache/97/36/9736132a43b8e6e3989932218ef309ed.jpg)
# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull
£17.93
* * *
**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.
## Product Description
"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more
## Product Information  
| UPC  | e72a5dfc7e9267b2  |  
| --- | --- |  
| Product Type  | Books  |  
| Price (excl. tax)  | £17.93  |  
| Price (incl. tax)  | £17.93  |  
| Tax  | £0.00  |  
| Availability  | In stock (19 available)  |  
| Number of reviews  | 0  |  
## Products you recently viewed
  * [![The Dirty Little Secrets of Getting Your Dream Job](https://books.toscrape.com/media/cache/92/27/92274a95b7c251fea59a2b8a78275ab4.jpg)](https://books.toscrape.com/catalogue/the-dirty-little-secrets-of-getting-your-dream-job_994/index.html)
### [The Dirty Little Secrets ...](https://books.toscrape.com/catalogue/the-dirty-little-secrets-of-getting-your-dream-job_994/index.html "The Dirty Little Secrets of Getting Your Dream Job")
£33.34
Add to basket
  * [![The Requiem Red](https://books.toscrape.com/media/cache/68/33/68339b4c9bc034267e1da611ab3b34f8.jpg)](https://books.toscrape.com/catalogue/the-requiem-red_995/index.html)
### [The Requiem Red](https://books.toscrape.com/catalogue/the-requiem-red_995/index.html "The Requiem Red")
£22.65
Add to basket
  * [![Sapiens: A Brief History of Humankind](https://books.toscrape.com/media/cache/be/a5/bea5697f2534a2f86a3ef27b5a8c12a6.jpg)](https://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html)
### [Sapiens: A Brief History ...](https://books.toscrape.com/catalogue/sapiens-a-brief-history-of-humankind_996/index.html "Sapiens: A Brief History of Humankind")
£54.23
Add to basket
  * [![Sharp Objects](https://books.toscrape.com/media/cache/32/51/3251cf3a3412f53f339e42cac2134093.jpg)](https://books.toscrape.com/catalogue/sharp-objects_997/index.html)
### [Sharp Objects](https://books.toscrape.com/catalogue/sharp-objects_997/index.html "Sharp Objects")
£47.82
Add to basket
```

**scrapy+md**
```
[Books to Scrape](../../index.html) We love being scraped!

* [Home](../../index.html)
* [Books](../category/books_1/index.html)
* [Default](../category/books/default_15/index.html)
* The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

£17.93

In stock (19 available)

 

---

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

## Product Description

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

## Product Information

|  |  |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
| Availability | In stock (19 available) |
| Number of reviews | 0 |

## Products you recently viewed

* ### [The Dirty Little Secrets ...](../the-dirty-little-secrets-of-getting-your-dream-job_994/index.html "The Dirty Little Secrets of Getting Your Dream Job")

  £33.34
```

**crawlee**
```
The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull | Books to Scrape - Sandbox




[Books to Scrape](../../index.html) We love being scraped!

* [Home](../../index.html)
* [Books](../category/books_1/index.html)
* [Default](../category/books/default_15/index.html)
* The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

£17.93

In stock (19 available)

 

---

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

## Product Description

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

## Product Information

|  |  |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
| Availability | In stock (19 available) |
| Number of reviews | 0 |
```

**colly+md**
```
  


The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull | Books to Scrape - Sandbox




[Books to Scrape](../../index.html) We love being scraped!

* [Home](../../index.html)
* [Books](../category/books_1/index.html)
* [Default](../category/books/default_15/index.html)
* The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

£17.93

In stock (19 available)

 

---

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

## Product Description

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

## Product Information

|  |  |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
```

**playwright**
```
The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull | Books to Scrape - Sandbox




[Books to Scrape](../../index.html) We love being scraped!

* [Home](../../index.html)
* [Books](../category/books_1/index.html)
* [Default](../category/books/default_15/index.html)
* The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

# The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

£17.93

In stock (19 available)

 

---

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

## Product Description

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

## Product Information

|  |  |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
| Availability | In stock (19 available) |
| Number of reviews | 0 |
```

**firecrawl**
```
*   [Home](http://books.toscrape.com/index.html)
    
*   [Books](http://books.toscrape.com/catalogue/category/books_1/index.html)
    
*   [Default](http://books.toscrape.com/catalogue/category/books/default_15/index.html)
    
*   The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull

![The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull](http://books.toscrape.com/media/cache/97/36/9736132a43b8e6e3989932218ef309ed.jpg)

The Coming Woman: A Novel Based on the Life of the Infamous Feminist, Victoria Woodhull
=======================================================================================

£17.93

In stock (19 available)

* * *

**Warning!** This is a demo website for web scraping purposes. Prices and ratings here were randomly assigned and have no real meaning.

Product Description
-------------------

"If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a "If you have a heart, if you have a soul, Karen Hicks' The Coming Woman will make you fall in love with Victoria Woodhull."-Kinky Friedman, author and Governor of the Heart of Texas "What kind of confidence would it take for a woman to buck the old boy's club of politics in 1872? More than 140 years pre-Hillary, there was Victoria Woodhull. This book takes you back with a breathtaking, present-tense bird's eye view into a time when women's liberation was primarily confined to one woman's very capable, independent mind. I couldn't put it down."---Ruth Buzzi, Golden Globe Award winner and Television Hall of Fame inductee"Sadly, too many Americans have never heard of Victoria Woodhull, let alone learned of her story: her revolutionary campaign for the presidency at a time when women weren't even allowed to vote, her support for worker's rights, or her feminist commitment to equality, a century before the official battle over the Equal Rights Amendment. But in The Coming Woman, Karen Hicks brings Woodhull's efforts to life, and reminds us that some of our nation's greatest figures aren't always featured in the history books. It is a riveting account of an amazing woman and her struggle for justice and human dignity, told in an engaging and eminently readable style."-Tim Wise, author, "White Like Me: Reflections on Race from a Privileged Son""The Coming Woman" is a novel based on the life of feminist Victoria Woodhull, the first woman to run for U.S. President, 50 years before women could even vote!Running for President wasn't Victoria's only first as a woman. She was also the first to own a successful Wall Street firm, the first to publish a successful national newspaper, and the first to head the two-million-member Spiritualist Association. She was the first woman to enter the Senate Judiciary Committee chambers to petition for woman's suffrage, her argument changing the entire focus of the suffragist movement by pointing out that the 14th and 15th Amendments already gave women the vote.In her campaign for the Presidency, Victoria Woodhull boldly addressed many of the issues we still face today: equal pay for equal work; freedom in love; corporate greed and political corruption fueled by powerful lobbyists; and the increasing disparity between the rich and the poor, to name only a few. Her outspoken and common-sense ideas may shed a new perspective on the parallel conundrums of today's world.This bold, beautiful, and sexually progressive woman dared to take on society and religion. To make an example of the hypocrisy in what Mark Twain dubbed The Gilded Age, she exposed the extramarital affairs of the most popular religious figure of the day (Henry Ward Beecher). This led to her persecution and imprisonment and the longest, most infamous trial of the 19th century. But it did not stop her fight for equality.Victoria's epic story, set in the late 1800s, comes to life in a modern, fictional style, while staying true to the actual words and views of the many well-known characters. ...more

Product Information
-------------------

|     |     |
| --- | --- |
| UPC | e72a5dfc7e9267b2 |
| Product Type | Books |
| Price (excl. tax) | £17.93 |
| Price (incl. tax) | £17.93 |
| Tax | £0.00 |
| Availability | In stock (19 available) |
| Number of reviews | 0   |

Products you recently viewed
```

</details>

<details>
<summary>Per-page word counts and preamble [1]</summary>

| URL | markcrawl words / preamble [1] | crawl4ai words / preamble [1] | crawl4ai-raw words / preamble [1] | scrapy+md words / preamble [1] | crawlee words / preamble [1] | colly+md words / preamble [1] | playwright words / preamble [1] | firecrawl words / preamble [1] |
|---|---|---|---|---|---|---|---|---|
| books.toscrape.com | 397 / 5 | 702 / 232 | 702 / 232 | 531 / 130 | 539 / 138 | 539 / 138 | 539 / 138 | 515 / 515 |
| books.toscrape.com/catalogue/a-light-in-the-attic_1000/ | — | — | — | — | — | — | — | 276 / 276 |
| books.toscrape.com/catalogue/category/books/academic_40 | 51 / 6 | 282 / 233 | 282 / 233 | 185 / 131 | 192 / 138 | 192 / 138 | 192 / 138 | 57 / 57 |
| books.toscrape.com/catalogue/category/books/add-a-comme | 424 / 8 | 745 / 235 | 745 / 235 | 558 / 133 | 567 / 142 | 567 / 142 | 567 / 142 | 558 / 558 |
| books.toscrape.com/catalogue/category/books/adult-ficti | 53 / 7 | 284 / 234 | 284 / 234 | 187 / 132 | 195 / 140 | 195 / 140 | 195 / 140 | 59 / 59 |
| books.toscrape.com/catalogue/category/books/art_25/inde | — | — | — | — | — | — | — | 211 / 211 |
| books.toscrape.com/catalogue/category/books/autobiograp | 169 / 6 | 412 / 233 | 412 / 233 | 303 / 131 | 310 / 138 | 310 / 138 | 310 / 138 | 203 / 203 |
| books.toscrape.com/catalogue/category/books/biography_3 | 145 / 6 | 410 / 233 | 410 / 233 | 279 / 131 | 286 / 138 | 286 / 138 | 286 / 138 | 193 / 193 |
| books.toscrape.com/catalogue/category/books/business_35 | 296 / 6 | 612 / 233 | 612 / 233 | 430 / 131 | 437 / 138 | 437 / 138 | 437 / 138 | 409 / 409 |
| books.toscrape.com/catalogue/category/books/childrens_1 | — | — | — | — | — | — | — | 455 / 455 |
| books.toscrape.com/catalogue/category/books/christian-f | — | — | — | — | — | — | — | 173 / 173 |
| books.toscrape.com/catalogue/category/books/christian_4 | 96 / 6 | 342 / 233 | 342 / 233 | 230 / 131 | 237 / 138 | 237 / 138 | 237 / 138 | 121 / 121 |
| books.toscrape.com/catalogue/category/books/classics_6/ | — | — | — | — | — | — | — | 404 / 404 |
| books.toscrape.com/catalogue/category/books/contemporar | 84 / 6 | 320 / 233 | 320 / 233 | 218 / 131 | 225 / 138 | 225 / 138 | 225 / 138 | 99 / 99 |
| books.toscrape.com/catalogue/category/books/crime_51/in | 58 / 6 | 296 / 233 | 296 / 233 | 192 / 131 | 199 / 138 | 199 / 138 | 199 / 138 | 71 / 71 |
| books.toscrape.com/catalogue/category/books/cultural_49 | 46 / 6 | 274 / 233 | 274 / 233 | 180 / 131 | 187 / 138 | 187 / 138 | 187 / 138 | 49 / 49 |
| books.toscrape.com/catalogue/category/books/default_15/ | 439 / 6 | 777 / 233 | 777 / 233 | 573 / 131 | 580 / 138 | 580 / 138 | 580 / 138 | 590 / 590 |
| books.toscrape.com/catalogue/category/books/erotica_50/ | 44 / 6 | 271 / 233 | 271 / 233 | 178 / 131 | 185 / 138 | 185 / 138 | 185 / 138 | 46 / 46 |
| books.toscrape.com/catalogue/category/books/fantasy_19/ | 436 / 6 | 764 / 233 | 764 / 233 | 570 / 131 | 577 / 138 | 577 / 138 | 577 / 138 | 577 / 577 |
| books.toscrape.com/catalogue/category/books/fiction_10/ | — | — | — | — | — | — | — | 449 / 449 |
| books.toscrape.com/catalogue/category/books/food-and-dr | 548 / 8 | 978 / 235 | 978 / 235 | 682 / 133 | 691 / 142 | 691 / 142 | 691 / 142 | 791 / 791 |
| books.toscrape.com/catalogue/category/books/health_47/i | 124 / 6 | 384 / 233 | 384 / 233 | 258 / 131 | 265 / 138 | 265 / 138 | 265 / 138 | 165 / 165 |
| books.toscrape.com/catalogue/category/books/historical- | 391 / 7 | 681 / 234 | 681 / 234 | 525 / 132 | 533 / 140 | 533 / 140 | 533 / 140 | 494 / 494 |
| books.toscrape.com/catalogue/category/books/historical_ | 75 / 6 | 315 / 233 | 315 / 233 | 209 / 131 | 216 / 138 | 216 / 138 | 216 / 138 | 92 / 92 |
| books.toscrape.com/catalogue/category/books/history_32/ | 447 / 6 | 822 / 233 | 822 / 233 | 581 / 131 | 588 / 138 | 588 / 138 | 588 / 138 | 631 / 631 |
| books.toscrape.com/catalogue/category/books/horror_31/i | 275 / 6 | 524 / 233 | 524 / 233 | 409 / 131 | 416 / 138 | 416 / 138 | 416 / 138 | 331 / 331 |
| books.toscrape.com/catalogue/category/books/humor_30/in | 239 / 6 | 529 / 233 | 529 / 233 | 373 / 131 | 380 / 138 | 380 / 138 | 380 / 138 | 322 / 322 |
| books.toscrape.com/catalogue/category/books/music_14/in | 304 / 6 | 616 / 233 | 616 / 233 | 438 / 131 | 445 / 138 | 445 / 138 | 445 / 138 | 415 / 415 |
| books.toscrape.com/catalogue/category/books/mystery_3/i | 407 / 6 | 710 / 233 | 710 / 233 | 541 / 131 | 548 / 138 | 548 / 138 | 548 / 138 | 523 / 523 |
| books.toscrape.com/catalogue/category/books/new-adult_2 | 130 / 7 | 370 / 234 | 370 / 234 | 264 / 132 | 272 / 140 | 272 / 140 | 272 / 140 | 155 / 155 |
| books.toscrape.com/catalogue/category/books/nonfiction_ | 501 / 6 | 887 / 233 | 887 / 233 | 635 / 131 | 642 / 138 | 642 / 138 | 642 / 138 | 700 / 700 |
| books.toscrape.com/catalogue/category/books/novels_46/i | — | — | — | — | — | — | — | 61 / 61 |
| books.toscrape.com/catalogue/category/books/paranormal_ | 52 / 6 | 284 / 233 | 284 / 233 | 186 / 131 | 193 / 138 | 193 / 138 | 193 / 138 | 59 / 59 |
| books.toscrape.com/catalogue/category/books/parenting_2 | 53 / 6 | 286 / 233 | 286 / 233 | 187 / 131 | 194 / 138 | 194 / 138 | 194 / 138 | 61 / 61 |
| books.toscrape.com/catalogue/category/books/philosophy_ | 236 / 6 | 516 / 233 | 516 / 233 | 370 / 131 | 377 / 138 | 377 / 138 | 377 / 138 | 311 / 311 |
| books.toscrape.com/catalogue/category/books/poetry_23/i | 355 / 6 | 642 / 233 | 642 / 233 | 489 / 131 | 496 / 138 | 496 / 138 | 496 / 138 | 453 / 453 |
| books.toscrape.com/catalogue/category/books/politics_48 | 94 / 6 | 340 / 233 | 340 / 233 | 228 / 131 | 235 / 138 | 235 / 138 | 235 / 138 | 119 / 119 |
| books.toscrape.com/catalogue/category/books/psychology_ | 184 / 6 | 460 / 233 | 460 / 233 | 318 / 131 | 325 / 138 | 325 / 138 | 325 / 138 | 247 / 247 |
| books.toscrape.com/catalogue/category/books/religion_12 | 180 / 6 | 453 / 233 | 453 / 233 | 314 / 131 | 321 / 138 | 321 / 138 | 321 / 138 | 240 / 240 |
| books.toscrape.com/catalogue/category/books/romance_8/i | 412 / 6 | 716 / 233 | 716 / 233 | 546 / 131 | 553 / 138 | 553 / 138 | 553 / 138 | 529 / 529 |
| books.toscrape.com/catalogue/category/books/science-fic | 322 / 7 | 615 / 234 | 615 / 234 | 456 / 132 | 464 / 140 | 464 / 140 | 464 / 140 | 420 / 420 |
| books.toscrape.com/catalogue/category/books/science_22/ | 350 / 6 | 690 / 233 | 690 / 233 | 484 / 131 | 491 / 138 | 491 / 138 | 491 / 138 | 491 / 491 |
| books.toscrape.com/catalogue/category/books/self-help_4 | 152 / 7 | 422 / 234 | 422 / 234 | 286 / 132 | 294 / 140 | 294 / 140 | 294 / 140 | 205 / 205 |
| books.toscrape.com/catalogue/category/books/sequential- | 441 / 7 | 774 / 234 | 774 / 234 | 575 / 132 | 583 / 140 | 583 / 140 | 583 / 140 | 587 / 587 |
| books.toscrape.com/catalogue/category/books/short-stori | — | — | — | — | — | — | — | 48 / 48 |
| books.toscrape.com/catalogue/category/books/spiritualit | 171 / 6 | 447 / 233 | 447 / 233 | 305 / 131 | 312 / 138 | 312 / 138 | 312 / 138 | 232 / 232 |
| books.toscrape.com/catalogue/category/books/sports-and- | 137 / 8 | 391 / 235 | 391 / 235 | 271 / 133 | 280 / 142 | 280 / 142 | 280 / 142 | 174 / 174 |
| books.toscrape.com/catalogue/category/books/suspense_44 | 52 / 6 | 284 / 233 | 284 / 233 | 186 / 131 | 193 / 138 | 193 / 138 | 193 / 138 | 59 / 59 |
| books.toscrape.com/catalogue/category/books/thriller_37 | 211 / 6 | 465 / 233 | 465 / 233 | 345 / 131 | 352 / 138 | 352 / 138 | 352 / 138 | 260 / 260 |
| books.toscrape.com/catalogue/category/books/travel_2/in | 258 / 6 | 550 / 233 | 550 / 233 | 392 / 131 | 399 / 138 | 399 / 138 | 399 / 138 | 345 / 345 |
| books.toscrape.com/catalogue/category/books/womens-fict | 330 / 7 | 614 / 234 | 614 / 234 | 464 / 132 | 472 / 140 | 472 / 140 | 472 / 140 | 421 / 421 |
| books.toscrape.com/catalogue/category/books/young-adult | 386 / 7 | 676 / 234 | 676 / 234 | 520 / 132 | 528 / 140 | 528 / 140 | 528 / 140 | 489 / 489 |
| books.toscrape.com/catalogue/category/books_1/index.htm | — | — | — | — | — | — | — | 513 / 513 |
| books.toscrape.com/catalogue/its-only-the-himalayas_981 | 448 / 11 | 480 / 22 | 480 / 22 | 463 / 18 | 473 / 28 | 473 / 28 | 473 / 28 | — |
| books.toscrape.com/catalogue/libertarianism-for-beginne | 411 / 10 | 442 / 20 | 442 / 20 | 426 / 17 | 435 / 26 | 435 / 26 | 435 / 26 | — |
| books.toscrape.com/catalogue/mesaerion-the-best-science | 500 / 15 | 530 / 29 | 530 / 29 | 515 / 22 | 528 / 35 | 528 / 35 | 528 / 35 | — |
| books.toscrape.com/catalogue/olio_984/index.html | 462 / 8 | 491 / 16 | 491 / 16 | 477 / 15 | 484 / 22 | 484 / 22 | 484 / 22 | — |
| books.toscrape.com/catalogue/page-2.html | 413 / 5 | 726 / 232 | 726 / 232 | 547 / 130 | 555 / 138 | 555 / 138 | 555 / 138 | — |
| books.toscrape.com/catalogue/rip-it-up-and-start-again_ | 371 / 13 | 407 / 26 | 407 / 26 | 386 / 20 | 398 / 32 | 398 / 32 | 398 / 32 | — |
| books.toscrape.com/catalogue/sapiens-a-brief-history-of | — | — | — | — | — | — | — | 489 / 489 |
| books.toscrape.com/catalogue/set-me-free_988/index.html | 365 / 11 | 411 / 21 | 411 / 21 | 380 / 18 | 389 / 27 | 389 / 27 | 389 / 27 | — |
| books.toscrape.com/catalogue/shakespeares-sonnets_989/i | 375 / 9 | 421 / 18 | 421 / 18 | 390 / 16 | 398 / 24 | 398 / 24 | 398 / 24 | — |
| books.toscrape.com/catalogue/sharp-objects_997/index.ht | 420 / 9 | 427 / 18 | 427 / 18 | 435 / 16 | 443 / 24 | 443 / 24 | 443 / 24 | 433 / 433 |
| books.toscrape.com/catalogue/soumission_998/index.html | 297 / 8 | 304 / 16 | 304 / 16 | 312 / 15 | 319 / 22 | 319 / 22 | 319 / 22 | 308 / 308 |
| books.toscrape.com/catalogue/starving-hearts-triangular | 436 / 13 | 486 / 26 | 486 / 26 | 451 / 20 | 463 / 32 | 463 / 32 | 463 / 32 | — |
| books.toscrape.com/catalogue/the-black-maria_991/index. | 696 / 10 | 742 / 20 | 742 / 20 | 711 / 17 | 720 / 26 | 720 / 26 | 720 / 26 | — |
| books.toscrape.com/catalogue/the-boys-in-the-boat-nine- | 576 / 25 | 620 / 50 | 620 / 50 | 591 / 32 | 615 / 56 | 615 / 56 | 615 / 56 | — |
| books.toscrape.com/catalogue/the-coming-woman-a-novel-b | 789 / 22 | 818 / 44 | 818 / 44 | 804 / 29 | 825 / 50 | 825 / 50 | 825 / 50 | 830 / 830 |
| books.toscrape.com/catalogue/the-dirty-little-secrets-o | 489 / 16 | 508 / 32 | 508 / 32 | 504 / 23 | 519 / 38 | 519 / 38 | 519 / 38 | 520 / 520 |
| books.toscrape.com/catalogue/the-requiem-red_995/index. | 350 / 11 | 362 / 21 | 362 / 21 | 365 / 18 | 374 / 27 | 374 / 27 | 374 / 27 | 372 / 372 |
| books.toscrape.com/catalogue/tipping-the-velvet_999/ind | — | — | — | — | — | — | — | 300 / 300 |

</details>

## fastapi-docs

| Tool | Avg words | Preamble [1] | Repeat rate | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|---|---|
| **markcrawl** | **2571** | **0** | **0%** | **31** | **18.2** | **20.8** | **100%** | **72%** |
| crawl4ai | 4018 | 1382 | 5% | 31 | 18.2 | 20.7 | 100% | 93% |
| crawl4ai-raw | 4025 | 1393 | 5% | 31 | 18.2 | 20.7 | 100% | 93% |
| scrapy+md | 3339 | 751 | 3% | 55 | 18.2 | 20.8 | 100% | 72% |
| crawlee | 3658 | 989 | 4% | 105 | 18.2 | 20.7 | 100% | 97% |
| colly+md | 3661 | 971 | 4% | 105 | 18.2 | 20.8 | 100% | 97% |
| playwright | 3642 | 972 | 4% | 105 | 18.2 | 20.8 | 100% | 97% |
| firecrawl | 1964 | 540 | 0% | 430 | 11.1 | 0.2 | 4% | 3% |

**[1]** Avg words per page before the first heading (nav chrome). Values >50 likely indicate nav/boilerplate problems.

**Reading the numbers:**
**markcrawl** produces the cleanest output with 0 word of preamble per page, while **crawl4ai-raw** injects 1393 words of nav chrome before content begins. The word count gap (1964 vs 4025 avg words) is largely explained by preamble: 1393 words of nav chrome account for ~35% of crawl4ai-raw's output on this site. markcrawl's lower recall (72% vs 97%) reflects stricter content filtering — the "missed" sentences are predominantly navigation, sponsor links, and footer text that other tools include as content. For RAG, this is a net positive: fewer junk tokens per chunk means better embedding quality and retrieval precision.

<details>
<summary>Sample output — first 40 lines of <code>fastapi.tiangolo.com/how-to/custom-request-and-route</code></summary>

This shows what each tool outputs at the *top* of the same page.
Nav boilerplate appears here before the real content starts.

**markcrawl**
```
# Custom Request and APIRoute class[¶](#custom-request-and-apiroute-class "Permanent link")

In some cases, you may want to override the logic used by the `Request` and `APIRoute` classes.

In particular, this may be a good alternative to logic in a middleware.

For example, if you want to read or manipulate the request body before it is processed by your application.

Danger

This is an "advanced" feature.

If you are just starting with **FastAPI** you might want to skip this section.

## Use cases[¶](#use-cases "Permanent link")

Some use cases include:

* Converting non-JSON request bodies to JSON (e.g. [`msgpack`](https://msgpack.org/index.html)).
* Decompressing gzip-compressed request bodies.
* Automatically logging all request bodies.

## Handling custom request body encodings[¶](#handling-custom-request-body-encodings "Permanent link")

Let's see how to make use of a custom `Request` subclass to decompress gzip requests.

And an `APIRoute` subclass to use that custom request class.

### Create a custom `GzipRequest` class[¶](#create-a-custom-gziprequest-class "Permanent link")

Tip

This is a toy example to demonstrate how it works, if you need Gzip support, you can use the provided [`GzipMiddleware`](../../advanced/middleware/#gzipmiddleware).

First, we create a `GzipRequest` class, which will overwrite the `Request.body()` method to decompress the body in the presence of an appropriate header.

If there's no `gzip` in the header, it will not try to decompress the body.

That way, the same route class can handle gzip compressed or uncompressed requests.
```

**crawl4ai**
```
[ Skip to content ](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)
[ **FastAPI Cloud** waiting list 🚀 ](https://fastapicloud.com)
[ Follow **@fastapi** on **X (Twitter)** to stay updated ](https://x.com/fastapi)
[ Follow **FastAPI** on **LinkedIn** to stay updated ](https://www.linkedin.com/company/fastapi)
[ **FastAPI and friends** newsletter 🎉 ](https://fastapi.tiangolo.com/newsletter/)
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/blockbee-banner.png) ](https://blockbee.io?ref=fastapi "BlockBee Cryptocurrency Payment Gateway")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/scalar-banner.svg) ](https://github.com/scalar/scalar/?utm_source=fastapi&utm_medium=website&utm_campaign=top-banner "Scalar: Beautiful Open-Source API References from Swagger/OpenAPI files")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/propelauth-banner.png) ](https://www.propelauth.com/?utm_source=fastapi&utm_campaign=1223&utm_medium=topbanner "Auth, user management and more for your B2B product")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/zuplo-banner.png) ](https://zuplo.link/fastapi-web "Zuplo: Scale, Protect, Document, and Monetize your FastAPI")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/liblab-banner.png) ](https://liblab.com?utm_source=fastapi "liblab - Generate SDKs from FastAPI")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/render-banner.svg) ](https://docs.render.com/deploy-fastapi?utm_source=deploydoc&utm_medium=referral&utm_campaign=fastapi "Deploy & scale any full-stack web app on Render. Focus on building apps, not infra.")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/coderabbit-banner.png) ](https://www.coderabbit.ai/?utm_source=fastapi&utm_medium=banner&utm_campaign=fastapi "Cut Code Review Time & Bugs in Half with CodeRabbit")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/subtotal-banner.svg) ](https://subtotal.com/?utm_source=fastapi&utm_medium=sponsorship&utm_campaign=open-source "Making Retail Purchases Actionable for Brands and Developers")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/railway-banner.png) ](https://docs.railway.com/guides/fastapi?utm_medium=integration&utm_source=docs&utm_campaign=fastapi "Deploy enterprise applications at startup speed")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/serpapi-banner.png) ](https://serpapi.com/?utm_source=fastapi_website "SerpApi: Web Search API")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/greptile-banner.png) ](https://www.greptile.com/?utm_source=fastapi&utm_medium=sponsorship&utm_campaign=fastapi_sponsor_page "Greptile: The AI Code Reviewer")
[ ![logo](https://fastapi.tiangolo.com/img/icon-white.svg) ](https://fastapi.tiangolo.com/ "FastAPI")
FastAPI 
Custom Request and APIRoute class 
  * [ en - English ](https://fastapi.tiangolo.com/)
  * [ de - Deutsch ](https://fastapi.tiangolo.com/de/)
  * [ es - español ](https://fastapi.tiangolo.com/es/)
  * [ fr - français ](https://fastapi.tiangolo.com/fr/)
  * [ ja - 日本語 ](https://fastapi.tiangolo.com/ja/)
  * [ ko - 한국어 ](https://fastapi.tiangolo.com/ko/)
  * [ pt - português ](https://fastapi.tiangolo.com/pt/)
  * [ ru - русский язык ](https://fastapi.tiangolo.com/ru/)
  * [ tr - Türkçe ](https://fastapi.tiangolo.com/tr/)
  * [ uk - українська мова ](https://fastapi.tiangolo.com/uk/)
  * [ zh - 简体中文 ](https://fastapi.tiangolo.com/zh/)
  * [ zh-hant - 繁體中文 ](https://fastapi.tiangolo.com/zh-hant/)


[ ](https://fastapi.tiangolo.com/how-to/custom-request-and-route/?q= "Share")
Type to start searching
[ fastapi/fastapi  ](https://github.com/fastapi/fastapi "Go to repository")
  * [ FastAPI ](https://fastapi.tiangolo.com/)
  * [ Features ](https://fastapi.tiangolo.com/features/)
  * [ Learn ](https://fastapi.tiangolo.com/learn/)
  * [ Reference ](https://fastapi.tiangolo.com/reference/)
```

**crawl4ai-raw**
```
[ Skip to content ](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)
[ **FastAPI Cloud** waiting list 🚀 ](https://fastapicloud.com)
[ Follow **@fastapi** on **X (Twitter)** to stay updated ](https://x.com/fastapi)
[ Follow **FastAPI** on **LinkedIn** to stay updated ](https://www.linkedin.com/company/fastapi)
[ **FastAPI and friends** newsletter 🎉 ](https://fastapi.tiangolo.com/newsletter/)
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/blockbee-banner.png) ](https://blockbee.io?ref=fastapi "BlockBee Cryptocurrency Payment Gateway")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/scalar-banner.svg) ](https://github.com/scalar/scalar/?utm_source=fastapi&utm_medium=website&utm_campaign=top-banner "Scalar: Beautiful Open-Source API References from Swagger/OpenAPI files")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/propelauth-banner.png) ](https://www.propelauth.com/?utm_source=fastapi&utm_campaign=1223&utm_medium=topbanner "Auth, user management and more for your B2B product")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/zuplo-banner.png) ](https://zuplo.link/fastapi-web "Zuplo: Scale, Protect, Document, and Monetize your FastAPI")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/liblab-banner.png) ](https://liblab.com?utm_source=fastapi "liblab - Generate SDKs from FastAPI")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/render-banner.svg) ](https://docs.render.com/deploy-fastapi?utm_source=deploydoc&utm_medium=referral&utm_campaign=fastapi "Deploy & scale any full-stack web app on Render. Focus on building apps, not infra.")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/coderabbit-banner.png) ](https://www.coderabbit.ai/?utm_source=fastapi&utm_medium=banner&utm_campaign=fastapi "Cut Code Review Time & Bugs in Half with CodeRabbit")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/subtotal-banner.svg) ](https://subtotal.com/?utm_source=fastapi&utm_medium=sponsorship&utm_campaign=open-source "Making Retail Purchases Actionable for Brands and Developers")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/railway-banner.png) ](https://docs.railway.com/guides/fastapi?utm_medium=integration&utm_source=docs&utm_campaign=fastapi "Deploy enterprise applications at startup speed")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/serpapi-banner.png) ](https://serpapi.com/?utm_source=fastapi_website "SerpApi: Web Search API")
[ sponsor ![](https://fastapi.tiangolo.com/img/sponsors/greptile-banner.png) ](https://www.greptile.com/?utm_source=fastapi&utm_medium=sponsorship&utm_campaign=fastapi_sponsor_page "Greptile: The AI Code Reviewer")
[ ![logo](https://fastapi.tiangolo.com/img/icon-white.svg) ](https://fastapi.tiangolo.com/ "FastAPI")
FastAPI 
Custom Request and APIRoute class 
  * [ en - English ](https://fastapi.tiangolo.com/)
  * [ de - Deutsch ](https://fastapi.tiangolo.com/de/)
  * [ es - español ](https://fastapi.tiangolo.com/es/)
  * [ fr - français ](https://fastapi.tiangolo.com/fr/)
  * [ ja - 日本語 ](https://fastapi.tiangolo.com/ja/)
  * [ ko - 한국어 ](https://fastapi.tiangolo.com/ko/)
  * [ pt - português ](https://fastapi.tiangolo.com/pt/)
  * [ ru - русский язык ](https://fastapi.tiangolo.com/ru/)
  * [ tr - Türkçe ](https://fastapi.tiangolo.com/tr/)
  * [ uk - українська мова ](https://fastapi.tiangolo.com/uk/)
  * [ zh - 简体中文 ](https://fastapi.tiangolo.com/zh/)
  * [ zh-hant - 繁體中文 ](https://fastapi.tiangolo.com/zh-hant/)


[ ](https://fastapi.tiangolo.com/how-to/custom-request-and-route/?q= "Share")
Initializing search 
[ fastapi/fastapi 
  * 0.135.3
  * 96.9k
  * 9k
```

**scrapy+md**
```
FastAPI

[fastapi/fastapi](https://github.com/fastapi/fastapi "Go to repository")

* [FastAPI](../..)
* [Features](../../features/)
* [Learn](../../learn/)

  Learn
  + [Python Types Intro](../../python-types/)
  + [Concurrency and async / await](../../async/)
  + [Environment Variables](../../environment-variables/)
  + [Virtual Environments](../../virtual-environments/)
  + [Tutorial - User Guide](../../tutorial/)

    Tutorial - User Guide
    - [First Steps](../../tutorial/first-steps/)
    - [Path Parameters](../../tutorial/path-params/)
    - [Query Parameters](../../tutorial/query-params/)
    - [Request Body](../../tutorial/body/)
    - [Query Parameters and String Validations](../../tutorial/query-params-str-validations/)
    - [Path Parameters and Numeric Validations](../../tutorial/path-params-numeric-validations/)
    - [Query Parameter Models](../../tutorial/query-param-models/)
    - [Body - Multiple Parameters](../../tutorial/body-multiple-params/)
    - [Body - Fields](../../tutorial/body-fields/)
    - [Body - Nested Models](../../tutorial/body-nested-models/)
    - [Declare Request Example Data](../../tutorial/schema-extra-example/)
    - [Extra Data Types](../../tutorial/extra-data-types/)
    - [Cookie Parameters](../../tutorial/cookie-params/)
    - [Header Parameters](../../tutorial/header-params/)
    - [Cookie Parameter Models](../../tutorial/cookie-param-models/)
    - [Header Parameter Models](../../tutorial/header-param-models/)
    - [Response Model - Return Type](../../tutorial/response-model/)
    - [Extra Models](../../tutorial/extra-models/)
    - [Response Status Code](../../tutorial/response-status-code/)
    - [Form Data](../../tutorial/request-forms/)
    - [Form Models](../../tutorial/request-form-models/)
    - [Request Files](../../tutorial/request-files/)
    - [Request Forms and Files](../../tutorial/request-forms-and-files/)
    - [Handling Errors](../../tutorial/handling-errors/)
```

**crawlee**
```
Custom Request and APIRoute class - FastAPI




:root{--md-text-font:"Roboto";--md-code-font:"Roboto Mono"}



\_\_md\_scope=new URL("../..",location),\_\_md\_hash=e=>[...e].reduce(((e,\_)=>(e<<5)-e+\_.charCodeAt(0)),0),\_\_md\_get=(e,\_=localStorage,t=\_\_md\_scope)=>JSON.parse(\_.getItem(t.pathname+"."+e)),\_\_md\_set=(e,\_,t=localStorage,a=\_\_md\_scope)=>{try{t.setItem(a.pathname+"."+e,JSON.stringify(\_))}catch(e){}}













.grecaptcha-badge {
visibility: hidden;
}





[Skip to content](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)

[Join the **FastAPI Cloud** waiting list 🚀](https://fastapicloud.com)

[Follow **@fastapi** on **X (Twitter)** to stay updated](https://x.com/fastapi)

[Follow **FastAPI** on **LinkedIn** to stay updated](https://www.linkedin.com/company/fastapi)

[Subscribe to the **FastAPI and friends** newsletter 🎉](https://fastapi.tiangolo.com/newsletter/)
```

**colly+md**
```
Custom Request and APIRoute class - FastAPI




:root{--md-text-font:"Roboto";--md-code-font:"Roboto Mono"}



\_\_md\_scope=new URL("../..",location),\_\_md\_hash=e=>[...e].reduce(((e,\_)=>(e<<5)-e+\_.charCodeAt(0)),0),\_\_md\_get=(e,\_=localStorage,t=\_\_md\_scope)=>JSON.parse(\_.getItem(t.pathname+"."+e)),\_\_md\_set=(e,\_,t=localStorage,a=\_\_md\_scope)=>{try{t.setItem(a.pathname+"."+e,JSON.stringify(\_))}catch(e){}}






[Skip to content](#custom-request-and-apiroute-class)

[Join the **FastAPI Cloud** waiting list 🚀](https://fastapicloud.com)

[Follow **@fastapi** on **X (Twitter)** to stay updated](https://x.com/fastapi)

[Follow **FastAPI** on **LinkedIn** to stay updated](https://www.linkedin.com/company/fastapi)

[Subscribe to the **FastAPI and friends** newsletter 🎉](https://fastapi.tiangolo.com/newsletter/)

[sponsor](https://blockbee.io?ref=fastapi "BlockBee Cryptocurrency Payment Gateway")

[sponsor](https://github.com/scalar/scalar/?utm_source=fastapi&utm_medium=website&utm_campaign=top-banner "Scalar: Beautiful Open-Source API References from Swagger/OpenAPI files")

[sponsor](https://www.propelauth.com/?utm_source=fastapi&utm_campaign=1223&utm_medium=topbanner "Auth, user management and more for your B2B product")

[sponsor](https://zuplo.link/fastapi-web "Zuplo: Scale, Protect, Document, and Monetize your FastAPI")

[sponsor](https://liblab.com?utm_source=fastapi "liblab - Generate SDKs from FastAPI")

[sponsor](https://docs.render.com/deploy-fastapi?utm_source=deploydoc&utm_medium=referral&utm_campaign=fastapi "Deploy & scale any full-stack web app on Render. Focus on building apps, not infra.")

[sponsor](https://www.coderabbit.ai/?utm_source=fastapi&utm_medium=banner&utm_campaign=fastapi "Cut Code Review Time & Bugs in Half with CodeRabbit")
```

**playwright**
```
Custom Request and APIRoute class - FastAPI




:root{--md-text-font:"Roboto";--md-code-font:"Roboto Mono"}



\_\_md\_scope=new URL("../..",location),\_\_md\_hash=e=>[...e].reduce(((e,\_)=>(e<<5)-e+\_.charCodeAt(0)),0),\_\_md\_get=(e,\_=localStorage,t=\_\_md\_scope)=>JSON.parse(\_.getItem(t.pathname+"."+e)),\_\_md\_set=(e,\_,t=localStorage,a=\_\_md\_scope)=>{try{t.setItem(a.pathname+"."+e,JSON.stringify(\_))}catch(e){}}






[Skip to content](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)

[Join the **FastAPI Cloud** waiting list 🚀](https://fastapicloud.com)

[Follow **@fastapi** on **X (Twitter)** to stay updated](https://x.com/fastapi)

[Follow **FastAPI** on **LinkedIn** to stay updated](https://www.linkedin.com/company/fastapi)

[Subscribe to the **FastAPI and friends** newsletter 🎉](https://fastapi.tiangolo.com/newsletter/)

[sponsor](https://blockbee.io?ref=fastapi "BlockBee Cryptocurrency Payment Gateway")

[sponsor](https://github.com/scalar/scalar/?utm_source=fastapi&utm_medium=website&utm_campaign=top-banner "Scalar: Beautiful Open-Source API References from Swagger/OpenAPI files")

[sponsor](https://www.propelauth.com/?utm_source=fastapi&utm_campaign=1223&utm_medium=topbanner "Auth, user management and more for your B2B product")

[sponsor](https://zuplo.link/fastapi-web "Zuplo: Scale, Protect, Document, and Monetize your FastAPI")

[sponsor](https://liblab.com?utm_source=fastapi "liblab - Generate SDKs from FastAPI")

[sponsor](https://docs.render.com/deploy-fastapi?utm_source=deploydoc&utm_medium=referral&utm_campaign=fastapi "Deploy & scale any full-stack web app on Render. Focus on building apps, not infra.")

[sponsor](https://www.coderabbit.ai/?utm_source=fastapi&utm_medium=banner&utm_campaign=fastapi "Cut Code Review Time & Bugs in Half with CodeRabbit")
```

**firecrawl**
```
 

[Skip to content](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)

Custom Request and APIRoute class[¶](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-request-and-apiroute-class)

======================================================================================================================================

In some cases, you may want to override the logic used by the `Request` and `APIRoute` classes.

In particular, this may be a good alternative to logic in a middleware.

For example, if you want to read or manipulate the request body before it is processed by your application.

Danger

This is an "advanced" feature.

If you are just starting with **FastAPI** you might want to skip this section.

Use cases[¶](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#use-cases)

--------------------------------------------------------------------------------------

Some use cases include:

*   Converting non-JSON request bodies to JSON (e.g. [`msgpack`](https://msgpack.org/index.html)
    ).
*   Decompressing gzip-compressed request bodies.
*   Automatically logging all request bodies.

Handling custom request body encodings[¶](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#handling-custom-request-body-encodings)

------------------------------------------------------------------------------------------------------------------------------------------------

Let's see how to make use of a custom `Request` subclass to decompress gzip requests.

And an `APIRoute` subclass to use that custom request class.

### Create a custom `GzipRequest` class[¶](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#create-a-custom-gziprequest-class)
```

</details>

<details>
<summary>Per-page word counts and preamble [1]</summary>

| URL | markcrawl words / preamble [1] | crawl4ai words / preamble [1] | crawl4ai-raw words / preamble [1] | scrapy+md words / preamble [1] | crawlee words / preamble [1] | colly+md words / preamble [1] | playwright words / preamble [1] | firecrawl words / preamble [1] |
|---|---|---|---|---|---|---|---|---|
| fastapi.tiangolo.com | 2230 / 0 | 3981 / 1528 | 3991 / 1538 | 3092 / 839 | 3376 / 1073 | 3404 / 1054 | 3357 / 1054 | 2388 / 196 |
| fastapi.tiangolo.com/?q= | — | — | — | — | — | — | — | 2388 / 196 |
| fastapi.tiangolo.com/_llm-test | — | — | — | — | — | — | — | 1598 / 678 |
| fastapi.tiangolo.com/_llm-test/?q= | — | — | — | — | — | — | — | 1598 / 678 |
| fastapi.tiangolo.com/about | — | — | — | — | — | — | — | 16 / 16 |
| fastapi.tiangolo.com/advanced | — | — | — | — | — | — | — | 113 / 113 |
| fastapi.tiangolo.com/advanced/additional-responses | — | — | — | — | — | — | — | 1252 / 1252 |
| fastapi.tiangolo.com/advanced/additional-status-codes | — | — | — | — | — | — | — | 466 / 466 |
| fastapi.tiangolo.com/advanced/advanced-dependencies | — | — | — | — | — | — | — | 2148 / 868 |
| fastapi.tiangolo.com/advanced/advanced-python-types | — | — | — | — | — | — | — | 319 / 319 |
| fastapi.tiangolo.com/advanced/async-sql-databases | — | — | — | — | — | — | — | 8 / 8 |
| fastapi.tiangolo.com/advanced/async-tests | — | — | — | — | — | — | — | 627 / 627 |
| fastapi.tiangolo.com/advanced/behind-a-proxy | — | — | — | — | — | — | — | 2118 / 143 |
| fastapi.tiangolo.com/advanced/conditional-openapi | — | — | — | — | — | — | — | 376 / 376 |
| fastapi.tiangolo.com/advanced/custom-request-and-route | — | — | — | — | — | — | — | 1483 / 137 |
| fastapi.tiangolo.com/advanced/custom-response | 1987 / 0 | 3447 / 1438 | 3457 / 1448 | 2782 / 779 | 3095 / 1025 | 3116 / 1008 | 3078 / 1008 | 1927 / 289 |
| fastapi.tiangolo.com/advanced/dataclasses | 778 / 0 | 2105 / 1286 | 2115 / 1296 | 1482 / 688 | 1811 / 924 | 1804 / 907 | 1794 / 907 | 769 / 769 |
| fastapi.tiangolo.com/advanced/events | — | — | — | — | — | — | — | 1468 / 543 |
| fastapi.tiangolo.com/advanced/extending-openapi | — | — | — | — | — | — | — | 736 / 263 |
| fastapi.tiangolo.com/advanced/generate-clients | — | — | — | — | — | — | — | 1620 / 350 |
| fastapi.tiangolo.com/advanced/graphql | — | — | — | — | — | — | — | 361 / 361 |
| fastapi.tiangolo.com/advanced/json-base64-bytes | — | — | — | — | — | — | — | 721 / 721 |
| fastapi.tiangolo.com/advanced/middleware | — | — | — | — | — | — | — | 578 / 578 |
| fastapi.tiangolo.com/advanced/openapi-callbacks | — | — | — | — | — | — | — | 1710 / 814 |
| fastapi.tiangolo.com/advanced/openapi-webhooks | — | — | — | — | — | — | — | 512 / 478 |
| fastapi.tiangolo.com/advanced/path-operation-advanced-c | — | — | — | — | — | — | — | 1293 / 72 |
| fastapi.tiangolo.com/advanced/response-change-status-co | — | — | — | — | — | — | — | 288 / 288 |
| fastapi.tiangolo.com/advanced/response-cookies | — | — | — | — | — | — | — | 369 / 290 |
| fastapi.tiangolo.com/advanced/response-directly | — | — | — | — | — | — | — | 723 / 723 |
| fastapi.tiangolo.com/advanced/response-headers | — | — | — | — | — | — | — | 345 / 345 |
| fastapi.tiangolo.com/advanced/security | — | — | — | — | — | — | — | 89 / 89 |
| fastapi.tiangolo.com/advanced/security/http-basic-auth | — | — | — | — | — | — | — | 1139 / 548 |
| fastapi.tiangolo.com/advanced/security/oauth2-scopes | — | — | — | — | — | — | — | 8934 / 8934 |
| fastapi.tiangolo.com/advanced/settings | — | — | — | — | — | — | — | 1994 / 173 |
| fastapi.tiangolo.com/advanced/sql-databases-peewee | — | — | — | — | — | — | — | 8 / 8 |
| fastapi.tiangolo.com/advanced/stream-data | — | — | — | — | — | — | — | 2672 / 544 |
| fastapi.tiangolo.com/advanced/strict-content-type | — | — | — | — | — | — | — | 505 / 505 |
| fastapi.tiangolo.com/advanced/sub-applications | — | — | — | — | — | — | — | 452 / 73 |
| fastapi.tiangolo.com/advanced/sub-applications-proxy | — | — | — | — | — | — | — | 8 / 8 |
| fastapi.tiangolo.com/advanced/templates | — | — | — | — | — | — | — | 527 / 309 |
| fastapi.tiangolo.com/advanced/testing-database | — | — | — | — | — | — | — | 46 / 46 |
| fastapi.tiangolo.com/advanced/testing-dependencies | — | — | — | — | — | — | — | 683 / 81 |
| fastapi.tiangolo.com/advanced/testing-events | — | — | — | — | — | — | — | 260 / 260 |
| fastapi.tiangolo.com/advanced/testing-websockets | — | — | — | — | — | — | — | 117 / 117 |
| fastapi.tiangolo.com/advanced/using-request-directly | — | — | — | — | — | — | — | 351 / 351 |
| fastapi.tiangolo.com/advanced/vibe | — | — | — | — | — | — | — | 380 / 380 |
| fastapi.tiangolo.com/advanced/websockets | — | — | — | — | — | — | — | 1619 / 48 |
| fastapi.tiangolo.com/advanced/wsgi | — | — | — | — | — | — | — | 240 / 240 |
| fastapi.tiangolo.com/alternatives | — | — | — | — | — | — | — | 3264 / 126 |
| fastapi.tiangolo.com/alternatives/?q= | — | — | — | — | — | — | — | 3264 / 126 |
| fastapi.tiangolo.com/async | — | — | — | — | — | — | — | 3641 / 694 |
| fastapi.tiangolo.com/benchmarks | 525 / 0 | 1817 / 1242 | 1831 / 1256 | 1202 / 661 | 1537 / 897 | 1522 / 878 | 1518 / 878 | 525 / 525 |
| fastapi.tiangolo.com/contributing | 1599 / 0 | 3113 / 1484 | 3116 / 1494 | 2438 / 823 | 2753 / 1061 | 2765 / 1044 | 2736 / 1044 | 1573 / 50 |
| fastapi.tiangolo.com/de | — | — | — | — | — | — | — | 2331 / 251 |
| fastapi.tiangolo.com/de/?q= | — | — | — | — | — | — | — | 2331 / 251 |
| fastapi.tiangolo.com/de/about | — | — | — | — | — | — | — | 62 / 62 |
| fastapi.tiangolo.com/de/about/?q= | — | — | — | — | — | — | — | 62 / 62 |
| fastapi.tiangolo.com/de/advanced | — | — | — | — | — | — | — | 150 / 150 |
| fastapi.tiangolo.com/de/advanced/additional-responses | — | — | — | — | — | — | — | 1230 / 1230 |
| fastapi.tiangolo.com/de/advanced/additional-status-code | — | — | — | — | — | — | — | 488 / 488 |
| fastapi.tiangolo.com/de/advanced/advanced-dependencies | — | — | — | — | — | — | — | 2108 / 897 |
| fastapi.tiangolo.com/de/advanced/advanced-python-types | — | — | — | — | — | — | — | 360 / 360 |
| fastapi.tiangolo.com/de/advanced/async-tests | — | — | — | — | — | — | — | 672 / 672 |
| fastapi.tiangolo.com/de/advanced/behind-a-proxy | — | — | — | — | — | — | — | 2062 / 178 |
| fastapi.tiangolo.com/de/advanced/custom-response | — | — | — | — | — | — | — | 1869 / 296 |
| fastapi.tiangolo.com/de/advanced/dataclasses | — | — | — | — | — | — | — | 773 / 773 |
| fastapi.tiangolo.com/de/advanced/events | — | — | — | — | — | — | — | 1441 / 580 |
| fastapi.tiangolo.com/de/advanced/generate-clients | — | — | — | — | — | — | — | 1559 / 383 |
| fastapi.tiangolo.com/de/advanced/json-base64-bytes | — | — | — | — | — | — | — | 742 / 742 |
| fastapi.tiangolo.com/de/advanced/middleware | — | — | — | — | — | — | — | 599 / 599 |
| fastapi.tiangolo.com/de/advanced/openapi-callbacks | — | — | — | — | — | — | — | 1692 / 823 |
| fastapi.tiangolo.com/de/advanced/openapi-webhooks | — | — | — | — | — | — | — | 527 / 494 |
| fastapi.tiangolo.com/de/advanced/path-operation-advance | — | — | — | — | — | — | — | 1247 / 113 |
| fastapi.tiangolo.com/de/advanced/response-change-status | — | — | — | — | — | — | — | 314 / 314 |
| fastapi.tiangolo.com/de/advanced/response-cookies | — | — | — | — | — | — | — | 397 / 318 |
| fastapi.tiangolo.com/de/advanced/response-directly | — | — | — | — | — | — | — | 735 / 735 |
| fastapi.tiangolo.com/de/advanced/response-headers | — | — | — | — | — | — | — | 377 / 377 |
| fastapi.tiangolo.com/de/advanced/security | — | — | — | — | — | — | — | 129 / 129 |
| fastapi.tiangolo.com/de/advanced/security/http-basic-au | — | — | — | — | — | — | — | 1193 / 599 |
| fastapi.tiangolo.com/de/advanced/security/oauth2-scopes | — | — | — | — | — | — | — | 8872 / 8872 |
| fastapi.tiangolo.com/de/advanced/settings | — | — | — | — | — | — | — | 1942 / 204 |
| fastapi.tiangolo.com/de/advanced/settings/?q= | — | — | — | — | — | — | — | 1942 / 204 |
| fastapi.tiangolo.com/de/advanced/stream-data | — | — | — | — | — | — | — | 2629 / 568 |
| fastapi.tiangolo.com/de/advanced/strict-content-type | — | — | — | — | — | — | — | 519 / 519 |
| fastapi.tiangolo.com/de/advanced/sub-applications | — | — | — | — | — | — | — | 470 / 115 |
| fastapi.tiangolo.com/de/advanced/templates | — | — | — | — | — | — | — | 555 / 354 |
| fastapi.tiangolo.com/de/advanced/testing-dependencies | — | — | — | — | — | — | — | 714 / 125 |
| fastapi.tiangolo.com/de/advanced/testing-events | — | — | — | — | — | — | — | 300 / 300 |
| fastapi.tiangolo.com/de/advanced/testing-websockets | — | — | — | — | — | — | — | 163 / 163 |
| fastapi.tiangolo.com/de/advanced/using-request-directly | — | — | — | — | — | — | — | 369 / 369 |
| fastapi.tiangolo.com/de/advanced/vibe | — | — | — | — | — | — | — | 415 / 415 |
| fastapi.tiangolo.com/de/advanced/websockets | — | — | — | — | — | — | — | 1652 / 89 |
| fastapi.tiangolo.com/de/advanced/wsgi | — | — | — | — | — | — | — | 277 / 277 |
| fastapi.tiangolo.com/de/alternatives | — | — | — | — | — | — | — | 3185 / 171 |
| fastapi.tiangolo.com/de/async | — | — | — | — | — | — | — | 3599 / 729 |
| fastapi.tiangolo.com/de/async/?q= | — | — | — | — | — | — | — | 3599 / 729 |
| fastapi.tiangolo.com/de/benchmarks | — | — | — | — | — | — | — | 562 / 562 |
| fastapi.tiangolo.com/de/contributing | — | — | — | — | — | — | — | 1613 / 85 |
| fastapi.tiangolo.com/de/deployment | — | — | — | — | — | — | — | 268 / 268 |
| fastapi.tiangolo.com/de/deployment/cloud | — | — | — | — | — | — | — | 174 / 174 |
| fastapi.tiangolo.com/de/deployment/concepts | — | — | — | — | — | — | — | 2860 / 313 |
| fastapi.tiangolo.com/de/deployment/docker | — | — | — | — | — | — | — | 3589 / 836 |
| fastapi.tiangolo.com/de/deployment/fastapicloud | — | — | — | — | — | — | — | 317 / 317 |
| fastapi.tiangolo.com/de/deployment/https | — | — | — | — | — | — | — | 1892 / 613 |
| fastapi.tiangolo.com/de/deployment/manually | — | — | — | — | — | — | — | 678 / 678 |
| fastapi.tiangolo.com/de/deployment/server-workers | — | — | — | — | — | — | — | 691 / 691 |
| fastapi.tiangolo.com/de/deployment/versions | — | — | — | — | — | — | — | 544 / 544 |
| fastapi.tiangolo.com/de/editor-support | — | — | — | — | — | — | — | 331 / 127 |
| fastapi.tiangolo.com/de/environment-variables | — | — | — | — | — | — | — | 1043 / 757 |
| fastapi.tiangolo.com/de/environment-variables/?q= | — | — | — | — | — | — | — | 1043 / 757 |
| fastapi.tiangolo.com/de/external-links | — | — | — | — | — | — | — | 797 / 797 |
| fastapi.tiangolo.com/de/fastapi-cli | — | — | — | — | — | — | — | 493 / 250 |
| fastapi.tiangolo.com/de/fastapi-people | — | — | — | — | — | — | — | 2188 / 285 |
| fastapi.tiangolo.com/de/fastapi-people/?q= | — | — | — | — | — | — | — | 2188 / 285 |
| fastapi.tiangolo.com/de/features | — | — | — | — | — | — | — | 1129 / 57 |
| fastapi.tiangolo.com/de/features/?q= | — | — | — | — | — | — | — | 1129 / 57 |
| fastapi.tiangolo.com/de/help-fastapi | — | — | — | — | — | — | — | 1982 / 600 |
| fastapi.tiangolo.com/de/history-design-future | — | — | — | — | — | — | — | 644 / 644 |
| fastapi.tiangolo.com/de/how-to | — | — | — | — | — | — | — | 128 / 128 |
| fastapi.tiangolo.com/de/how-to/authentication-error-sta | — | — | — | — | — | — | — | 215 / 215 |
| fastapi.tiangolo.com/de/how-to/conditional-openapi | — | — | — | — | — | — | — | 415 / 415 |
| fastapi.tiangolo.com/de/how-to/configure-swagger-ui | — | — | — | — | — | — | — | 1609 / 1609 |
| fastapi.tiangolo.com/de/how-to/custom-docs-ui-assets | — | — | — | — | — | — | — | 1503 / 132 |
| fastapi.tiangolo.com/de/how-to/custom-request-and-route | — | — | — | — | — | — | — | 1477 / 167 |
| fastapi.tiangolo.com/de/how-to/extending-openapi | — | — | — | — | — | — | — | 755 / 293 |
| fastapi.tiangolo.com/de/how-to/general | — | — | — | — | — | — | — | 392 / 392 |
| fastapi.tiangolo.com/de/how-to/graphql | — | — | — | — | — | — | — | 386 / 386 |
| fastapi.tiangolo.com/de/how-to/migrate-from-pydantic-v1 | — | — | — | — | — | — | — | 852 / 420 |
| fastapi.tiangolo.com/de/how-to/separate-openapi-schemas | — | — | — | — | — | — | — | 858 / 207 |
| fastapi.tiangolo.com/de/how-to/testing-database | — | — | — | — | — | — | — | 93 / 93 |
| fastapi.tiangolo.com/de/learn | — | — | — | — | — | — | — | 82 / 82 |
| fastapi.tiangolo.com/de/learn/?q= | — | — | — | — | — | — | — | 82 / 82 |
| fastapi.tiangolo.com/de/management | — | — | — | — | — | — | — | 213 / 213 |
| fastapi.tiangolo.com/de/management-tasks | — | — | — | — | — | — | — | 1786 / 141 |
| fastapi.tiangolo.com/de/newsletter | — | — | — | — | — | — | — | 10 / 10 |
| fastapi.tiangolo.com/de/project-generation | — | — | — | — | — | — | — | 278 / 278 |
| fastapi.tiangolo.com/de/python-types | — | — | — | — | — | — | — | 1840 / 260 |
| fastapi.tiangolo.com/de/python-types/?q= | — | — | — | — | — | — | — | 1840 / 260 |
| fastapi.tiangolo.com/de/reference | — | — | — | — | — | — | — | 45 / 45 |
| fastapi.tiangolo.com/de/reference/?q= | — | — | — | — | — | — | — | 45 / 45 |
| fastapi.tiangolo.com/de/reference/apirouter | — | — | — | — | — | — | — | 24492 / 120 |
| fastapi.tiangolo.com/de/reference/background | — | — | — | — | — | — | — | 351 / 91 |
| fastapi.tiangolo.com/de/reference/dependencies | — | — | — | — | — | — | — | 1479 / 1479 |
| fastapi.tiangolo.com/de/reference/encoders | — | — | — | — | — | — | — | 1104 / 1104 |
| fastapi.tiangolo.com/de/reference/exceptions | — | — | — | — | — | — | — | 710 / 138 |
| fastapi.tiangolo.com/de/reference/fastapi | — | — | — | — | — | — | — | 28965 / 110 |
| fastapi.tiangolo.com/de/reference/httpconnection | — | — | — | — | — | — | — | 256 / 103 |
| fastapi.tiangolo.com/de/reference/middleware | — | — | — | — | — | — | — | 949 / 233 |
| fastapi.tiangolo.com/de/reference/openapi | — | — | — | — | — | — | — | 32 / 32 |
| fastapi.tiangolo.com/de/reference/openapi/docs | — | — | — | — | — | — | — | 1716 / 1716 |
| fastapi.tiangolo.com/de/reference/openapi/models | — | — | — | — | — | — | — | 3638 / 21 |
| fastapi.tiangolo.com/de/reference/parameters | — | — | — | — | — | — | — | 12209 / 12209 |
| fastapi.tiangolo.com/de/reference/request | — | — | — | — | — | — | — | 622 / 147 |
| fastapi.tiangolo.com/de/reference/response | — | — | — | — | — | — | — | 617 / 145 |
| fastapi.tiangolo.com/de/reference/responses | — | — | — | — | — | — | — | 5296 / 294 |
| fastapi.tiangolo.com/de/reference/security | — | — | — | — | — | — | — | 8598 / 190 |
| fastapi.tiangolo.com/de/reference/staticfiles | — | — | — | — | — | — | — | 942 / 131 |
| fastapi.tiangolo.com/de/reference/status | — | — | — | — | — | — | — | 835 / 126 |
| fastapi.tiangolo.com/de/reference/templating | — | — | — | — | — | — | — | 628 / 222 |
| fastapi.tiangolo.com/de/reference/testclient | — | — | — | — | — | — | — | 2068 / 192 |
| fastapi.tiangolo.com/de/reference/uploadfile | — | — | — | — | — | — | — | 675 / 105 |
| fastapi.tiangolo.com/de/reference/websockets | — | — | — | — | — | — | — | 1211 / 140 |
| fastapi.tiangolo.com/de/release-notes | — | — | — | — | — | — | — | 54501 / 8 |
| fastapi.tiangolo.com/de/release-notes/?q= | — | — | — | — | — | — | — | 54501 / 8 |
| fastapi.tiangolo.com/de/resources | — | — | — | — | — | — | — | 60 / 60 |
| fastapi.tiangolo.com/de/resources/?q= | — | — | — | — | — | — | — | 60 / 60 |
| fastapi.tiangolo.com/de/tutorial | — | — | — | — | — | — | — | 537 / 537 |
| fastapi.tiangolo.com/de/tutorial/?q= | — | — | — | — | — | — | — | 537 / 537 |
| fastapi.tiangolo.com/de/tutorial/background-tasks | — | — | — | — | — | — | — | 951 / 951 |
| fastapi.tiangolo.com/de/tutorial/bigger-applications | — | — | — | — | — | — | — | 3232 / 500 |
| fastapi.tiangolo.com/de/tutorial/body | — | — | — | — | — | — | — | 1150 / 1150 |
| fastapi.tiangolo.com/de/tutorial/body-fields | — | — | — | — | — | — | — | 659 / 659 |
| fastapi.tiangolo.com/de/tutorial/body-fields/?q= | — | — | — | — | — | — | — | 659 / 659 |
| fastapi.tiangolo.com/de/tutorial/body-multiple-params | — | — | — | — | — | — | — | 1353 / 1353 |
| fastapi.tiangolo.com/de/tutorial/body-multiple-params/? | — | — | — | — | — | — | — | 1353 / 1353 |
| fastapi.tiangolo.com/de/tutorial/body-nested-models | — | — | — | — | — | — | — | 1384 / 170 |
| fastapi.tiangolo.com/de/tutorial/body-nested-models/?q= | — | — | — | — | — | — | — | 1384 / 170 |
| fastapi.tiangolo.com/de/tutorial/body-updates | — | — | — | — | — | — | — | 1022 / 215 |
| fastapi.tiangolo.com/de/tutorial/body-updates/?q= | — | — | — | — | — | — | — | 1022 / 215 |
| fastapi.tiangolo.com/de/tutorial/body/?q= | — | — | — | — | — | — | — | 1150 / 1150 |
| fastapi.tiangolo.com/de/tutorial/cookie-param-models | — | — | — | — | — | — | — | 592 / 592 |
| fastapi.tiangolo.com/de/tutorial/cookie-param-models/?q | — | — | — | — | — | — | — | 592 / 592 |
| fastapi.tiangolo.com/de/tutorial/cookie-params | — | — | — | — | — | — | — | 379 / 379 |
| fastapi.tiangolo.com/de/tutorial/cookie-params/?q= | — | — | — | — | — | — | — | 379 / 379 |
| fastapi.tiangolo.com/de/tutorial/cors | — | — | — | — | — | — | — | 730 / 621 |
| fastapi.tiangolo.com/de/tutorial/debugging | — | — | — | — | — | — | — | 416 / 112 |
| fastapi.tiangolo.com/de/tutorial/dependencies | — | — | — | — | — | — | — | 1642 / 223 |
| fastapi.tiangolo.com/de/tutorial/dependencies/?q= | — | — | — | — | — | — | — | 1642 / 223 |
| fastapi.tiangolo.com/de/tutorial/dependencies/classes-a | — | — | — | — | — | — | — | 1940 / 1940 |
| fastapi.tiangolo.com/de/tutorial/dependencies/classes-a | — | — | — | — | — | — | — | 1940 / 1940 |
| fastapi.tiangolo.com/de/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 895 / 378 |
| fastapi.tiangolo.com/de/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 895 / 378 |
| fastapi.tiangolo.com/de/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 2210 / 1245 |
| fastapi.tiangolo.com/de/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 2210 / 1245 |
| fastapi.tiangolo.com/de/tutorial/dependencies/global-de | — | — | — | — | — | — | — | 303 / 303 |
| fastapi.tiangolo.com/de/tutorial/dependencies/global-de | — | — | — | — | — | — | — | 303 / 303 |
| fastapi.tiangolo.com/de/tutorial/dependencies/sub-depen | — | — | — | — | — | — | — | 850 / 850 |
| fastapi.tiangolo.com/de/tutorial/dependencies/sub-depen | — | — | — | — | — | — | — | 850 / 850 |
| fastapi.tiangolo.com/de/tutorial/encoder | — | — | — | — | — | — | — | 308 / 308 |
| fastapi.tiangolo.com/de/tutorial/encoder/?q= | — | — | — | — | — | — | — | 308 / 308 |
| fastapi.tiangolo.com/de/tutorial/extra-data-types | — | — | — | — | — | — | — | 711 / 711 |
| fastapi.tiangolo.com/de/tutorial/extra-data-types/?q= | — | — | — | — | — | — | — | 711 / 711 |
| fastapi.tiangolo.com/de/tutorial/extra-models | — | — | — | — | — | — | — | 1158 / 243 |
| fastapi.tiangolo.com/de/tutorial/extra-models/?q= | — | — | — | — | — | — | — | 1158 / 243 |
| fastapi.tiangolo.com/de/tutorial/first-steps | — | — | — | — | — | — | — | 1555 / 128 |
| fastapi.tiangolo.com/de/tutorial/first-steps/?q= | — | — | — | — | — | — | — | 1555 / 128 |
| fastapi.tiangolo.com/de/tutorial/handling-errors | — | — | — | — | — | — | — | 1622 / 206 |
| fastapi.tiangolo.com/de/tutorial/handling-errors/?q= | — | — | — | — | — | — | — | 1622 / 206 |
| fastapi.tiangolo.com/de/tutorial/header-param-models | — | — | — | — | — | — | — | 689 / 689 |
| fastapi.tiangolo.com/de/tutorial/header-param-models/?q | — | — | — | — | — | — | — | 689 / 689 |
| fastapi.tiangolo.com/de/tutorial/header-params | — | — | — | — | — | — | — | 693 / 693 |
| fastapi.tiangolo.com/de/tutorial/header-params/?q= | — | — | — | — | — | — | — | 693 / 693 |
| fastapi.tiangolo.com/de/tutorial/metadata | — | — | — | — | — | — | — | 1085 / 628 |
| fastapi.tiangolo.com/de/tutorial/middleware | — | — | — | — | — | — | — | 618 / 376 |
| fastapi.tiangolo.com/de/tutorial/middleware/?q= | — | — | — | — | — | — | — | 618 / 376 |
| fastapi.tiangolo.com/de/tutorial/path-operation-configu | — | — | — | — | — | — | — | 884 / 306 |
| fastapi.tiangolo.com/de/tutorial/path-operation-configu | — | — | — | — | — | — | — | 884 / 306 |
| fastapi.tiangolo.com/de/tutorial/path-params | — | — | — | — | — | — | — | 1421 / 654 |
| fastapi.tiangolo.com/de/tutorial/path-params-numeric-va | — | — | — | — | — | — | — | 1699 / 937 |
| fastapi.tiangolo.com/de/tutorial/path-params-numeric-va | — | — | — | — | — | — | — | 1699 / 937 |
| fastapi.tiangolo.com/de/tutorial/path-params/?q= | — | — | — | — | — | — | — | 1421 / 654 |
| fastapi.tiangolo.com/de/tutorial/query-param-models | — | — | — | — | — | — | — | 533 / 533 |
| fastapi.tiangolo.com/de/tutorial/query-param-models/?q= | — | — | — | — | — | — | — | 533 / 533 |
| fastapi.tiangolo.com/de/tutorial/query-params | — | — | — | — | — | — | — | 815 / 815 |
| fastapi.tiangolo.com/de/tutorial/query-params-str-valid | — | — | — | — | — | — | — | 3890 / 194 |
| fastapi.tiangolo.com/de/tutorial/query-params-str-valid | — | — | — | — | — | — | — | 3890 / 194 |
| fastapi.tiangolo.com/de/tutorial/query-params/?q= | — | — | — | — | — | — | — | 815 / 815 |
| fastapi.tiangolo.com/de/tutorial/request-files | — | — | — | — | — | — | — | 1741 / 599 |
| fastapi.tiangolo.com/de/tutorial/request-files/?q= | — | — | — | — | — | — | — | 1741 / 599 |
| fastapi.tiangolo.com/de/tutorial/request-form-models | — | — | — | — | — | — | — | 461 / 461 |
| fastapi.tiangolo.com/de/tutorial/request-form-models/?q | — | — | — | — | — | — | — | 461 / 461 |
| fastapi.tiangolo.com/de/tutorial/request-forms | — | — | — | — | — | — | — | 491 / 491 |
| fastapi.tiangolo.com/de/tutorial/request-forms-and-file | — | — | — | — | — | — | — | 406 / 406 |
| fastapi.tiangolo.com/de/tutorial/request-forms-and-file | — | — | — | — | — | — | — | 406 / 406 |
| fastapi.tiangolo.com/de/tutorial/request-forms/?q= | — | — | — | — | — | — | — | 491 / 491 |
| fastapi.tiangolo.com/de/tutorial/response-model | — | — | — | — | — | — | — | 2918 / 611 |
| fastapi.tiangolo.com/de/tutorial/response-model/?q= | — | — | — | — | — | — | — | 2918 / 611 |
| fastapi.tiangolo.com/de/tutorial/response-status-code | — | — | — | — | — | — | — | 630 / 630 |
| fastapi.tiangolo.com/de/tutorial/response-status-code/? | — | — | — | — | — | — | — | 630 / 630 |
| fastapi.tiangolo.com/de/tutorial/schema-extra-example | — | — | — | — | — | — | — | 1940 / 420 |
| fastapi.tiangolo.com/de/tutorial/schema-extra-example/? | — | — | — | — | — | — | — | 1940 / 420 |
| fastapi.tiangolo.com/de/tutorial/security | — | — | — | — | — | — | — | 701 / 219 |
| fastapi.tiangolo.com/de/tutorial/security/?q= | — | — | — | — | — | — | — | 701 / 219 |
| fastapi.tiangolo.com/de/tutorial/security/first-steps | — | — | — | — | — | — | — | 1497 / 1203 |
| fastapi.tiangolo.com/de/tutorial/security/first-steps/? | — | — | — | — | — | — | — | 1497 / 1203 |
| fastapi.tiangolo.com/de/tutorial/security/get-current-u | — | — | — | — | — | — | — | 1509 / 1509 |
| fastapi.tiangolo.com/de/tutorial/security/get-current-u | — | — | — | — | — | — | — | 1509 / 1509 |
| fastapi.tiangolo.com/de/tutorial/security/oauth2-jwt | — | — | — | — | — | — | — | 4388 / 391 |
| fastapi.tiangolo.com/de/tutorial/security/oauth2-jwt/?q | — | — | — | — | — | — | — | 4388 / 391 |
| fastapi.tiangolo.com/de/tutorial/security/simple-oauth2 | — | — | — | — | — | — | — | 3511 / 196 |
| fastapi.tiangolo.com/de/tutorial/security/simple-oauth2 | — | — | — | — | — | — | — | 3511 / 196 |
| fastapi.tiangolo.com/de/tutorial/server-sent-events | — | — | — | — | — | — | — | 1421 / 617 |
| fastapi.tiangolo.com/de/tutorial/sql-databases | — | — | — | — | — | — | — | 10366 / 321 |
| fastapi.tiangolo.com/de/tutorial/static-files | — | — | — | — | — | — | — | 284 / 125 |
| fastapi.tiangolo.com/de/tutorial/stream-json-lines | — | — | — | — | — | — | — | 1159 / 802 |
| fastapi.tiangolo.com/de/tutorial/testing | — | — | — | — | — | — | — | 1480 / 338 |
| fastapi.tiangolo.com/de/virtual-environments | — | — | — | — | — | — | — | 2902 / 1069 |
| fastapi.tiangolo.com/de/virtual-environments/?q= | — | — | — | — | — | — | — | 2902 / 1069 |
| fastapi.tiangolo.com/deployment | — | — | — | — | — | — | — | 238 / 238 |
| fastapi.tiangolo.com/deployment/cloud | — | — | — | — | — | — | — | 140 / 140 |
| fastapi.tiangolo.com/deployment/concepts | — | — | — | — | — | — | — | 3021 / 279 |
| fastapi.tiangolo.com/deployment/docker | — | — | — | — | — | — | — | 3709 / 818 |
| fastapi.tiangolo.com/deployment/fastapicloud | — | — | — | — | — | — | — | 282 / 282 |
| fastapi.tiangolo.com/deployment/https | — | — | — | — | — | — | — | 2079 / 627 |
| fastapi.tiangolo.com/deployment/manually | — | — | — | — | — | — | — | 667 / 667 |
| fastapi.tiangolo.com/deployment/server-workers | — | — | — | — | — | — | — | 677 / 677 |
| fastapi.tiangolo.com/deployment/versions | 537 / 0 | 1874 / 1306 | 1886 / 1318 | 1254 / 701 | 1580 / 941 | 1575 / 922 | 1561 / 922 | 519 / 519 |
| fastapi.tiangolo.com/editor-support | — | — | — | — | — | — | — | 309 / 98 |
| fastapi.tiangolo.com/environment-variables | 1134 / 0 | 2524 / 1316 | 2449 / 1326 | 1862 / 712 | 2152 / 950 | 2185 / 931 | 2120 / 931 | 1058 / 741 |
| fastapi.tiangolo.com/es | — | — | — | — | — | — | — | 2504 / 263 |
| fastapi.tiangolo.com/es/?q= | — | — | — | — | — | — | — | 2504 / 263 |
| fastapi.tiangolo.com/es/about | — | — | — | — | — | — | — | 64 / 64 |
| fastapi.tiangolo.com/es/advanced | — | — | — | — | — | — | — | 156 / 156 |
| fastapi.tiangolo.com/es/advanced/additional-responses | — | — | — | — | — | — | — | 1299 / 1299 |
| fastapi.tiangolo.com/es/advanced/additional-status-code | — | — | — | — | — | — | — | 496 / 496 |
| fastapi.tiangolo.com/es/advanced/advanced-dependencies | — | — | — | — | — | — | — | 2261 / 900 |
| fastapi.tiangolo.com/es/advanced/advanced-python-types | — | — | — | — | — | — | — | 367 / 367 |
| fastapi.tiangolo.com/es/advanced/async-tests | — | — | — | — | — | — | — | 685 / 685 |
| fastapi.tiangolo.com/es/advanced/behind-a-proxy | — | — | — | — | — | — | — | 2155 / 189 |
| fastapi.tiangolo.com/es/advanced/custom-response | — | — | — | — | — | — | — | 1925 / 319 |
| fastapi.tiangolo.com/es/advanced/dataclasses | — | — | — | — | — | — | — | 832 / 832 |
| fastapi.tiangolo.com/es/advanced/events | — | — | — | — | — | — | — | 1526 / 583 |
| fastapi.tiangolo.com/es/advanced/generate-clients | — | — | — | — | — | — | — | 1694 / 417 |
| fastapi.tiangolo.com/es/advanced/json-base64-bytes | — | — | — | — | — | — | — | 753 / 753 |
| fastapi.tiangolo.com/es/advanced/middleware | — | — | — | — | — | — | — | 635 / 635 |
| fastapi.tiangolo.com/es/advanced/openapi-callbacks | — | — | — | — | — | — | — | 1732 / 832 |
| fastapi.tiangolo.com/es/advanced/openapi-webhooks | — | — | — | — | — | — | — | 551 / 519 |
| fastapi.tiangolo.com/es/advanced/path-operation-advance | — | — | — | — | — | — | — | 1324 / 115 |
| fastapi.tiangolo.com/es/advanced/response-change-status | — | — | — | — | — | — | — | 318 / 318 |
| fastapi.tiangolo.com/es/advanced/response-cookies | — | — | — | — | — | — | — | 410 / 331 |
| fastapi.tiangolo.com/es/advanced/response-directly | — | — | — | — | — | — | — | 750 / 750 |
| fastapi.tiangolo.com/es/advanced/response-headers | — | — | — | — | — | — | — | 382 / 382 |
| fastapi.tiangolo.com/es/advanced/security | — | — | — | — | — | — | — | 135 / 135 |
| fastapi.tiangolo.com/es/advanced/security/http-basic-au | — | — | — | — | — | — | — | 1197 / 598 |
| fastapi.tiangolo.com/es/advanced/security/oauth2-scopes | — | — | — | — | — | — | — | 8934 / 8934 |
| fastapi.tiangolo.com/es/advanced/settings | — | — | — | — | — | — | — | 2035 / 233 |
| fastapi.tiangolo.com/es/advanced/stream-data | — | — | — | — | — | — | — | 2687 / 573 |
| fastapi.tiangolo.com/es/advanced/strict-content-type | — | — | — | — | — | — | — | 553 / 553 |
| fastapi.tiangolo.com/es/advanced/sub-applications | — | — | — | — | — | — | — | 496 / 120 |
| fastapi.tiangolo.com/es/advanced/templates | — | — | — | — | — | — | — | 560 / 351 |
| fastapi.tiangolo.com/es/advanced/testing-dependencies | — | — | — | — | — | — | — | 713 / 125 |
| fastapi.tiangolo.com/es/advanced/testing-events | — | — | — | — | — | — | — | 304 / 304 |
| fastapi.tiangolo.com/es/advanced/testing-websockets | — | — | — | — | — | — | — | 162 / 162 |
| fastapi.tiangolo.com/es/advanced/using-request-directly | — | — | — | — | — | — | — | 380 / 380 |
| fastapi.tiangolo.com/es/advanced/vibe | — | — | — | — | — | — | — | 416 / 416 |
| fastapi.tiangolo.com/es/advanced/websockets | — | — | — | — | — | — | — | 1648 / 89 |
| fastapi.tiangolo.com/es/advanced/wsgi | — | — | — | — | — | — | — | 270 / 270 |
| fastapi.tiangolo.com/es/async | — | — | — | — | — | — | — | 3629 / 751 |
| fastapi.tiangolo.com/es/deployment | — | — | — | — | — | — | — | 278 / 278 |
| fastapi.tiangolo.com/es/editor-support | — | — | — | — | — | — | — | 405 / 154 |
| fastapi.tiangolo.com/es/environment-variables | — | — | — | — | — | — | — | 1102 / 806 |
| fastapi.tiangolo.com/es/fastapi-cli | — | — | — | — | — | — | — | 516 / 260 |
| fastapi.tiangolo.com/es/fastapi-people | — | — | — | — | — | — | — | 2189 / 286 |
| fastapi.tiangolo.com/es/features | — | — | — | — | — | — | — | 1294 / 60 |
| fastapi.tiangolo.com/es/learn | — | — | — | — | — | — | — | 81 / 81 |
| fastapi.tiangolo.com/es/python-types | — | — | — | — | — | — | — | 1843 / 259 |
| fastapi.tiangolo.com/es/reference | — | — | — | — | — | — | — | 46 / 46 |
| fastapi.tiangolo.com/es/release-notes | — | — | — | — | — | — | — | 54502 / 9 |
| fastapi.tiangolo.com/es/resources | — | — | — | — | — | — | — | 61 / 61 |
| fastapi.tiangolo.com/es/tutorial | — | — | — | — | — | — | — | 550 / 550 |
| fastapi.tiangolo.com/es/tutorial/background-tasks | — | — | — | — | — | — | — | 1013 / 1013 |
| fastapi.tiangolo.com/es/tutorial/bigger-applications | — | — | — | — | — | — | — | 3216 / 518 |
| fastapi.tiangolo.com/es/tutorial/body | — | — | — | — | — | — | — | 1252 / 1252 |
| fastapi.tiangolo.com/es/tutorial/body-fields | — | — | — | — | — | — | — | 704 / 704 |
| fastapi.tiangolo.com/es/tutorial/body-multiple-params | — | — | — | — | — | — | — | 1403 / 1403 |
| fastapi.tiangolo.com/es/tutorial/body-nested-models | — | — | — | — | — | — | — | 1456 / 180 |
| fastapi.tiangolo.com/es/tutorial/body-updates | — | — | — | — | — | — | — | 1039 / 213 |
| fastapi.tiangolo.com/es/tutorial/cookie-param-models | — | — | — | — | — | — | — | 622 / 622 |
| fastapi.tiangolo.com/es/tutorial/cookie-params | — | — | — | — | — | — | — | 403 / 403 |
| fastapi.tiangolo.com/es/tutorial/cors | — | — | — | — | — | — | — | 794 / 671 |
| fastapi.tiangolo.com/es/tutorial/debugging | — | — | — | — | — | — | — | 423 / 113 |
| fastapi.tiangolo.com/es/tutorial/dependencies | — | — | — | — | — | — | — | 1764 / 231 |
| fastapi.tiangolo.com/es/tutorial/dependencies/classes-a | — | — | — | — | — | — | — | 1970 / 1970 |
| fastapi.tiangolo.com/es/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 922 / 400 |
| fastapi.tiangolo.com/es/tutorial/dependencies/dependenc | — | — | — | — | — | — | — | 2311 / 1299 |
| fastapi.tiangolo.com/es/tutorial/dependencies/global-de | — | — | — | — | — | — | — | 317 / 317 |
| fastapi.tiangolo.com/es/tutorial/dependencies/sub-depen | — | — | — | — | — | — | — | 846 / 846 |
| fastapi.tiangolo.com/es/tutorial/encoder | — | — | — | — | — | — | — | 331 / 331 |
| fastapi.tiangolo.com/es/tutorial/extra-data-types | — | — | — | — | — | — | — | 759 / 759 |
| fastapi.tiangolo.com/es/tutorial/extra-models | — | — | — | — | — | — | — | 1204 / 257 |
| fastapi.tiangolo.com/es/tutorial/first-steps | — | — | — | — | — | — | — | 1589 / 127 |
| fastapi.tiangolo.com/es/tutorial/handling-errors | — | — | — | — | — | — | — | 1701 / 217 |
| fastapi.tiangolo.com/es/tutorial/header-param-models | — | — | — | — | — | — | — | 723 / 723 |
| fastapi.tiangolo.com/es/tutorial/header-params | — | — | — | — | — | — | — | 734 / 734 |
| fastapi.tiangolo.com/es/tutorial/metadata | — | — | — | — | — | — | — | 1123 / 669 |
| fastapi.tiangolo.com/es/tutorial/middleware | — | — | — | — | — | — | — | 640 / 382 |
| fastapi.tiangolo.com/es/tutorial/path-operation-configu | — | — | — | — | — | — | — | 903 / 323 |
| fastapi.tiangolo.com/es/tutorial/path-params | — | — | — | — | — | — | — | 1547 / 736 |
| fastapi.tiangolo.com/es/tutorial/path-params-numeric-va | — | — | — | — | — | — | — | 1711 / 963 |
| fastapi.tiangolo.com/es/tutorial/query-param-models | — | — | — | — | — | — | — | 561 / 561 |
| fastapi.tiangolo.com/es/tutorial/query-params | — | — | — | — | — | — | — | 878 / 878 |
| fastapi.tiangolo.com/es/tutorial/query-params-str-valid | — | — | — | — | — | — | — | 3981 / 201 |
| fastapi.tiangolo.com/es/tutorial/request-files | — | — | — | — | — | — | — | 1783 / 603 |
| fastapi.tiangolo.com/es/tutorial/request-form-models | — | — | — | — | — | — | — | 477 / 477 |
| fastapi.tiangolo.com/es/tutorial/request-forms | — | — | — | — | — | — | — | 528 / 528 |
| fastapi.tiangolo.com/es/tutorial/request-forms-and-file | — | — | — | — | — | — | — | 414 / 414 |
| fastapi.tiangolo.com/es/tutorial/response-model | — | — | — | — | — | — | — | 3224 / 693 |
| fastapi.tiangolo.com/es/tutorial/response-status-code | — | — | — | — | — | — | — | 685 / 685 |
| fastapi.tiangolo.com/es/tutorial/schema-extra-example | — | — | — | — | — | — | — | 2040 / 451 |
| fastapi.tiangolo.com/es/tutorial/security | — | — | — | — | — | — | — | 727 / 222 |
| fastapi.tiangolo.com/es/tutorial/security/first-steps | — | — | — | — | — | — | — | 1510 / 1199 |
| fastapi.tiangolo.com/es/tutorial/security/get-current-u | — | — | — | — | — | — | — | 1565 / 1565 |
| fastapi.tiangolo.com/es/tutorial/security/oauth2-jwt | — | — | — | — | — | — | — | 4444 / 400 |
| fastapi.tiangolo.com/es/tutorial/security/simple-oauth2 | — | — | — | — | — | — | — | 3595 / 221 |
| fastapi.tiangolo.com/es/tutorial/server-sent-events | — | — | — | — | — | — | — | 1470 / 635 |
| fastapi.tiangolo.com/es/tutorial/sql-databases | — | — | — | — | — | — | — | 10528 / 337 |
| fastapi.tiangolo.com/es/tutorial/static-files | — | — | — | — | — | — | — | 287 / 125 |
| fastapi.tiangolo.com/es/tutorial/stream-json-lines | — | — | — | — | — | — | — | 1165 / 800 |
| fastapi.tiangolo.com/es/tutorial/testing | — | — | — | — | — | — | — | 1494 / 343 |
| fastapi.tiangolo.com/es/virtual-environments | — | — | — | — | — | — | — | 2812 / 1030 |
| fastapi.tiangolo.com/external-links | — | — | — | — | — | — | — | 798 / 798 |
| fastapi.tiangolo.com/fastapi-cli | — | — | — | — | — | — | — | 472 / 210 |
| fastapi.tiangolo.com/fastapi-people | — | — | — | — | — | — | — | 2189 / 286 |
| fastapi.tiangolo.com/features | 1154 / 0 | 2559 / 1356 | 2569 / 1366 | 1899 / 729 | 2204 / 963 | 2215 / 946 | 2187 / 946 | 1143 / 13 |
| fastapi.tiangolo.com/fr | — | — | — | — | — | — | — | 2697 / 301 |
| fastapi.tiangolo.com/help-fastapi | — | — | — | — | — | — | — | 1928 / 578 |
| fastapi.tiangolo.com/history-design-future | — | — | — | — | — | — | — | 612 / 612 |
| fastapi.tiangolo.com/how-to | — | — | — | — | — | — | — | 98 / 98 |
| fastapi.tiangolo.com/how-to/authentication-error-status | — | — | — | — | — | — | — | 195 / 195 |
| fastapi.tiangolo.com/how-to/conditional-openapi | — | — | — | — | — | — | — | 376 / 376 |
| fastapi.tiangolo.com/how-to/configure-swagger-ui | — | — | — | — | — | — | — | 1566 / 1566 |
| fastapi.tiangolo.com/how-to/custom-docs-ui-assets | — | — | — | — | — | — | — | 1486 / 94 |
| fastapi.tiangolo.com/how-to/custom-request-and-route | 1510 / 0 | 2886 / 1345 | 2896 / 1355 | 2262 / 736 | 2592 / 980 | 2587 / 961 | 2573 / 961 | 1483 / 137 |
| fastapi.tiangolo.com/how-to/extending-openapi | — | — | — | — | — | — | — | 736 / 263 |
| fastapi.tiangolo.com/how-to/general | — | — | — | — | — | — | — | 344 / 344 |
| fastapi.tiangolo.com/how-to/graphql | 364 / 0 | 1695 / 1285 | 1705 / 1295 | 1068 / 688 | 1401 / 922 | 1394 / 905 | 1384 / 905 | 361 / 361 |
| fastapi.tiangolo.com/how-to/migrate-from-pydantic-v1-to | — | — | — | — | — | — | — | 844 / 394 |
| fastapi.tiangolo.com/how-to/separate-openapi-schemas | — | — | — | — | — | — | — | 863 / 174 |
| fastapi.tiangolo.com/how-to/testing-database | — | — | — | — | — | — | — | 46 / 46 |
| fastapi.tiangolo.com/ja | — | — | — | — | — | — | — | 1308 / 95 |
| fastapi.tiangolo.com/ko | — | — | — | — | — | — | — | 2003 / 202 |
| fastapi.tiangolo.com/learn | — | — | — | — | — | — | — | 36 / 36 |
| fastapi.tiangolo.com/management | — | — | — | — | — | — | — | 214 / 214 |
| fastapi.tiangolo.com/management-tasks | — | — | — | — | — | — | — | 1787 / 142 |
| fastapi.tiangolo.com/newsletter | — | — | — | — | — | — | — | 11 / 11 |
| fastapi.tiangolo.com/project-generation | — | — | — | — | — | — | — | 254 / 254 |
| fastapi.tiangolo.com/pt | — | — | — | — | — | — | — | 2504 / 260 |
| fastapi.tiangolo.com/pt/alternatives | — | — | — | — | — | — | — | 3483 / 173 |
| fastapi.tiangolo.com/pt/benchmarks | — | — | — | — | — | — | — | 591 / 591 |
| fastapi.tiangolo.com/pt/features | — | — | — | — | — | — | — | 1301 / 63 |
| fastapi.tiangolo.com/pt/history-design-future | — | — | — | — | — | — | — | 667 / 667 |
| fastapi.tiangolo.com/pt/tutorial | — | — | — | — | — | — | — | 568 / 568 |
| fastapi.tiangolo.com/python-types | — | — | — | — | — | — | — | 1829 / 209 |
| fastapi.tiangolo.com/reference | — | — | — | — | — | — | — | 46 / 46 |
| fastapi.tiangolo.com/reference/apirouter | — | — | — | — | — | — | — | 24493 / 121 |
| fastapi.tiangolo.com/reference/background | — | — | — | — | — | — | — | 352 / 92 |
| fastapi.tiangolo.com/reference/dependencies | 1517 / 0 | 2825 / 1266 | 2839 / 1280 | 2206 / 673 | 2546 / 915 | 2535 / 898 | 2529 / 898 | 1480 / 1480 |
| fastapi.tiangolo.com/reference/encoders | 1117 / 0 | 2405 / 1242 | 2415 / 1252 | 1792 / 659 | 2131 / 897 | 2116 / 880 | 2114 / 880 | 1105 / 1105 |
| fastapi.tiangolo.com/reference/exceptions | — | — | — | — | — | — | — | 711 / 139 |
| fastapi.tiangolo.com/reference/fastapi | 29527 / 0 | 31312 / 1444 | 31322 / 1454 | 30321 / 778 | 30633 / 1016 | 30640 / 997 | 30626 / 1009 | 28966 / 111 |
| fastapi.tiangolo.com/reference/httpconnection | — | — | — | — | — | — | — | 257 / 104 |
| fastapi.tiangolo.com/reference/middleware | — | — | — | — | — | — | — | 950 / 234 |
| fastapi.tiangolo.com/reference/openapi | 32 / 0 | 1310 / 1235 | 1322 / 1247 | 696 / 648 | 1028 / 882 | 1013 / 865 | 1011 / 865 | 33 / 33 |
| fastapi.tiangolo.com/reference/openapi/docs | — | — | — | — | — | — | — | 1717 / 1717 |
| fastapi.tiangolo.com/reference/openapi/models | — | — | — | — | — | — | — | 3639 / 22 |
| fastapi.tiangolo.com/reference/parameters | — | — | — | — | — | — | — | 12210 / 12210 |
| fastapi.tiangolo.com/reference/request | — | — | — | — | — | — | — | 623 / 148 |
| fastapi.tiangolo.com/reference/response | — | — | — | — | — | — | — | 618 / 146 |
| fastapi.tiangolo.com/reference/responses | — | — | — | — | — | — | — | 5297 / 295 |
| fastapi.tiangolo.com/reference/security | 8809 / 0 | 10895 / 1910 | 10905 / 1920 | 9911 / 1086 | 10207 / 1324 | 10232 / 1305 | 10188 / 1305 | 8599 / 191 |
| fastapi.tiangolo.com/reference/staticfiles | — | — | — | — | — | — | — | 943 / 132 |
| fastapi.tiangolo.com/reference/status | 996 / 0 | 2758 / 1720 | 2768 / 1730 | 1986 / 974 | 2321 / 1212 | 2306 / 1193 | 2308 / 1199 | 836 / 127 |
| fastapi.tiangolo.com/reference/templating | — | — | — | — | — | — | — | 629 / 223 |
| fastapi.tiangolo.com/reference/testclient | — | — | — | — | — | — | — | 2069 / 193 |
| fastapi.tiangolo.com/reference/uploadfile | — | — | — | — | — | — | — | 676 / 106 |
| fastapi.tiangolo.com/reference/websockets | 1267 / 0 | 2816 / 1456 | 2826 / 1466 | 2086 / 803 | 2419 / 1039 | 2404 / 1020 | 2400 / 1020 | 1212 / 141 |
| fastapi.tiangolo.com/release-notes | — | — | — | — | — | — | — | 54502 / 9 |
| fastapi.tiangolo.com/resources | — | — | — | — | — | — | — | 15 / 15 |
| fastapi.tiangolo.com/ru | — | — | — | — | — | — | — | 2235 / 238 |
| fastapi.tiangolo.com/tr | — | — | — | — | — | — | — | 2143 / 238 |
| fastapi.tiangolo.com/translation-banner | — | — | — | — | — | — | — | 52 / 52 |
| fastapi.tiangolo.com/tutorial | — | — | — | — | — | — | — | 404 / 404 |
| fastapi.tiangolo.com/tutorial/application-configuration | — | — | — | — | — | — | — | 8 / 8 |
| fastapi.tiangolo.com/tutorial/background-tasks | — | — | — | — | — | — | — | 954 / 954 |
| fastapi.tiangolo.com/tutorial/bigger-applications | — | — | — | — | — | — | — | 3245 / 453 |
| fastapi.tiangolo.com/tutorial/body | — | — | — | — | — | — | — | 1204 / 1204 |
| fastapi.tiangolo.com/tutorial/body-fields | — | — | — | — | — | — | — | 638 / 638 |
| fastapi.tiangolo.com/tutorial/body-multiple-params | — | — | — | — | — | — | — | 1362 / 1362 |
| fastapi.tiangolo.com/tutorial/body-nested-models | — | — | — | — | — | — | — | 1412 / 131 |
| fastapi.tiangolo.com/tutorial/body-updates | — | — | — | — | — | — | — | 991 / 163 |
| fastapi.tiangolo.com/tutorial/cookie-param-models | — | — | — | — | — | — | — | 572 / 572 |
| fastapi.tiangolo.com/tutorial/cookie-params | 365 / 0 | 1674 / 1269 | 1686 / 1281 | 1058 / 677 | 1388 / 913 | 1379 / 896 | 1371 / 896 | 352 / 352 |
| fastapi.tiangolo.com/tutorial/cors | — | — | — | — | — | — | — | 740 / 619 |
| fastapi.tiangolo.com/tutorial/debugging | — | — | — | — | — | — | — | 378 / 66 |
| fastapi.tiangolo.com/tutorial/dependencies | 1793 / 0 | 3099 / 1324 | 3109 / 1334 | 2521 / 712 | 2786 / 948 | 2841 / 929 | 2813 / 929 | 1707 / 178 |
| fastapi.tiangolo.com/tutorial/dependencies/classes-as-d | — | — | — | — | — | — | — | 1937 / 1937 |
| fastapi.tiangolo.com/tutorial/dependencies/dependencies | — | — | — | — | — | — | — | 873 / 349 |
| fastapi.tiangolo.com/tutorial/dependencies/dependencies | — | — | — | — | — | — | — | 2277 / 1263 |
| fastapi.tiangolo.com/tutorial/dependencies/global-depen | — | — | — | — | — | — | — | 279 / 279 |
| fastapi.tiangolo.com/tutorial/dependencies/sub-dependen | 864 / 0 | 2199 / 1307 | 2213 / 1321 | 1586 / 706 | 1901 / 940 | 1908 / 923 | 1896 / 923 | 828 / 828 |
| fastapi.tiangolo.com/tutorial/encoder | — | — | — | — | — | — | — | 280 / 280 |
| fastapi.tiangolo.com/tutorial/extra-data-types | — | — | — | — | — | — | — | 704 / 704 |
| fastapi.tiangolo.com/tutorial/extra-models | — | — | — | — | — | — | — | 1165 / 210 |
| fastapi.tiangolo.com/tutorial/first-steps | — | — | — | — | — | — | — | 1550 / 80 |
| fastapi.tiangolo.com/tutorial/handling-errors | 1710 / 0 | 3147 / 1407 | 3159 / 1419 | 2503 / 777 | 2817 / 1013 | 2826 / 996 | 2800 / 996 | 1656 / 171 |
| fastapi.tiangolo.com/tutorial/header-param-models | — | — | — | — | — | — | — | 680 / 680 |
| fastapi.tiangolo.com/tutorial/header-params | — | — | — | — | — | — | — | 668 / 668 |
| fastapi.tiangolo.com/tutorial/metadata | — | — | — | — | — | — | — | 1085 / 612 |
| fastapi.tiangolo.com/tutorial/middleware | — | — | — | — | — | — | — | 589 / 347 |
| fastapi.tiangolo.com/tutorial/path-operation-configurat | — | — | — | — | — | — | — | 876 / 286 |
| fastapi.tiangolo.com/tutorial/path-params | — | — | — | — | — | — | — | 1485 / 677 |
| fastapi.tiangolo.com/tutorial/path-params-numeric-valid | — | — | — | — | — | — | — | 1682 / 927 |
| fastapi.tiangolo.com/tutorial/query-param-models | — | — | — | — | — | — | — | 520 / 520 |
| fastapi.tiangolo.com/tutorial/query-params | — | — | — | — | — | — | — | 817 / 817 |
| fastapi.tiangolo.com/tutorial/query-params-str-validati | — | — | — | — | — | — | — | 3922 / 153 |
| fastapi.tiangolo.com/tutorial/request-files | — | — | — | — | — | — | — | 1741 / 562 |
| fastapi.tiangolo.com/tutorial/request-form-models | 445 / 0 | 1770 / 1287 | 1784 / 1301 | 1152 / 691 | 1479 / 927 | 1472 / 910 | 1462 / 910 | 429 / 429 |
| fastapi.tiangolo.com/tutorial/request-forms | 488 / 0 | 1812 / 1281 | 1824 / 1293 | 1189 / 685 | 1519 / 923 | 1510 / 904 | 1505 / 909 | 474 / 474 |
| fastapi.tiangolo.com/tutorial/request-forms-and-files | 388 / 0 | 1711 / 1283 | 1721 / 1293 | 1091 / 687 | 1426 / 929 | 1415 / 910 | 1407 / 910 | 375 / 375 |
| fastapi.tiangolo.com/tutorial/response-model | 3150 / 0 | 4706 / 1543 | 4716 / 1553 | 4040 / 874 | 4342 / 1118 | 4367 / 1099 | 4323 / 1099 | 3072 / 616 |
| fastapi.tiangolo.com/tutorial/response-status-code | — | — | — | — | — | — | — | 620 / 620 |
| fastapi.tiangolo.com/tutorial/schema-extra-example | — | — | — | — | — | — | — | 1966 / 408 |
| fastapi.tiangolo.com/tutorial/security | — | — | — | — | — | — | — | 674 / 174 |
| fastapi.tiangolo.com/tutorial/security/first-steps | — | — | — | — | — | — | — | 1500 / 1174 |
| fastapi.tiangolo.com/tutorial/security/get-current-user | — | — | — | — | — | — | — | 1500 / 1500 |
| fastapi.tiangolo.com/tutorial/security/oauth2-jwt | — | — | — | — | — | — | — | 4393 / 370 |
| fastapi.tiangolo.com/tutorial/security/simple-oauth2 | — | — | — | — | — | — | — | 3542 / 168 |
| fastapi.tiangolo.com/tutorial/server-sent-events | — | — | — | — | — | — | — | 1410 / 579 |
| fastapi.tiangolo.com/tutorial/sql-databases | — | — | — | — | — | — | — | 10436 / 282 |
| fastapi.tiangolo.com/tutorial/static-files | — | — | — | — | — | — | — | 238 / 80 |
| fastapi.tiangolo.com/tutorial/stream-json-lines | — | — | — | — | — | — | — | 1132 / 769 |
| fastapi.tiangolo.com/tutorial/testing | — | — | — | — | — | — | — | 1452 / 298 |
| fastapi.tiangolo.com/uk | — | — | — | — | — | — | — | 2274 / 233 |
| fastapi.tiangolo.com/virtual-environments | — | — | — | — | — | — | — | 2918 / 1019 |
| fastapi.tiangolo.com/zh | — | — | — | — | — | — | — | 1273 / 89 |
| fastapi.tiangolo.com/zh-hant | — | — | — | — | — | — | — | 1285 / 90 |
| fastapi.tiangolo.com/zh/contributing | — | — | — | — | — | — | — | 1610 / 84 |
| fastapi.tiangolo.com/zh/deployment | — | — | — | — | — | — | — | 46 / 46 |
| fastapi.tiangolo.com/zh/features | — | — | — | — | — | — | — | 410 / 21 |
| fastapi.tiangolo.com/zh/help-fastapi | — | — | — | — | — | — | — | 463 / 209 |
| fastapi.tiangolo.com/zh/python-types | — | — | — | — | — | — | — | 684 / 86 |
| fastapi.tiangolo.com/zh/tutorial | — | — | — | — | — | — | — | 105 / 105 |
| fastapi.tiangolo.com/zh/tutorial/body | — | — | — | — | — | — | — | 524 / 524 |
| fastapi.tiangolo.com/zh/tutorial/body-fields | — | — | — | — | — | — | — | 427 / 427 |
| fastapi.tiangolo.com/zh/tutorial/body-multiple-params | — | — | — | — | — | — | — | 909 / 909 |
| fastapi.tiangolo.com/zh/tutorial/first-steps | — | — | — | — | — | — | — | 717 / 59 |
| fastapi.tiangolo.com/zh/tutorial/path-params | — | — | — | — | — | — | — | 712 / 263 |
| fastapi.tiangolo.com/zh/tutorial/path-params-numeric-va | — | — | — | — | — | — | — | 1086 / 588 |
| fastapi.tiangolo.com/zh/tutorial/query-params | — | — | — | — | — | — | — | 420 / 420 |
| fastapi.tiangolo.com/zh/tutorial/query-params-str-valid | — | — | — | — | — | — | — | 2427 / 82 |

</details>

## python-docs

| Tool | Avg words | Preamble [1] | Repeat rate | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|---|---|
| **markcrawl** | **758** | **0** | **0%** | **24** | **4.0** | **1.4** | **100%** | **64%** |
| crawl4ai | 1125 | 52 | 2% | 93 | 10.6 | 1.4 | 100% | 52% |
| crawl4ai-raw | 1125 | 52 | 2% | 93 | 10.6 | 1.4 | 100% | 52% |
| scrapy+md | 1273 | 4 | 1% | 70 | 12.4 | 2.1 | 100% | 100% |
| crawlee | 1071 | 43 | 1% | 93 | 10.6 | 1.4 | 100% | 87% |
| colly+md | 1001 | 22 | 1% | 93 | 10.6 | 1.4 | 100% | 87% |
| playwright | 1071 | 43 | 1% | 93 | 10.6 | 1.4 | 100% | 87% |
| firecrawl | 3077 | 0 | 0% | 1815 | 8.2 | 0.0 | 0% | 0% |

**[1]** Avg words per page before the first heading (nav chrome). Values >50 likely indicate nav/boilerplate problems.

**Reading the numbers:**
**markcrawl** produces the cleanest output with 0 word of preamble per page, while **crawl4ai** injects 52 words of nav chrome before content begins. markcrawl's lower recall (64% vs 100%) reflects stricter content filtering — the "missed" sentences are predominantly navigation, sponsor links, and footer text that other tools include as content. For RAG, this is a net positive: fewer junk tokens per chunk means better embedding quality and retrieval precision.

<details>
<summary>Sample output — first 40 lines of <code>docs.python.org/3.12</code></summary>

This shows what each tool outputs at the *top* of the same page.
Nav boilerplate appears here before the real content starts.

**markcrawl**
```
# Python 3.12.13 documentation

Welcome! This is the official documentation for Python 3.12.13.

**Documentation sections:**

|  |  |
| --- | --- |
| [What's new in Python 3.12?](whatsnew/3.12.html)   Or [all "What's new" documents since Python 2.0](whatsnew/index.html)  [Tutorial](tutorial/index.html)  Start here: a tour of Python's syntax and features  [Library reference](library/index.html)  Standard library and builtins  [Language reference](reference/index.html)  Syntax and language elements  [Python setup and usage](using/index.html)  How to install, configure, and use Python  [Python HOWTOs](howto/index.html)  In-depth topic manuals | [Installing Python modules](installing/index.html)  Third-party modules and PyPI.org  [Distributing Python modules](distributing/index.html)  Publishing modules for use by other people  [Extending and embedding](extending/index.html)  For C/C++ programmers  [Python's C API](c-api/index.html)  C API reference  [FAQs](faq/index.html)  Frequently asked questions (with answers!)  [Deprecations](deprecations/index.html)  Deprecated functionality |

**Indices, glossary, and search:**

|  |  |
| --- | --- |
| [Global module index](py-modindex.html)  All modules and libraries  [General index](genindex.html)  All functions, classes, and terms  [Glossary](glossary.html)  Terms explained | [Search page](search.html)  Search this documentation  [Complete table of contents](contents.html)  Lists all sections and subsections |

**Project information:**

|  |  |
| --- | --- |
| [Reporting issues](bugs.html)  [Contributing to Docs](https://devguide.python.org/documentation/help-documenting/)  [Download the documentation](download.html) | [History and license of Python](license.html)  [Copyright](copyright.html)  [About the documentation](about.html) |
```

**crawl4ai**
```
[ ![Python logo](https://docs.python.org/3.12/_static/py.svg) ](https://www.python.org/) dev (3.15) 3.14 3.13 3.12.13 3.11 3.10 3.9 3.8 3.7 3.6 3.5 3.4 3.3 3.2 3.1 3.0 2.7 2.6
Greek | Ελληνικά English Spanish | español French | français Italian | italiano Japanese | 日本語 Korean | 한국어 Polish | polski Brazilian Portuguese | Português brasileiro Romanian | Românește Turkish | Türkçe Simplified Chinese | 简体中文 Traditional Chinese | 繁體中文
Theme  Auto Light Dark
### Download
[Download these documents](https://docs.python.org/3.12/download.html)
### Docs by version
  * [Python 3.15 (in development)](https://docs.python.org/3.15/)
  * [Python 3.14 (stable)](https://docs.python.org/3.14/)
  * [Python 3.13 (stable)](https://docs.python.org/3.13/)
  * [Python 3.12 (security-fixes)](https://docs.python.org/3.12/)
  * [Python 3.11 (security-fixes)](https://docs.python.org/3.11/)
  * [Python 3.10 (security-fixes)](https://docs.python.org/3.10/)
  * [Python 3.9 (EOL)](https://docs.python.org/3.9/)
  * [Python 3.8 (EOL)](https://docs.python.org/3.8/)
  * [Python 3.7 (EOL)](https://docs.python.org/3.7/)
  * [Python 3.6 (EOL)](https://docs.python.org/3.6/)
  * [Python 3.5 (EOL)](https://docs.python.org/3.5/)
  * [Python 3.4 (EOL)](https://docs.python.org/3.4/)
  * [Python 3.3 (EOL)](https://docs.python.org/3.3/)
  * [Python 3.2 (EOL)](https://docs.python.org/3.2/)
  * [Python 3.1 (EOL)](https://docs.python.org/3.1/)
  * [Python 3.0 (EOL)](https://docs.python.org/3.0/)
  * [Python 2.7 (EOL)](https://docs.python.org/2.7/)
  * [Python 2.6 (EOL)](https://docs.python.org/2.6/)
  * [All versions](https://www.python.org/doc/versions/)


### Other resources
  * [PEP Index](https://peps.python.org/)
  * [Beginner's Guide](https://wiki.python.org/moin/BeginnersGuide)
  * [Book List](https://wiki.python.org/moin/PythonBooks)
  * [Audio/Visual Talks](https://www.python.org/doc/av/)
  * [Python Developer’s Guide](https://devguide.python.org/)


### Navigation
  * [index](https://docs.python.org/3.12/genindex.html "General Index")
  * [modules](https://docs.python.org/3.12/py-modindex.html "Python Module Index") |
  * ![Python logo](https://docs.python.org/3.12/_static/py.svg)
  * [Python](https://www.python.org/) »
```

**crawl4ai-raw**
```
[ ![Python logo](https://docs.python.org/3.12/_static/py.svg) ](https://www.python.org/) dev (3.15) 3.14 3.13 3.12.13 3.11 3.10 3.9 3.8 3.7 3.6 3.5 3.4 3.3 3.2 3.1 3.0 2.7 2.6
Greek | Ελληνικά English Spanish | español French | français Italian | italiano Japanese | 日本語 Korean | 한국어 Polish | polski Brazilian Portuguese | Português brasileiro Romanian | Românește Turkish | Türkçe Simplified Chinese | 简体中文 Traditional Chinese | 繁體中文
Theme  Auto Light Dark
### Download
[Download these documents](https://docs.python.org/3.12/download.html)
### Docs by version
  * [Python 3.15 (in development)](https://docs.python.org/3.15/)
  * [Python 3.14 (stable)](https://docs.python.org/3.14/)
  * [Python 3.13 (stable)](https://docs.python.org/3.13/)
  * [Python 3.12 (security-fixes)](https://docs.python.org/3.12/)
  * [Python 3.11 (security-fixes)](https://docs.python.org/3.11/)
  * [Python 3.10 (security-fixes)](https://docs.python.org/3.10/)
  * [Python 3.9 (EOL)](https://docs.python.org/3.9/)
  * [Python 3.8 (EOL)](https://docs.python.org/3.8/)
  * [Python 3.7 (EOL)](https://docs.python.org/3.7/)
  * [Python 3.6 (EOL)](https://docs.python.org/3.6/)
  * [Python 3.5 (EOL)](https://docs.python.org/3.5/)
  * [Python 3.4 (EOL)](https://docs.python.org/3.4/)
  * [Python 3.3 (EOL)](https://docs.python.org/3.3/)
  * [Python 3.2 (EOL)](https://docs.python.org/3.2/)
  * [Python 3.1 (EOL)](https://docs.python.org/3.1/)
  * [Python 3.0 (EOL)](https://docs.python.org/3.0/)
  * [Python 2.7 (EOL)](https://docs.python.org/2.7/)
  * [Python 2.6 (EOL)](https://docs.python.org/2.6/)
  * [All versions](https://www.python.org/doc/versions/)


### Other resources
  * [PEP Index](https://peps.python.org/)
  * [Beginner's Guide](https://wiki.python.org/moin/BeginnersGuide)
  * [Book List](https://wiki.python.org/moin/PythonBooks)
  * [Audio/Visual Talks](https://www.python.org/doc/av/)
  * [Python Developer’s Guide](https://devguide.python.org/)


### Navigation
  * [index](https://docs.python.org/3.12/genindex.html "General Index")
  * [modules](https://docs.python.org/3.12/py-modindex.html "Python Module Index") |
  * ![Python logo](https://docs.python.org/3.12/_static/py.svg)
  * [Python](https://www.python.org/) »
```

**scrapy+md**
```
Theme
Auto
Light
Dark

### Download

[Download these documents](download.html)

### Docs by version

* [Python 3.15 (in development)](https://docs.python.org/3.15/)
* [Python 3.14 (stable)](https://docs.python.org/3.14/)
* [Python 3.13 (stable)](https://docs.python.org/3.13/)
* [Python 3.12 (security-fixes)](https://docs.python.org/3.12/)
* [Python 3.11 (security-fixes)](https://docs.python.org/3.11/)
* [Python 3.10 (security-fixes)](https://docs.python.org/3.10/)
* [Python 3.9 (EOL)](https://docs.python.org/3.9/)
* [Python 3.8 (EOL)](https://docs.python.org/3.8/)
* [Python 3.7 (EOL)](https://docs.python.org/3.7/)
* [Python 3.6 (EOL)](https://docs.python.org/3.6/)
* [Python 3.5 (EOL)](https://docs.python.org/3.5/)
* [Python 3.4 (EOL)](https://docs.python.org/3.4/)
* [Python 3.3 (EOL)](https://docs.python.org/3.3/)
* [Python 3.2 (EOL)](https://docs.python.org/3.2/)
* [Python 3.1 (EOL)](https://docs.python.org/3.1/)
* [Python 3.0 (EOL)](https://docs.python.org/3.0/)
* [Python 2.7 (EOL)](https://docs.python.org/2.7/)
* [Python 2.6 (EOL)](https://docs.python.org/2.6/)
* [All versions](https://www.python.org/doc/versions/)

### Other resources

* [PEP Index](https://peps.python.org/)
* [Beginner's Guide](https://wiki.python.org/moin/BeginnersGuide)
* [Book List](https://wiki.python.org/moin/PythonBooks)
* [Audio/Visual Talks](https://www.python.org/doc/av/)
* [Python Developer’s Guide](https://devguide.python.org/)

### Navigation
```

**crawlee**
```
3.12.13 Documentation
















@media only screen {
table.full-width-table {
width: 100%;
}
}



dev (3.15)3.143.133.12.133.113.103.93.83.73.63.53.43.33.23.13.02.72.6

Greek | ΕλληνικάEnglishSpanish | españolFrench | françaisItalian | italianoJapanese | 日本語Korean | 한국어Polish | polskiBrazilian Portuguese | Português brasileiroRomanian | RomâneșteTurkish | TürkçeSimplified Chinese | 简体中文Traditional Chinese | 繁體中文

Theme
Auto
Light
Dark

### Download

[Download these documents](download.html)

### Docs by version
```

**colly+md**
```
3.12.13 Documentation
















@media only screen {
table.full-width-table {
width: 100%;
}
}



Theme
Auto
Light
Dark

### Download

[Download these documents](download.html)

### Docs by version

* [Python 3.15 (in development)](https://docs.python.org/3.15/)
* [Python 3.14 (stable)](https://docs.python.org/3.14/)
* [Python 3.13 (stable)](https://docs.python.org/3.13/)
* [Python 3.12 (security-fixes)](https://docs.python.org/3.12/)
```

**playwright**
```
3.12.13 Documentation
















@media only screen {
table.full-width-table {
width: 100%;
}
}



dev (3.15)3.143.133.12.133.113.103.93.83.73.63.53.43.33.23.13.02.72.6

Greek | ΕλληνικάEnglishSpanish | españolFrench | françaisItalian | italianoJapanese | 日本語Korean | 한국어Polish | polskiBrazilian Portuguese | Português brasileiroRomanian | RomâneșteTurkish | TürkçeSimplified Chinese | 简体中文Traditional Chinese | 繁體中文

Theme
Auto
Light
Dark

### Download

[Download these documents](download.html)

### Docs by version
```

**firecrawl** — no output for this URL

</details>

<details>
<summary>Per-page word counts and preamble [1]</summary>

| URL | markcrawl words / preamble [1] | crawl4ai words / preamble [1] | crawl4ai-raw words / preamble [1] | scrapy+md words / preamble [1] | crawlee words / preamble [1] | colly+md words / preamble [1] | playwright words / preamble [1] | firecrawl words / preamble [1] |
|---|---|---|---|---|---|---|---|---|
| docs.python.org/2.6 | 328 / 0 | 323 / 0 | 323 / 0 | — | 349 / 20 | 349 / 20 | 349 / 20 | — |
| docs.python.org/2.7 | 186 / 0 | 320 / 28 | 320 / 28 | — | 315 / 30 | 309 / 30 | 315 / 30 | — |
| docs.python.org/3.1 | 320 / 0 | 315 / 0 | 315 / 0 | — | 341 / 20 | 341 / 20 | 341 / 20 | — |
| docs.python.org/3.10 | 190 / 0 | 711 / 68 | 711 / 68 | 521 / 4 | 629 / 47 | 533 / 16 | 629 / 47 | — |
| docs.python.org/3.10/c-api/index.html | 427 / 0 | 837 / 68 | 837 / 68 | 640 / 4 | 754 / 53 | 658 / 22 | 754 / 53 | — |
| docs.python.org/3.10/extending/index.html | 623 / 0 | 1108 / 68 | 1108 / 68 | 912 / 4 | 1028 / 55 | 932 / 24 | 1028 / 55 | — |
| docs.python.org/3.10/faq/index.html | 48 / 0 | 454 / 68 | 454 / 68 | 257 / 4 | 371 / 53 | 275 / 22 | 371 / 53 | — |
| docs.python.org/3.10/installing/index.html | 1255 / 0 | 1808 / 68 | 1808 / 68 | 1612 / 4 | 1725 / 52 | 1629 / 21 | 1725 / 52 | — |
| docs.python.org/3.10/library/index.html | 2282 / 0 | 2684 / 68 | 2684 / 68 | 2487 / 4 | 2601 / 53 | 2505 / 22 | 2601 / 53 | — |
| docs.python.org/3.10/license.html | 6986 / 0 | 7625 / 68 | 7625 / 68 | 7445 / 4 | 7558 / 52 | 7462 / 21 | 7558 / 52 | — |
| docs.python.org/3.10/reference/index.html | 438 / 0 | 844 / 68 | 844 / 68 | 647 / 4 | 761 / 53 | 665 / 22 | 761 / 53 | — |
| docs.python.org/3.10/using/index.html | 460 / 0 | 870 / 68 | 870 / 68 | 673 / 4 | 787 / 53 | 691 / 22 | 787 / 53 | — |
| docs.python.org/3.11 | 188 / 0 | 711 / 68 | 711 / 68 | 522 / 4 | 629 / 47 | 534 / 16 | 629 / 47 | — |
| docs.python.org/3.12 | 191 / 0 | 712 / 68 | 712 / 68 | 525 / 4 | 632 / 47 | 537 / 16 | 632 / 47 | — |
| docs.python.org/3.13 | 191 / 0 | 712 / 68 | 712 / 68 | 525 / 4 | 632 / 47 | 537 / 16 | 632 / 47 | — |
| docs.python.org/3.14 | 191 / 0 | 712 / 68 | 712 / 68 | 525 / 4 | 632 / 47 | 537 / 16 | 632 / 47 | — |
| docs.python.org/3.15 | 191 / 0 | 709 / 67 | 709 / 67 | 525 / 4 | 629 / 46 | 537 / 16 | 629 / 46 | — |
| docs.python.org/3.2 | 302 / 0 | 298 / 0 | 298 / 0 | — | 324 / 20 | 323 / 20 | 324 / 20 | — |
| docs.python.org/3.5 | 186 / 0 | 371 / 28 | 371 / 28 | — | 353 / 29 | 324 / 29 | 353 / 29 | — |
| docs.python.org/3.7 | 186 / 0 | 371 / 28 | 371 / 28 | — | 363 / 39 | 334 / 39 | 363 / 39 | — |
| docs.python.org/3/library | — | — | — | — | — | — | — | 2394 / 0 |
| docs.python.org/3/library/__future__.html | — | — | — | — | — | — | — | 912 / 0 |
| docs.python.org/3/library/__main__.html | — | — | — | — | — | — | — | 1979 / 0 |
| docs.python.org/3/library/_thread.html | — | — | — | — | — | — | — | 1312 / 0 |
| docs.python.org/3/library/abc.html | — | — | — | — | — | — | — | 1771 / 0 |
| docs.python.org/3/library/aifc.html | — | — | — | — | — | — | — | 292 / 0 |
| docs.python.org/3/library/allos.html | — | — | — | — | — | — | — | 775 / 0 |
| docs.python.org/3/library/annotationlib.html | — | — | — | — | — | — | — | 4093 / 0 |
| docs.python.org/3/library/archiving.html | — | — | — | — | — | — | — | 487 / 0 |
| docs.python.org/3/library/argparse.html | — | — | — | — | — | — | — | 11203 / 0 |
| docs.python.org/3/library/array.html | — | — | — | — | — | — | — | 1716 / 0 |
| docs.python.org/3/library/ast.html | — | — | — | — | — | — | — | 10362 / 0 |
| docs.python.org/3/library/asynchat.html | — | — | — | — | — | — | — | 311 / 0 |
| docs.python.org/3/library/asyncio-api-index.html | — | — | — | — | — | — | — | 911 / 0 |
| docs.python.org/3/library/asyncio-dev.html | — | — | — | — | — | — | — | 2081 / 0 |
| docs.python.org/3/library/asyncio-eventloop.html | — | — | — | — | — | — | — | 9323 / 0 |
| docs.python.org/3/library/asyncio-exceptions.html | — | — | — | — | — | — | — | 468 / 0 |
| docs.python.org/3/library/asyncio-extending.html | — | — | — | — | — | — | — | 636 / 0 |
| docs.python.org/3/library/asyncio-future.html | — | — | — | — | — | — | — | 1379 / 0 |
| docs.python.org/3/library/asyncio-graph.html | — | — | — | — | — | — | — | 880 / 0 |
| docs.python.org/3/library/asyncio-llapi-index.html | — | — | — | — | — | — | — | 1914 / 0 |
| docs.python.org/3/library/asyncio-platforms.html | — | — | — | — | — | — | — | 573 / 0 |
| docs.python.org/3/library/asyncio-policy.html | — | — | — | — | — | — | — | 824 / 0 |
| docs.python.org/3/library/asyncio-protocol.html | — | — | — | — | — | — | — | 4244 / 0 |
| docs.python.org/3/library/asyncio-queue.html | — | — | — | — | — | — | — | 1292 / 0 |
| docs.python.org/3/library/asyncio-runner.html | — | — | — | — | — | — | — | 1071 / 0 |
| docs.python.org/3/library/asyncio-stream.html | — | — | — | — | — | — | — | 2264 / 0 |
| docs.python.org/3/library/asyncio-subprocess.html | — | — | — | — | — | — | — | 1651 / 0 |
| docs.python.org/3/library/asyncio-sync.html | — | — | — | — | — | — | — | 2032 / 0 |
| docs.python.org/3/library/asyncio-task.html | — | — | — | — | — | — | — | 6789 / 0 |
| docs.python.org/3/library/asyncio.html | — | — | — | — | — | — | — | 572 / 0 |
| docs.python.org/3/library/asyncore.html | — | — | — | — | — | — | — | 302 / 0 |
| docs.python.org/3/library/atexit.html | — | — | — | — | — | — | — | 872 / 0 |
| docs.python.org/3/library/audioop.html | — | — | — | — | — | — | — | 292 / 0 |
| docs.python.org/3/library/audit_events.html | — | — | — | — | — | — | — | 1847 / 0 |
| docs.python.org/3/library/base64.html | — | — | — | — | — | — | — | 2052 / 0 |
| docs.python.org/3/library/bdb.html | — | — | — | — | — | — | — | 2604 / 0 |
| docs.python.org/3/library/binary.html | — | — | — | — | — | — | — | 463 / 0 |
| docs.python.org/3/library/binascii.html | — | — | — | — | — | — | — | 1221 / 0 |
| docs.python.org/3/library/bisect.html | — | — | — | — | — | — | — | 1617 / 0 |
| docs.python.org/3/library/builtins.html | — | — | — | — | — | — | — | 431 / 0 |
| docs.python.org/3/library/bz2.html | — | — | — | — | — | — | — | 2097 / 0 |
| docs.python.org/3/library/calendar.html | — | — | — | — | — | — | — | 3889 / 0 |
| docs.python.org/3/library/cgi.html | — | — | — | — | — | — | — | 329 / 0 |
| docs.python.org/3/library/cgitb.html | — | — | — | — | — | — | — | 330 / 0 |
| docs.python.org/3/library/chunk.html | — | — | — | — | — | — | — | 301 / 0 |
| docs.python.org/3/library/cmath.html | — | — | — | — | — | — | — | 2209 / 0 |
| docs.python.org/3/library/cmd.html | — | — | — | — | — | — | — | 2237 / 0 |
| docs.python.org/3/library/cmdline.html | — | — | — | — | — | — | — | 444 / 0 |
| docs.python.org/3/library/cmdlinelibs.html | — | — | — | — | — | — | — | 334 / 0 |
| docs.python.org/3/library/code.html | — | — | — | — | — | — | — | 1407 / 0 |
| docs.python.org/3/library/codecs.html | — | — | — | — | — | — | — | 8946 / 0 |
| docs.python.org/3/library/codeop.html | — | — | — | — | — | — | — | 670 / 0 |
| docs.python.org/3/library/collections.abc.html | — | — | — | — | — | — | — | 2442 / 0 |
| docs.python.org/3/library/collections.html | — | — | — | — | — | — | — | 7302 / 0 |
| docs.python.org/3/library/colorsys.html | — | — | — | — | — | — | — | 457 / 0 |
| docs.python.org/3/library/compileall.html | — | — | — | — | — | — | — | 2258 / 0 |
| docs.python.org/3/library/compression.html | — | — | — | — | — | — | — | 377 / 0 |
| docs.python.org/3/library/compression.zstd.html | — | — | — | — | — | — | — | 5047 / 0 |
| docs.python.org/3/library/concurrency.html | — | — | — | — | — | — | — | 679 / 0 |
| docs.python.org/3/library/concurrent.futures.html | — | — | — | — | — | — | — | 4248 / 0 |
| docs.python.org/3/library/concurrent.html | — | — | — | — | — | — | — | 275 / 0 |
| docs.python.org/3/library/concurrent.interpreters.html | — | — | — | — | — | — | — | 1945 / 0 |
| docs.python.org/3/library/configparser.html | — | — | — | — | — | — | — | 7144 / 0 |
| docs.python.org/3/library/constants.html | — | — | — | — | — | — | — | 849 / 0 |
| docs.python.org/3/library/contextlib.html | — | — | — | — | — | — | — | 4996 / 0 |
| docs.python.org/3/library/contextvars.html | — | — | — | — | — | — | — | 1676 / 0 |
| docs.python.org/3/library/copy.html | — | — | — | — | — | — | — | 878 / 0 |
| docs.python.org/3/library/copyreg.html | — | — | — | — | — | — | — | 516 / 0 |
| docs.python.org/3/library/crypt.html | — | — | — | — | — | — | — | 344 / 0 |
| docs.python.org/3/library/crypto.html | — | — | — | — | — | — | — | 356 / 0 |
| docs.python.org/3/library/csv.html | — | — | — | — | — | — | — | 3499 / 0 |
| docs.python.org/3/library/ctypes.html | — | — | — | — | — | — | — | 15868 / 0 |
| docs.python.org/3/library/curses.ascii.html | — | — | — | — | — | — | — | 1238 / 0 |
| docs.python.org/3/library/curses.html | — | — | — | — | — | — | — | 10727 / 0 |
| docs.python.org/3/library/curses.panel.html | — | — | — | — | — | — | — | 677 / 0 |
| docs.python.org/3/library/custominterp.html | — | — | — | — | — | — | — | 315 / 0 |
| docs.python.org/3/library/dataclasses.html | — | — | — | — | — | — | — | 4930 / 0 |
| docs.python.org/3/library/datatypes.html | — | — | — | — | — | — | — | 688 / 0 |
| docs.python.org/3/library/datetime.html | — | — | — | — | — | — | — | 15139 / 0 |
| docs.python.org/3/library/dbm.html | — | — | — | — | — | — | — | 2563 / 0 |
| docs.python.org/3/library/debug.html | — | — | — | — | — | — | — | 484 / 0 |
| docs.python.org/3/library/decimal.html | — | — | — | — | — | — | — | 11401 / 0 |
| docs.python.org/3/library/development.html | — | — | — | — | — | — | — | 979 / 0 |
| docs.python.org/3/library/devmode.html | — | — | — | — | — | — | — | 1242 / 0 |
| docs.python.org/3/library/dialog.html | — | — | — | — | — | — | — | 1087 / 0 |
| docs.python.org/3/library/difflib.html | — | — | — | — | — | — | — | 4984 / 0 |
| docs.python.org/3/library/dis.html | — | — | — | — | — | — | — | 8612 / 0 |
| docs.python.org/3/library/distribution.html | — | — | — | — | — | — | — | 341 / 0 |
| docs.python.org/3/library/distutils.html | — | — | — | — | — | — | — | 312 / 0 |
| docs.python.org/3/library/doctest.html | — | — | — | — | — | — | — | 10845 / 0 |
| docs.python.org/3/library/email.charset.html | — | — | — | — | — | — | — | 1338 / 0 |
| docs.python.org/3/library/email.compat32-message.html | — | — | — | — | — | — | — | 4628 / 0 |
| docs.python.org/3/library/email.contentmanager.html | — | — | — | — | — | — | — | 1424 / 0 |
| docs.python.org/3/library/email.encoders.html | — | — | — | — | — | — | — | 616 / 0 |
| docs.python.org/3/library/email.errors.html | — | — | — | — | — | — | — | 980 / 0 |
| docs.python.org/3/library/email.examples.html | — | — | — | — | — | — | — | 1837 / 0 |
| docs.python.org/3/library/email.generator.html | — | — | — | — | — | — | — | 2024 / 0 |
| docs.python.org/3/library/email.header.html | — | — | — | — | — | — | — | 1651 / 0 |
| docs.python.org/3/library/email.headerregistry.html | — | — | — | — | — | — | — | 2829 / 0 |
| docs.python.org/3/library/email.html | — | — | — | — | — | — | — | 1328 / 0 |
| docs.python.org/3/library/email.iterators.html | — | — | — | — | — | — | — | 528 / 0 |
| docs.python.org/3/library/email.message.html | — | — | — | — | — | — | — | 4579 / 0 |
| docs.python.org/3/library/email.mime.html | — | — | — | — | — | — | — | 1661 / 0 |
| docs.python.org/3/library/email.parser.html | — | — | — | — | — | — | — | 2196 / 0 |
| docs.python.org/3/library/email.policy.html | — | — | — | — | — | — | — | 4165 / 0 |
| docs.python.org/3/library/email.utils.html | — | — | — | — | — | — | — | 1590 / 0 |
| docs.python.org/3/library/ensurepip.html | — | — | — | — | — | — | — | 993 / 0 |
| docs.python.org/3/library/enum.html | — | — | — | — | — | — | — | 5123 / 0 |
| docs.python.org/3/library/errno.html | — | — | — | — | — | — | — | 2005 / 0 |
| docs.python.org/3/library/exceptions.html | — | — | — | — | — | — | — | 6007 / 0 |
| docs.python.org/3/library/faulthandler.html | — | — | — | — | — | — | — | 1651 / 0 |
| docs.python.org/3/library/fcntl.html | — | — | — | — | — | — | — | 1860 / 0 |
| docs.python.org/3/library/filecmp.html | — | — | — | — | — | — | — | 1114 / 0 |
| docs.python.org/3/library/fileformats.html | — | — | — | — | — | — | — | 354 / 0 |
| docs.python.org/3/library/fileinput.html | — | — | — | — | — | — | — | 1586 / 0 |
| docs.python.org/3/library/filesys.html | — | — | — | — | — | — | — | 529 / 0 |
| docs.python.org/3/library/fnmatch.html | — | — | — | — | — | — | — | 758 / 0 |
| docs.python.org/3/library/fractions.html | — | — | — | — | — | — | — | 1387 / 0 |
| docs.python.org/3/library/ftplib.html | — | — | — | — | — | — | — | 3285 / 0 |
| docs.python.org/3/library/functional.html | — | — | — | — | — | — | — | 300 / 0 |
| docs.python.org/3/library/functions.html | — | — | — | — | — | — | — | 13267 / 0 |
| docs.python.org/3/library/functools.html | — | — | — | — | — | — | — | 4211 / 0 |
| docs.python.org/3/library/gc.html | — | — | — | — | — | — | — | 1987 / 0 |
| docs.python.org/3/library/getopt.html | — | — | — | — | — | — | — | 1504 / 0 |
| docs.python.org/3/library/getpass.html | — | — | — | — | — | — | — | 619 / 0 |
| docs.python.org/3/library/gettext.html | — | — | — | — | — | — | — | 3650 / 0 |
| docs.python.org/3/library/glob.html | — | — | — | — | — | — | — | 1190 / 0 |
| docs.python.org/3/library/graphlib.html | — | — | — | — | — | — | — | 1461 / 0 |
| docs.python.org/3/library/grp.html | — | — | — | — | — | — | — | 537 / 0 |
| docs.python.org/3/library/gzip.html | — | — | — | — | — | — | — | 1888 / 0 |
| docs.python.org/3/library/hashlib.html | — | — | — | — | — | — | — | 4253 / 0 |
| docs.python.org/3/library/heapq.html | — | — | — | — | — | — | — | 2756 / 0 |
| docs.python.org/3/library/hmac.html | — | — | — | — | — | — | — | 980 / 0 |
| docs.python.org/3/library/html.entities.html | — | — | — | — | — | — | — | 390 / 0 |
| docs.python.org/3/library/html.html | — | — | — | — | — | — | — | 439 / 0 |
| docs.python.org/3/library/html.parser.html | — | — | — | — | — | — | — | 1760 / 0 |
| docs.python.org/3/library/i18n.html | — | — | — | — | — | — | — | 347 / 0 |
| docs.python.org/3/library/idle.html | — | — | — | — | — | — | — | 6890 / 0 |
| docs.python.org/3/library/imaplib.html | — | — | — | — | — | — | — | 3648 / 0 |
| docs.python.org/3/library/imghdr.html | — | — | — | — | — | — | — | 329 / 0 |
| docs.python.org/3/library/imp.html | — | — | — | — | — | — | — | 310 / 0 |
| docs.python.org/3/library/importlib.html | — | — | — | — | — | — | — | 7805 / 0 |
| docs.python.org/3/library/importlib.metadata.html | — | — | — | — | — | — | — | 2820 / 0 |
| docs.python.org/3/library/importlib.resources.abc.html | — | — | — | — | — | — | — | 1067 / 0 |
| docs.python.org/3/library/importlib.resources.html | — | — | — | — | — | — | — | 1486 / 0 |
| docs.python.org/3/library/inspect.html | — | — | — | — | — | — | — | 8427 / 0 |
| docs.python.org/3/library/internet.html | — | — | — | — | — | — | — | 811 / 0 |
| docs.python.org/3/library/intro.html | — | — | — | — | — | — | — | 1512 / 0 |
| docs.python.org/3/library/io.html | — | — | — | — | — | — | — | 7118 / 0 |
| docs.python.org/3/library/ipaddress.html | — | — | — | — | — | — | — | 5187 / 0 |
| docs.python.org/3/library/ipc.html | — | — | — | — | — | — | — | 336 / 0 |
| docs.python.org/3/library/itertools.html | — | — | — | — | — | — | — | 5819 / 0 |
| docs.python.org/3/library/json.html | — | — | — | — | — | — | — | 4288 / 0 |
| docs.python.org/3/library/keyword.html | — | — | — | — | — | — | — | 393 / 0 |
| docs.python.org/3/library/language.html | — | — | — | — | — | — | — | 449 / 0 |
| docs.python.org/3/library/linecache.html | — | — | — | — | — | — | — | 624 / 0 |
| docs.python.org/3/library/locale.html | — | — | — | — | — | — | — | 4046 / 0 |
| docs.python.org/3/library/logging.config.html | — | — | — | — | — | — | — | 5867 / 0 |
| docs.python.org/3/library/logging.handlers.html | — | — | — | — | — | — | — | 7330 / 0 |
| docs.python.org/3/library/logging.html | — | — | — | — | — | — | — | 9825 / 0 |
| docs.python.org/3/library/lzma.html | — | — | — | — | — | — | — | 2718 / 0 |
| docs.python.org/3/library/mailbox.html | — | — | — | — | — | — | — | 8759 / 0 |
| docs.python.org/3/library/mailcap.html | — | — | — | — | — | — | — | 298 / 0 |
| docs.python.org/3/library/markup.html | — | — | — | — | — | — | — | 581 / 0 |
| docs.python.org/3/library/marshal.html | — | — | — | — | — | — | — | 1225 / 0 |
| docs.python.org/3/library/math.html | — | — | — | — | — | — | — | 4631 / 0 |
| docs.python.org/3/library/mimetypes.html | — | — | — | — | — | — | — | 2291 / 0 |
| docs.python.org/3/library/mm.html | — | — | — | — | — | — | — | 273 / 0 |
| docs.python.org/3/library/mmap.html | — | — | — | — | — | — | — | 2585 / 0 |
| docs.python.org/3/library/modulefinder.html | — | — | — | — | — | — | — | 629 / 0 |
| docs.python.org/3/library/modules.html | — | — | — | — | — | — | — | 440 / 0 |
| docs.python.org/3/library/msilib.html | — | — | — | — | — | — | — | 304 / 0 |
| docs.python.org/3/library/msvcrt.html | — | — | — | — | — | — | — | 1400 / 0 |
| docs.python.org/3/library/multiprocessing.html | — | — | — | — | — | — | — | 18264 / 0 |
| docs.python.org/3/library/multiprocessing.shared_memory | — | — | — | — | — | — | — | 2624 / 0 |
| docs.python.org/3/library/netdata.html | — | — | — | — | — | — | — | 495 / 0 |
| docs.python.org/3/library/netrc.html | — | — | — | — | — | — | — | 736 / 0 |
| docs.python.org/3/library/nis.html | — | — | — | — | — | — | — | 304 / 0 |
| docs.python.org/3/library/nntplib.html | — | — | — | — | — | — | — | 301 / 0 |
| docs.python.org/3/library/numbers.html | — | — | — | — | — | — | — | 1275 / 0 |
| docs.python.org/3/library/numeric.html | — | — | — | — | — | — | — | 572 / 0 |
| docs.python.org/3/library/operator.html | — | — | — | — | — | — | — | 2663 / 0 |
| docs.python.org/3/library/optparse.html | — | — | — | — | — | — | — | 11471 / 0 |
| docs.python.org/3/library/os.html | — | — | — | — | — | — | — | 29776 / 0 |
| docs.python.org/3/library/os.path.html | — | — | — | — | — | — | — | 3477 / 0 |
| docs.python.org/3/library/ossaudiodev.html | — | — | — | — | — | — | — | 295 / 0 |
| docs.python.org/3/library/pathlib.html | — | — | — | — | — | — | — | 8859 / 0 |
| docs.python.org/3/library/pdb.html | — | — | — | — | — | — | — | 4588 / 0 |
| docs.python.org/3/library/persistence.html | — | — | — | — | — | — | — | 603 / 0 |
| docs.python.org/3/library/pickle.html | — | — | — | — | — | — | — | 7372 / 0 |
| docs.python.org/3/library/pickletools.html | — | — | — | — | — | — | — | 803 / 0 |
| docs.python.org/3/library/pipes.html | — | — | — | — | — | — | — | 302 / 0 |
| docs.python.org/3/library/pkgutil.html | — | — | — | — | — | — | — | 1581 / 0 |
| docs.python.org/3/library/platform.html | — | — | — | — | — | — | — | 2106 / 0 |
| docs.python.org/3/library/plistlib.html | — | — | — | — | — | — | — | 1094 / 0 |
| docs.python.org/3/library/poplib.html | — | — | — | — | — | — | — | 1495 / 0 |
| docs.python.org/3/library/posix.html | — | — | — | — | — | — | — | 738 / 0 |
| docs.python.org/3/library/pprint.html | — | — | — | — | — | — | — | 2093 / 0 |
| docs.python.org/3/library/profile.html | — | — | — | — | — | — | — | 4490 / 0 |
| docs.python.org/3/library/pty.html | — | — | — | — | — | — | — | 879 / 0 |
| docs.python.org/3/library/pwd.html | — | — | — | — | — | — | — | 535 / 0 |
| docs.python.org/3/library/py_compile.html | — | — | — | — | — | — | — | 1195 / 0 |
| docs.python.org/3/library/pyclbr.html | — | — | — | — | — | — | — | 914 / 0 |
| docs.python.org/3/library/pydoc.html | — | — | — | — | — | — | — | 992 / 0 |
| docs.python.org/3/library/pyexpat.html | — | — | — | — | — | — | — | 4738 / 0 |
| docs.python.org/3/library/python.html | — | — | — | — | — | — | — | 764 / 0 |
| docs.python.org/3/library/queue.html | — | — | — | — | — | — | — | 2029 / 0 |
| docs.python.org/3/library/quopri.html | — | — | — | — | — | — | — | 590 / 0 |
| docs.python.org/3/library/random.html | — | — | — | — | — | — | — | 4206 / 0 |
| docs.python.org/3/library/re.html | — | — | — | — | — | — | — | 11123 / 0 |
| docs.python.org/3/library/readline.html | — | — | — | — | — | — | — | 2056 / 0 |
| docs.python.org/3/library/removed.html | — | — | — | — | — | — | — | 439 / 0 |
| docs.python.org/3/library/reprlib.html | — | — | — | — | — | — | — | 1226 / 0 |
| docs.python.org/3/library/resource.html | — | — | — | — | — | — | — | 2058 / 0 |
| docs.python.org/3/library/rlcompleter.html | — | — | — | — | — | — | — | 581 / 0 |
| docs.python.org/3/library/runpy.html | — | — | — | — | — | — | — | 1500 / 0 |
| docs.python.org/3/library/sched.html | — | — | — | — | — | — | — | 898 / 0 |
| docs.python.org/3/library/secrets.html | — | — | — | — | — | — | — | 1084 / 0 |
| docs.python.org/3/library/security_warnings.html | — | — | — | — | — | — | — | 507 / 0 |
| docs.python.org/3/library/select.html | — | — | — | — | — | — | — | 3356 / 0 |
| docs.python.org/3/library/selectors.html | — | — | — | — | — | — | — | 1466 / 0 |
| docs.python.org/3/library/shelve.html | — | — | — | — | — | — | — | 1556 / 0 |
| docs.python.org/3/library/shlex.html | — | — | — | — | — | — | — | 2795 / 0 |
| docs.python.org/3/library/shutil.html | — | — | — | — | — | — | — | 5342 / 0 |
| docs.python.org/3/library/signal.html | — | — | — | — | — | — | — | 4310 / 0 |
| docs.python.org/3/library/site.html | — | — | — | — | — | — | — | 1806 / 0 |
| docs.python.org/3/library/smtpd.html | — | — | — | — | — | — | — | 312 / 0 |
| docs.python.org/3/library/smtplib.html | — | — | — | — | — | — | — | 3632 / 0 |
| docs.python.org/3/library/sndhdr.html | — | — | — | — | — | — | — | 317 / 0 |
| docs.python.org/3/library/socket.html | — | — | — | — | — | — | — | 12781 / 0 |
| docs.python.org/3/library/socketserver.html | — | — | — | — | — | — | — | 3649 / 0 |
| docs.python.org/3/library/spwd.html | — | — | — | — | — | — | — | 325 / 0 |
| docs.python.org/3/library/sqlite3.html | — | — | — | — | — | — | — | 11571 / 0 |
| docs.python.org/3/library/ssl.html | — | — | — | — | — | — | — | 14512 / 0 |
| docs.python.org/3/library/stat.html | — | — | — | — | — | — | — | 1976 / 0 |
| docs.python.org/3/library/statistics.html | — | — | — | — | — | — | — | 6180 / 0 |
| docs.python.org/3/library/stdtypes.html | — | — | — | — | — | — | — | 31227 / 0 |
| docs.python.org/3/library/string.html | — | — | — | — | — | — | — | 5725 / 0 |
| docs.python.org/3/library/string.templatelib.html | — | — | — | — | — | — | — | 1768 / 0 |
| docs.python.org/3/library/stringprep.html | — | — | — | — | — | — | — | 794 / 0 |
| docs.python.org/3/library/struct.html | — | — | — | — | — | — | — | 3680 / 0 |
| docs.python.org/3/library/subprocess.html | — | — | — | — | — | — | — | 8821 / 0 |
| docs.python.org/3/library/sunau.html | — | — | — | — | — | — | — | 295 / 0 |
| docs.python.org/3/library/superseded.html | — | — | — | — | — | — | — | 398 / 0 |
| docs.python.org/3/library/symtable.html | — | — | — | — | — | — | — | 1648 / 0 |
| docs.python.org/3/library/sys.html | — | — | — | — | — | — | — | 12257 / 0 |
| docs.python.org/3/library/sys.monitoring.html | — | — | — | — | — | — | — | 2237 / 0 |
| docs.python.org/3/library/sys_path_init.html | — | — | — | — | — | — | — | 1191 / 0 |
| docs.python.org/3/library/sysconfig.html | — | — | — | — | — | — | — | 2337 / 0 |
| docs.python.org/3/library/syslog.html | — | — | — | — | — | — | — | 1227 / 0 |
| docs.python.org/3/library/tabnanny.html | — | — | — | — | — | — | — | 485 / 0 |
| docs.python.org/3/library/tarfile.html | — | — | — | — | — | — | — | 7535 / 0 |
| docs.python.org/3/library/telnetlib.html | — | — | — | — | — | — | — | 320 / 0 |
| docs.python.org/3/library/tempfile.html | — | — | — | — | — | — | — | 3089 / 0 |
| docs.python.org/3/library/termios.html | — | — | — | — | — | — | — | 842 / 0 |
| docs.python.org/3/library/test.html | — | — | — | — | — | — | — | 8442 / 0 |
| docs.python.org/3/library/text.html | — | — | — | — | — | — | — | 465 / 0 |
| docs.python.org/3/library/textwrap.html | — | — | — | — | — | — | — | 1749 / 0 |
| docs.python.org/3/library/threading.html | — | — | — | — | — | — | — | 7930 / 0 |
| docs.python.org/3/library/threadsafety.html | — | — | — | — | — | — | — | 3067 / 0 |
| docs.python.org/3/library/time.html | — | — | — | — | — | — | — | 5434 / 0 |
| docs.python.org/3/library/timeit.html | — | — | — | — | — | — | — | 2170 / 0 |
| docs.python.org/3/library/tk.html | — | — | — | — | — | — | — | 1017 / 0 |
| docs.python.org/3/library/tkinter.colorchooser.html | — | — | — | — | — | — | — | 341 / 0 |
| docs.python.org/3/library/tkinter.dnd.html | — | — | — | — | — | — | — | 533 / 0 |
| docs.python.org/3/library/tkinter.font.html | — | — | — | — | — | — | — | 684 / 0 |
| docs.python.org/3/library/tkinter.html | — | — | — | — | — | — | — | 6426 / 0 |
| docs.python.org/3/library/tkinter.messagebox.html | — | — | — | — | — | — | — | 1064 / 0 |
| docs.python.org/3/library/tkinter.scrolledtext.html | — | — | — | — | — | — | — | 381 / 0 |
| docs.python.org/3/library/tkinter.ttk.html | — | — | — | — | — | — | — | 6688 / 0 |
| docs.python.org/3/library/token.html | — | — | — | — | — | — | — | 1801 / 0 |
| docs.python.org/3/library/tokenize.html | — | — | — | — | — | — | — | 1643 / 0 |
| docs.python.org/3/library/tomllib.html | — | — | — | — | — | — | — | 792 / 0 |
| docs.python.org/3/library/trace.html | — | — | — | — | — | — | — | 1256 / 0 |
| docs.python.org/3/library/traceback.html | — | — | — | — | — | — | — | 3818 / 0 |
| docs.python.org/3/library/tracemalloc.html | — | — | — | — | — | — | — | 3657 / 0 |
| docs.python.org/3/library/tty.html | — | — | — | — | — | — | — | 605 / 0 |
| docs.python.org/3/library/turtle.html | — | — | — | — | — | — | — | 10964 / 0 |
| docs.python.org/3/library/types.html | — | — | — | — | — | — | — | 2466 / 0 |
| docs.python.org/3/library/typing.html | — | — | — | — | — | — | — | 19075 / 0 |
| docs.python.org/3/library/unicodedata.html | — | — | — | — | — | — | — | 1172 / 0 |
| docs.python.org/3/library/unittest.html | — | — | — | — | — | — | — | 13372 / 0 |
| docs.python.org/3/library/unittest.mock-examples.html | — | — | — | — | — | — | — | 6905 / 0 |
| docs.python.org/3/library/unittest.mock.html | — | — | — | — | — | — | — | 14261 / 0 |
| docs.python.org/3/library/unix.html | — | — | — | — | — | — | — | 352 / 0 |
| docs.python.org/3/library/urllib.error.html | — | — | — | — | — | — | — | 568 / 0 |
| docs.python.org/3/library/urllib.html | — | — | — | — | — | — | — | 333 / 0 |
| docs.python.org/3/library/urllib.parse.html | — | — | — | — | — | — | — | 4407 / 0 |
| docs.python.org/3/library/urllib.request.html | — | — | — | — | — | — | — | 8074 / 0 |
| docs.python.org/3/library/urllib.robotparser.html | — | — | — | — | — | — | — | 611 / 0 |
| docs.python.org/3/library/uu.html | — | — | — | — | — | — | — | 295 / 0 |
| docs.python.org/3/library/uuid.html | — | — | — | — | — | — | — | 2449 / 0 |
| docs.python.org/3/library/venv.html | — | — | — | — | — | — | — | 3779 / 0 |
| docs.python.org/3/library/warnings.html | — | — | — | — | — | — | — | 4247 / 0 |
| docs.python.org/3/library/wave.html | — | — | — | — | — | — | — | 1347 / 0 |
| docs.python.org/3/library/weakref.html | — | — | — | — | — | — | — | 3421 / 0 |
| docs.python.org/3/library/webbrowser.html | — | — | — | — | — | — | — | 1566 / 0 |
| docs.python.org/3/library/windows.html | — | — | — | — | — | — | — | 301 / 0 |
| docs.python.org/3/library/winreg.html | — | — | — | — | — | — | — | 3755 / 0 |
| docs.python.org/3/library/winsound.html | — | — | — | — | — | — | — | 977 / 0 |
| docs.python.org/3/library/wsgiref.html | — | — | — | — | — | — | — | 5199 / 0 |
| docs.python.org/3/library/xdrlib.html | — | — | — | — | — | — | — | 289 / 0 |
| docs.python.org/3/library/xml.dom.html | — | — | — | — | — | — | — | 5230 / 0 |
| docs.python.org/3/library/xml.dom.minidom.html | — | — | — | — | — | — | — | 1841 / 0 |
| docs.python.org/3/library/xml.dom.pulldom.html | — | — | — | — | — | — | — | 864 / 0 |
| docs.python.org/3/library/xml.etree.elementtree.html | — | — | — | — | — | — | — | 7753 / 0 |
| docs.python.org/3/library/xml.html | — | — | — | — | — | — | — | 827 / 0 |
| docs.python.org/3/library/xml.sax.handler.html | — | — | — | — | — | — | — | 2510 / 0 |
| docs.python.org/3/library/xml.sax.html | — | — | — | — | — | — | — | 1224 / 0 |
| docs.python.org/3/library/xml.sax.reader.html | — | — | — | — | — | — | — | 1859 / 0 |
| docs.python.org/3/library/xml.sax.utils.html | — | — | — | — | — | — | — | 780 / 0 |
| docs.python.org/3/library/xmlrpc.client.html | — | — | — | — | — | — | — | 2927 / 0 |
| docs.python.org/3/library/xmlrpc.html | — | — | — | — | — | — | — | 318 / 0 |
| docs.python.org/3/library/xmlrpc.server.html | — | — | — | — | — | — | — | 2252 / 0 |
| docs.python.org/3/library/zipapp.html | — | — | — | — | — | — | — | 2421 / 0 |
| docs.python.org/3/library/zipfile.html | — | — | — | — | — | — | — | 5543 / 0 |
| docs.python.org/3/library/zipimport.html | — | — | — | — | — | — | — | 1105 / 0 |
| docs.python.org/3/library/zlib.html | — | — | — | — | — | — | — | 2756 / 0 |
| docs.python.org/3/library/zoneinfo.html | — | — | — | — | — | — | — | 2485 / 0 |

</details>

