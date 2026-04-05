# Extraction Quality Comparison

## Methodology

Three automated quality metrics, no LLM or human review needed:

1. **Junk detection** — known boilerplate phrases (nav, footer, breadcrumbs) found in output
2. **Structure preservation** — heading count and code block count in Markdown
3. **Cross-tool consensus** — sentences shared with other tools (precision) vs sentences all tools agree on (recall)

Precision answers: "How much of this tool's output is real content?"
Recall answers: "How much of the agreed-upon content did this tool capture?"

## quotes-toscrape

| Tool | Avg words | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|
| markcrawl | 157 | 1 | 2.7 | 0.0 | 73% | 73% |
| crawl4ai | 166 | 1 | 2.7 | 0.0 | 73% | 73% |
| scrapy+md | 166 | 1 | 2.7 | 0.0 | 73% | 73% |

<details>
<summary>Per-page word counts</summary>

| URL | markcrawl | crawl4ai | scrapy+md |
|---|---|---|---|
| quotes.toscrape.com | 271 | 282 | 282 |
| quotes.toscrape.com/author/Marilyn-Monroe | 382 | 390 | 390 |
| quotes.toscrape.com/login | 7 | 15 | 15 |
| quotes.toscrape.com/tag/abilities/page/1 | 46 | 54 | 54 |
| quotes.toscrape.com/tag/aliteracy/page/1 | 51 | 59 | 59 |
| quotes.toscrape.com/tag/be-yourself/page/1 | 46 | 54 | 54 |
| quotes.toscrape.com/tag/friends | 305 | 313 | 313 |
| quotes.toscrape.com/tag/friendship | 158 | 166 | 166 |
| quotes.toscrape.com/tag/humor/page/1 | 284 | 295 | 295 |
| quotes.toscrape.com/tag/life/page/1 | 498 | 509 | 509 |
| quotes.toscrape.com/tag/miracle/page/1 | 59 | 67 | 67 |
| quotes.toscrape.com/tag/misattributed-eleanor-roosevelt/page | 48 | 56 | 56 |
| quotes.toscrape.com/tag/obvious/page/1 | 40 | 48 | 48 |
| quotes.toscrape.com/tag/simile/page/1 | 76 | 84 | 84 |
| quotes.toscrape.com/tag/thinking/page/1 | 85 | 93 | 93 |

</details>

## books-toscrape

| Tool | Avg words | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|
| markcrawl | 283 | 0 | 1.7 | 0.0 | 94% | 100% |
| crawl4ai | 497 | 0 | 10.7 | 0.0 | 81% | 100% |
| scrapy+md | 388 | 0 | 1.7 | 0.0 | 100% | 100% |

<details>
<summary>Per-page word counts</summary>

