# Come to the Fire slides

Picture slides made from Aletha Hinthorn's daily devotional, "Aletha Hinthorn's Journal."

This folder is a public shelf. A scheduling tool picks the pictures up from here and posts them to Instagram @cometothefire.

How it is laid out:

- One folder per post, named by the post date (year-month-day).
- `feed` holds the slides for the Instagram carousel. From November 18, 2026 they are 1080 x 1350 (Instagram's 4:5 portrait size). Older folders hold square 1080 x 1080 slides.
- `story` holds the tall frame for Instagram stories (1080 x 1920).
- A `posted.json` file inside a date folder means that post has already gone out.
- `looks.json` is the picture log: which kind of picture each post used, so no two posts look alike.

The words on the slides come from Aletha's post.

## The slide maker

Run it as `python3 tools/make_slides.py slides.json out`.

- `tools/make_slides.py` sets the words and checks every slide. It stops with a plain message instead of making a bad slide.
- `tools/scenes.py` paints the pictures with code: sky, land, water, trees and light. No photos and no AI image tool, so a picture can never contain a person.
- `tools/fonts` holds the typeface (Cormorant Garamond, open licence).
- `tools/render_slides.py` is the old name. It now calls the new maker.

It needs Python with numpy, scipy, opencv, Pillow, and Playwright with Chromium.

The rules it enforces:

1. Every slide gets its own picture. No picture type twice in one post. No post repeats an earlier post.
2. No people in any picture.
3. The words are the same size on every slide of a post.
4. The words stay inside a safe box with room on every side, the most at the bottom.
5. Strong contrast behind every word, measured on the finished slide.
