#!/usr/bin/env bash
# Cuts the "one building, every stage" film from the rendered frames (see render-film.py and
# render-final-shot.py) and writes the web versions into public/media.
#   bash tools/make-film.sh
set -e
cd "$(dirname "$0")/.."
F=assets-src/gellert/film
O=public/media
W=1280; H=536        # 2.39:1 widescreen

# the four stage looks: crop to widescreen, a soft vignette and a little grain so they sit with the final shot
pass() { ffmpeg -v error -y -framerate 24 -start_number "$2" -i "$F/$1/%04d.jpg" \
  -vf "crop=1600:670,scale=$W:$H:flags=lanczos,vignette=PI/6,noise=alls=4:allf=t,format=yuv420p" -c:v libx264 -crf 14 -preset fast "$F/$1.mp4"; }
pass sketch 0; pass clay 72; pass bim 156; pass mat 240

# the hero shot: film grade. Lifted contrast, cool shadows and warm highlights, bloom on the bright
# areas, a vignette and fine grain.
ffmpeg -v error -y -framerate 24 -start_number 1 -i "$F/hero/%04d.jpg" -filter_complex "\
[0:v]scale=$W:$H:flags=lanczos,eq=contrast=1.09:saturation=1.14:gamma=0.97,\
colorbalance=rs=-0.035:bs=0.055:rm=0.015:bm=-0.01:rh=0.06:gh=0.015:bh=-0.07,split[base][glow];\
[glow]curves=all='0/0 0.62/0 1/1',gblur=sigma=22[g];\
[base][g]blend=all_mode=screen:all_opacity=0.32,vignette=PI/4.6,noise=alls=7:allf=t,\
fade=t=out:st=9.4:d=0.6,format=yuv420p[v]" -map "[v]" -c:v libx264 -crf 14 -preset fast "$F/hero.mp4"

# dissolve the stages into each other, then into the hero shot
ffmpeg -v error -y -i "$F/sketch.mp4" -i "$F/clay.mp4" -i "$F/bim.mp4" -i "$F/mat.mp4" -i "$F/hero.mp4" -filter_complex "\
[0][1]xfade=transition=fade:duration=1:offset=3[a];\
[a][2]xfade=transition=fade:duration=1:offset=6.5[b];\
[b][3]xfade=transition=fade:duration=1:offset=10[c];\
[c][4]xfade=transition=fade:duration=1.2:offset=12.8,fade=t=in:st=0:d=0.5[v]" \
  -map "[v]" -an -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p -movflags +faststart "$O/stages-film.mp4"

# poster: a frame from the hero shot
ffmpeg -v error -y -ss 20 -i "$O/stages-film.mp4" -frames:v 1 -c:v libwebp -q:v 80 "$O/stages-film.webp"
ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$O/stages-film.mp4"
