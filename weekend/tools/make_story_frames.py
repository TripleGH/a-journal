"""Story pictures for every slide of a weekend post after slide 1.

Usage, from the repo folder:  python3 weekend/tools/make_story_frames.py weekend/<run date>

Reads <dir>/feed/slide-NN.jpg (1080 x 1350) and writes <dir>/story/story-NN.jpg
(1080 x 1920) for NN = 02 and up. Slide 1 keeps the painted story-single.jpg that
make_slides.py makes. Each story is the feed slide set 285 px from the top, with
the slide's own top and bottom colour (the median of its edge rows) filling the
bands, so the words stay inside the story safe zone (270 top, 400 bottom).
"""
import glob, os, sys
import numpy as np
from PIL import Image

W, H, Y = 1080, 1920, 285

def frame(src):
    s = Image.open(src).convert('RGB')
    if s.size != (1080, 1350):
        sys.exit(f'STOPPED: {src} is {s.size}, expected 1080 x 1350')
    a = np.asarray(s).astype(float)
    top = np.median(a[:8].reshape(-1, 3), 0)
    bot = np.median(a[-8:].reshape(-1, 3), 0)
    bg = np.zeros((H, W, 3))
    bg[:Y] = top
    bg[Y + 1350:] = bot
    im = Image.fromarray(bg.astype('uint8'))
    im.paste(s, (0, Y))
    return im

def main(d):
    feed = sorted(glob.glob(os.path.join(d, 'feed', 'slide-*.jpg')))
    if not feed:
        sys.exit(f'STOPPED: no feed slides in {d}')
    os.makedirs(os.path.join(d, 'story'), exist_ok=True)
    made = 0
    for f in feed:
        n = os.path.basename(f)[6:8]
        if n == '01':
            continue
        frame(f).save(os.path.join(d, 'story', f'story-{n}.jpg'), quality=92, subsampling=0)
        made += 1
    have = len(glob.glob(os.path.join(d, 'story', 'story-[0-9][0-9].jpg')))
    if have != len(feed) - 1:
        sys.exit(f'STOPPED: {len(feed)} feed slides but {have} story-NN pictures')
    print(f'{d}: {made} story pictures (slides 02 to {len(feed):02d}); slide 01 uses story-single.jpg')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1].rstrip('/'))
