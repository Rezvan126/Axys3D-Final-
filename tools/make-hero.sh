#!/usr/bin/env bash
# The home page hero film: the Cycles hero shot, graded, made into a seamless loop
# (the last second dissolves into the first), in a wide version and an upright one for phones.
#   bash tools/make-hero.sh
set -e
cd "$(dirname "$0")/.."
F=assets-src/gellert/film/hero
O=public/media
G="eq=contrast=1.09:saturation=1.14:gamma=0.97,colorbalance=rs=-0.035:bs=0.055:rm=0.015:bm=-0.01:rh=0.06:gh=0.015:bh=-0.07,split[base][glow];[glow]curves=all='0/0 0.62/0 1/1',gblur=sigma=26[g];[base][g]blend=all_mode=screen:all_opacity=0.32,vignette=PI/4.6"
LOOP="split=3[a][b][c];[a]trim=9:10,setpts=PTS-STARTPTS[t];[b]trim=0:1,setpts=PTS-STARTPTS[h];[c]trim=1:9,setpts=PTS-STARTPTS[m];[t][h]xfade=transition=fade:duration=1:offset=0[x];[x][m]concat=n=2:v=1,format=yuv420p[v]"
# wide: laptops and desktops
ffmpeg -v error -y -framerate 24 -start_number 1 -i "$F/%04d.jpg" -filter_complex "[0:v]scale=1720:720:flags=lanczos,$G,$LOOP" -map "[v]" -an -c:v libx264 -preset veryslow -crf 30 -movflags +faststart "$O/hero-film.mp4"
# upright: phones. The house sits right of centre in the frame, so the crop is taken there.
ffmpeg -v error -y -framerate 24 -start_number 1 -i "$F/%04d.jpg" -filter_complex "[0:v]$G,crop=540:720:700:0,$LOOP" -map "[v]" -an -c:v libx264 -preset veryslow -crf 30 -movflags +faststart "$O/hero-film-tall.mp4"
# posters: the first frame of each loop, so the film takes over from the still without a jump
ffmpeg -v error -y -i "$O/hero-film.mp4" -frames:v 1 -c:v libwebp -q:v 78 "$O/hero-film.webp"
ffmpeg -v error -y -i "$O/hero-film.webp" -vf scale=900:-2 -c:v libwebp -q:v 74 "$O/hero-film-sm.webp"
ffmpeg -v error -y -i "$O/hero-film-tall.mp4" -frames:v 1 -c:v libwebp -q:v 78 "$O/hero-film-tall.webp"
ls -l $O/hero-film* | awk '{print $5, $9}'
