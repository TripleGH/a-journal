# weekend

Pictures for Mom's Saturday and Sunday posts (older Come to the Fire devotionals), plus the slide maker that paints them.

- `<run date>/feed/slide-NN.jpg` and `<run date>/story/story-single.jpg`: one folder per post, named for the day it runs.
- `tools/`: the garden-look slide maker. `make_slides.py` here also takes `"hook": true` (a bigger first slide). Without that key it behaves like the weekday maker.
- `looks.json`: the log that keeps two weekend posts from looking alike.

The weekday robot uses the `tools/` folder and `looks.json` at the top of the repo, not these.