| URL | markcrawl | crawl4ai | scrapy+md |
|---|---|---|---|
| books.toscrape.com | 397 | 702 | 531 |
| books.toscrape.com/catalogue/a-light-in-the-attic_1000/index | 269 | 276 | 284 |
| books.toscrape.com/catalogue/category/books/academic_40/inde | 51 | 282 | 185 |
| books.toscrape.com/catalogue/category/books/add-a-comment_18 | 424 | 745 | 558 |
| books.toscrape.com/catalogue/category/books/adult-fiction_29 | 53 | 284 | 187 |
| books.toscrape.com/catalogue/category/books/art_25/index.htm | 169 | 422 | 303 |
| books.toscrape.com/catalogue/category/books/biography_36/ind | 145 | 410 | 279 |
| books.toscrape.com/catalogue/category/books/business_35/inde | 296 | 612 | 430 |
| books.toscrape.com/catalogue/category/books/childrens_11/ind | 366 | 642 | 500 |
| books.toscrape.com/catalogue/category/books/christian-fictio | 140 | 388 | 274 |
| books.toscrape.com/catalogue/category/books/christian_43/ind | 96 | 342 | 230 |
| books.toscrape.com/catalogue/category/books/contemporary_38/ | 84 | 320 | 218 |
| books.toscrape.com/catalogue/category/books/crime_51/index.h | 58 | 296 | 192 |
| books.toscrape.com/catalogue/category/books/cultural_49/inde | 46 | 274 | 180 |
| books.toscrape.com/catalogue/category/books/default_15/index | 439 | 777 | 573 |
| books.toscrape.com/catalogue/category/books/erotica_50/index | 44 | 271 | 178 |
| books.toscrape.com/catalogue/category/books/fantasy_19/index | 436 | 764 | 570 |
| books.toscrape.com/catalogue/category/books/fiction_10/index | 365 | 636 | 499 |
| books.toscrape.com/catalogue/category/books/historical_42/in | 75 | 315 | 209 |
| books.toscrape.com/catalogue/category/books/history_32/index | 447 | 822 | 581 |
| books.toscrape.com/catalogue/category/books/horror_31/index. | 275 | 524 | 409 |
| books.toscrape.com/catalogue/category/books/humor_30/index.h | 239 | 529 | 373 |
| books.toscrape.com/catalogue/category/books/music_14/index.h | 304 | 616 | 438 |
| books.toscrape.com/catalogue/category/books/mystery_3/index. | 407 | 710 | 541 |
| books.toscrape.com/catalogue/category/books/new-adult_20/ind | 130 | 370 | 264 |
| books.toscrape.com/catalogue/category/books/nonfiction_13/in | 501 | 887 | 635 |
| books.toscrape.com/catalogue/category/books/novels_46/index. | 53 | 286 | 187 |
| books.toscrape.com/catalogue/category/books/parenting_28/ind | 53 | 286 | 187 |
| books.toscrape.com/catalogue/category/books/philosophy_7/ind | 236 | 516 | 370 |
| books.toscrape.com/catalogue/category/books/poetry_23/index. | 355 | 642 | 489 |
| books.toscrape.com/catalogue/category/books/politics_48/inde | 94 | 340 | 228 |
| books.toscrape.com/catalogue/category/books/psychology_26/in | 184 | 460 | 318 |
| books.toscrape.com/catalogue/category/books/religion_12/inde | 180 | 453 | 314 |
| books.toscrape.com/catalogue/category/books/romance_8/index. | 412 | 716 | 546 |
| books.toscrape.com/catalogue/category/books/science_22/index | 350 | 690 | 484 |
| books.toscrape.com/catalogue/category/books/self-help_41/ind | 152 | 422 | 286 |
| books.toscrape.com/catalogue/category/books/sequential-art_5 | 441 | 774 | 575 |
| books.toscrape.com/catalogue/category/books/short-stories_45 | 46 | 273 | 180 |
| books.toscrape.com/catalogue/category/books/spirituality_39/ | 171 | 447 | 305 |
| books.toscrape.com/catalogue/category/books/sports-and-games | 137 | 391 | 271 |
| books.toscrape.com/catalogue/category/books/suspense_44/inde | 52 | 284 | 186 |
| books.toscrape.com/catalogue/category/books/thriller_37/inde | 211 | 465 | 345 |
| books.toscrape.com/catalogue/category/books/travel_2/index.h | 258 | 550 | 392 |
| books.toscrape.com/catalogue/category/books/womens-fiction_9 | 330 | 614 | 464 |
| books.toscrape.com/catalogue/category/books/young-adult_21/i | 386 | 676 | 520 |
| books.toscrape.com/catalogue/its-only-the-himalayas_981/inde | 448 | 480 | 463 |
| books.toscrape.com/catalogue/libertarianism-for-beginners_98 | 411 | 442 | 426 |
| books.toscrape.com/catalogue/mesaerion-the-best-science-fict | 500 | 530 | 515 |
| books.toscrape.com/catalogue/our-band-could-be-your-life-sce | 388 | 419 | 403 |
| books.toscrape.com/catalogue/page-2.html | 413 | 726 | 547 |
| books.toscrape.com/catalogue/rip-it-up-and-start-again_986/i | 371 | 407 | 386 |
| books.toscrape.com/catalogue/sapiens-a-brief-history-of-huma | 470 | 481 | 485 |
| books.toscrape.com/catalogue/sharp-objects_997/index.html | 420 | 427 | 435 |
| books.toscrape.com/catalogue/soumission_998/index.html | 297 | 304 | 312 |
| books.toscrape.com/catalogue/starving-hearts-triangular-trad | 436 | 486 | 451 |
| books.toscrape.com/catalogue/the-boys-in-the-boat-nine-ameri | 576 | 620 | 591 |
| books.toscrape.com/catalogue/the-coming-woman-a-novel-based- | 789 | 818 | 804 |
| books.toscrape.com/catalogue/the-dirty-little-secrets-of-get | 489 | 508 | 504 |
| books.toscrape.com/catalogue/the-requiem-red_995/index.html | 350 | 362 | 365 |
| books.toscrape.com/catalogue/tipping-the-velvet_999/index.ht | 290 | 298 | 305 |

</details>

## fastapi-docs

| Tool | Avg words | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|
| markcrawl | 1209 | 28 | 23.2 | 21.3 | 96% | 92% |
| crawl4ai | 2696 | 28 | 23.2 | 21.3 | 58% | 92% |
| scrapy+md | 2000 | 50 | 23.2 | 21.3 | 96% | 92% |

