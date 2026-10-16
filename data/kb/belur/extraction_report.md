# Extraction report – BELUR-KB-001 v1.0
Date: 2026-10-16

## Scope
Supplied: temples.bio timings page; explorekarnataka.com/heritage/ (listed twice). Scope applied: pages on those two sites that concern Belur / Chennakeshava Temple.

## Counts
- Pages fetched and processed: 6 (ExploreKarnataka 2, Temples.bio 4). All fetches succeeded.
- Pages discovered but not processed: 14 listed (plus 17 further nearby-temple profile pages on temples.bio, not individually listed).
- Third-party pages seen only as search snippets: 4 (not crawled; used only to flag timing disagreement).
- Failed fetches: 0 pages. First attempt at the temples.bio timings URL was refused until it appeared in a search result; then fetched normally.
- Images catalogued: 21 (17 ExploreKarnataka, 3 Temples.bio content images, 1 metadata-only). Excluded: logos, UI icons, 18 thumbnails of other temples.
- Images embedded in PDF: 0. Images downloaded: 0. Images visually described by AI: 0. OCR operations: 0.
- Structured chunks in kb_chunks.jsonl: 22 sections + 21 image records + 10 conflict records.
- Duplicate pages: none (the user's list repeated the ExploreKarnataka URL; processed once).

## Known gaps and limitations
1. Not a full-site crawl. Only in-scope Belur pages were processed; the other heritage pages, blog, divinity and city-tour sections of ExploreKarnataka were not opened.
2. robots.txt and site terms were not fetched or checked. I used a page-fetch tool, not a crawler, so no rate-limit issues arose, but I cannot confirm compliance beyond that.
3. No image files: the build environment has no outbound network, so images could not be downloaded, embedded or OCR'd. The PDF carries each image's ID, URL, source caption and context only. Descriptions are caption-derived; no visual AI descriptions were written because I did not view the images.
4. Wording is paraphrased, not copied verbatim. All facts, names, dates, numbers and prices are kept; the page's prose is not reproduced word for word, and short descriptions of the 18 other nearby temples on the city guide are summarised or omitted. For verbatim text, run a local crawler against the manifest URLs.
5. Collapsed FAQ answers on the timings page and the 10 hidden entries in the profile page's nearby-temples list were not captured.
6. Publication/modified dates: only the city guide shows one (July 2026). Others show none.
7. Third-party timing claims are unverified snippets.
8. Not a 100% completeness claim. Completeness is limited to the six pages above.

## QA checks done
- Manifest compared with pages processed: 6 of 6 in-scope pages have a status.
- Every section record carries source URL, page title, heading, date, content type.
- Image IDs in section text match image_catalogue rows (21 IDs).
- PDF text-selectability and page checks: see final verification in chat summary.
