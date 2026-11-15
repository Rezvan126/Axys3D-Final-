#!/usr/bin/env bash
# Portfolio pieces from the studio's own residence scene:
#   - the four new stills (render-portfolio.py) as web images adu-9 .. adu-12
#   - one exterior film cut from the four cinematic shots (render-final-shot.py and render-clip.py),
#     with a short silent preview and a poster frame for the work tiles
#   bash tools/make-portfolio.sh
set -e
cd "$(dirname "$0")/.."
S=assets-src/gellert
O=public/media

# ---- stills: a gentle grade to match the films, then two sizes ----
n=9
for v in garden balcony approach corner meadow doors window upper; do   # corner (adu-12) is not used on the site
  G="eq=contrast=1.06:saturation=1.1:gamma=0.98,colorbalance=rs=-0.02:bs=0.03:rh=0.04:bh=-0.04,unsharp=5:5:0.5"
  ffmpeg -v error -y -i "$S/portfolio/$v.jpg" -vf "scale=1920:1080:flags=lanczos,$G" -c:v libwebp -q:v 80 "$O/adu-$n.webp"
  ffmpeg -v error -y -i "$S/portfolio/$v.jpg" -vf "scale=800:450:flags=lanczos,$G" -c:v libwebp -q:v 76 "$O/adu-$n-sm.webp"
  n=$((n + 1))
done

# ---- film: grade each shot the same way, then dissolve them together ----
W=1600; H=670
GRADE="scale=$W:$H:flags=lanczos,eq=contrast=1.09:saturation=1.14:gamma=0.97,colorbalance=rs=-0.035:bs=0.055:rm=0.015:bm=-0.01:rh=0.06:gh=0.015:bh=-0.07,split[base][glow];[glow]curves=all='0/0 0.62/0 1/1',gblur=sigma=26[g];[base][g]blend=all_mode=screen:all_opacity=0.32,vignette=PI/4.6,noise=alls=5:allf=t,format=yuv420p"
for c in wide garden hero detail; do
  ffmpeg -v error -y -framerate 24 -start_number 1 -i "$S/film/$c/%04d.jpg" -filter_complex "[0:v]$GRADE[v]" -map "[v]" -c:v libx264 -crf 14 -preset fast "$S/film/pf-$c.mp4"
done
# wide 8s, garden 8s, hero 10s, detail 8s, one second dissolves
ffmpeg -v error -y -i "$S/film/pf-wide.mp4" -i "$S/film/pf-garden.mp4" -i "$S/film/pf-hero.mp4" -i "$S/film/pf-detail.mp4" -filter_complex "\
[0][1]xfade=transition=fade:duration=1:offset=7[a];\
[a][2]xfade=transition=fade:duration=1:offset=14[b];\
[b][3]xfade=transition=fade:duration=1:offset=23,fade=t=in:st=0:d=0.6,fade=t=out:st=30.2:d=0.8,scale=1280:536[v]" \
  -map "[v]" -an -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart "$O/exterior-full.mp4"
# hover preview: six seconds from the garden and hero shots, small
ffmpeg -v error -y -ss 8 -t 6 -i "$O/exterior-full.mp4" -vf "scale=960:402" -an -c:v libx264 -preset slow -crf 28 -pix_fmt yuv420p -movflags +faststart "$O/exterior.mp4"
# poster: 16:9 crop from the end of the hero shot
ffmpeg -v error -y -ss 22.5 -i "$O/exterior-full.mp4" -frames:v 1 -vf "crop=1191:670,scale=1600:900:flags=lanczos" -c:v libwebp -q:v 80 "$O/exterior.webp"
ffmpeg -v error -y -i "$O/exterior.webp" -vf scale=800:450 -c:v libwebp -q:v 76 "$O/exterior-sm.webp"
ls -l $O/exterior* $O/adu-9* $O/adu-1[0-2]* | awk '{print $5, $9}'