<details>
<summary>Per-page word counts</summary>

| URL | markcrawl | crawl4ai | scrapy+md |
|---|---|---|---|
| fastapi.tiangolo.com | 2230 | 3979 | 3092 |
| fastapi.tiangolo.com/advanced/security/http-basic-auth | 1169 | 2553 | 1913 |
| fastapi.tiangolo.com/advanced/wsgi | 247 | 1565 | 937 |
| fastapi.tiangolo.com/deployment/versions | 537 | 1886 | 1254 |
| fastapi.tiangolo.com/editor-support | 310 | 1621 | 998 |
| fastapi.tiangolo.com/environment-variables | 1134 | 2449 | 1862 |
| fastapi.tiangolo.com/how-to/configure-swagger-ui | 1564 | 2923 | 2284 |
| fastapi.tiangolo.com/how-to/extending-openapi | 759 | 2145 | 1500 |
| fastapi.tiangolo.com/learn | 35 | 1322 | 697 |
| fastapi.tiangolo.com/newsletter | 10 | 1299 | 672 |
| fastapi.tiangolo.com/python-types | 1892 | 3339 | 2671 |
| fastapi.tiangolo.com/reference | 44 | 1334 | 706 |
| fastapi.tiangolo.com/reference/exceptions | 746 | 2097 | 1455 |
| fastapi.tiangolo.com/reference/httpconnection | 292 | 1671 | 1022 |
| fastapi.tiangolo.com/reference/middleware | 1030 | 2490 | 1811 |
| fastapi.tiangolo.com/reference/openapi/models | 3708 | 7394 | 5672 |
| fastapi.tiangolo.com/tutorial/cookie-params | 365 | 1686 | 1058 |
| fastapi.tiangolo.com/tutorial/debugging | 380 | 1735 | 1090 |
| fastapi.tiangolo.com/tutorial/dependencies/global-dependenci | 282 | 1601 | 973 |
| fastapi.tiangolo.com/tutorial/extra-models | 1219 | 2647 | 1998 |
| fastapi.tiangolo.com/tutorial/path-params-numeric-validation | 1734 | 3179 | 2518 |
| fastapi.tiangolo.com/tutorial/request-files | 1791 | 3199 | 2548 |
| fastapi.tiangolo.com/tutorial/response-model | 3150 | 4716 | 4040 |
| fastapi.tiangolo.com/tutorial/schema-extra-example | 2006 | 3483 | 2823 |
| fastapi.tiangolo.com/tutorial/security/simple-oauth2 | 3596 | 5078 | 4405 |

</details>

## python-docs

| Tool | Avg words | Junk found | Headings | Code blocks | Precision | Recall |
|---|---|---|---|---|---|---|
| markcrawl | 1460 | 16 | 9.7 | 3.7 | 66% | 40% |
| crawl4ai | 1910 | 99 | 17.5 | 3.7 | 32% | 40% |
| scrapy+md | 2109 | 85 | 20.1 | 4.6 | 89% | 38% |

<details>
<summary>Per-page word counts</summary>

| URL | markcrawl | crawl4ai | scrapy+md |
|---|---|---|---|
| docs.python.org/3.0 | 286 | 281 | — |
| docs.python.org/3.10 | 190 | 711 | 521 |
| docs.python.org/3.10/bugs.html | 666 | 1104 | 913 |
| docs.python.org/3.10/distributing/index.html | 984 | 1481 | 1285 |
| docs.python.org/3.10/extending/index.html | 623 | 1108 | 912 |
| docs.python.org/3.10/faq/index.html | 48 | 454 | 257 |
| docs.python.org/3.10/installing/index.html | 1255 | 1808 | 1612 |
| docs.python.org/3.10/license.html | 6986 | 7625 | 7445 |
| docs.python.org/3.10/tutorial/index.html | 982 | 1382 | 1185 |
| docs.python.org/3.10/whatsnew/3.10.html | 12688 | 13749 | 13627 |
| docs.python.org/3.10/whatsnew/index.html | 2172 | 2587 | 2389 |
| docs.python.org/3.11 | 188 | 711 | 522 |
| docs.python.org/3.12 | 191 | 712 | 525 |
| docs.python.org/3.13 | 191 | 712 | 525 |
| docs.python.org/3.14 | 191 | 712 | 525 |
| docs.python.org/3.15 | 191 | 709 | 525 |
| docs.python.org/3.4 | 339 | 336 | — |
| docs.python.org/3.6 | 186 | 371 | — |
| docs.python.org/3.8 | 189 | 551 | — |
| docs.python.org/3/bugs.html | — | — | 980 |
| docs.python.org/bugs.html | 650 | 1096 | — |

</details>

