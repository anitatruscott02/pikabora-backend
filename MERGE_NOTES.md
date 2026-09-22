# v0.5 notes

## Correction to last message
I told you Nigeria and Senegal had "no meal candidates in Meal Intelligence
yet." That was wrong -- meals.json already had 6 meals per country (18
total), matching the spreadsheet's NG-M001-006 and SN-M001-006. I said that
without testing it. Should have checked before claiming it.

## What was actually broken, found by testing before building anything new
Once I actually ran requests through it: a Nigerian user typing real Yoruba
food names -- "iyan" (pounded yam), "ewedu" (jute-leaf soup), "eja" (fish) --
matched nothing, because matching only checked a hand-written list of English
category words. Worse: the scoring gave every meal a 40-point floor
regardless of matches, so a completely unmatched request still returned
confident-looking ranked recommendations with every component silently
marked "missing." That's the exact false-precision failure the project's own
Quantitative Scoring sheet says to prevent (Availability fit is a Hard_Gate).

## The fix
- Matching now checks the real food database first: a user's term is looked
  up against every food's actual `source_food_name` AND `local_or_french_name`
  for that country, and matched via food_group if found. "Iyan" now matches
  because it's genuinely in the Nigeria data with food_group "Roots & tubers"
  -- not because I added it to a list.
- Zero real matches now excludes a meal from recommendations entirely,
  instead of floor-scoring it at 40. A fully-unmatched request now returns
  no recommendations and an honest message, not fake ones.
- Old hand-written pairs list kept as a fast-path (English generic words
  still short-circuit), but it's no longer the only path.

## Honest limit of the fix, checked not assumed
"Eja" and "ewedu" still don't match anything -- verified this is because
NFCT itself never lists them as local names for any entry (it has specific
fish-species names like "Iyak", "Alaran", but not the generic word "eja").
The fix pulls from real data; it doesn't invent coverage the source doesn't
have. Adding common generic vernacular terms by hand would undo the point of
this fix -- that's a real, separate follow-up if wanted, not silently done here.

## Tests
13 passing (11 previous + 2 new, one per fix above).
