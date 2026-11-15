#!/usr/bin/env bash
# Grades and encodes the cinematic clips shown in the last stage of the interactive building
# (frames from render-final-shot.py and render-clip.py). Same film grade for all three angles.
#   bash tools/make-clips.sh [hero wide detail]
set -e
cd "$(dirname "$0")/.."
F=assets-src/gellert/film
O=public/media
W=1280; H=536
for n in ${@:-hero wide detail}; do
  ffmpeg -v error -y -framerate 24 -start_number 1 -i "$F/$n/%04d.jpg" -filter_complex "\
[0:v]scale=$W:$H:flags=lanczos,eq=contrast=1.09:saturation=1.14:gamma=0.97,\
colorbalance=rs=-0.035:bs=0.055:rm=0.015:bm=-0.01:rh=0.06:gh=0.015:bh=-0.07,split[base][glow];\
[glow]curves=all='0/0 0.62/0 1/1',gblur=sigma=22[g];\
[base][g]blend=all_mode=screen:all_opacity=0.32,vignette=PI/4.6,noise=alls=2:allf=t,format=yuv420p[v]" \
    -map "[v]" -an -c:v libx264 -preset veryslow -crf 29 -pix_fmt yuv420p -movflags +faststart "$O/adu-film-$n.mp4"
  ls -l "$O/adu-film-$n.mp4" | awk '{print $5, $9}'
done
