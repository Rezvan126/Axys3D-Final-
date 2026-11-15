#!/usr/bin/env bash
# Grades and encodes the amber house renders for the site. Same treatment as the ADU pieces:
# stills as in make-portfolio.sh, clips as in make-clips.sh.
#   bash tools/make-amber.sh            stills and clips
#   bash tools/make-amber.sh stills     only the six stills
#   bash tools/make-amber.sh clips      only the three clips and their posters
# Inputs:  assets-src/amber/renders/stills/<view>.jpg   (tools/amber-stills.py)
#          assets-src/amber/renders/film/<shot>/%04d.jpg (tools/amber-clip.py)
set -e
cd "$(dirname "$0")/.."
S=assets-src/amber/renders
O=public/media
WHAT=${1:-all}
# -map_metadata -1: nothing from the render machine travels with the files

if [ "$WHAT" != clips ]; then
  n=1
  G="eq=contrast=1.06:saturation=1.1:gamma=0.98,colorbalance=rs=-0.02:bs=0.03:rh=0.04:bh=-0.04,unsharp=5:5:0.5"
  for v in hero low34 entry upper wide uphill; do
    ffmpeg -v error -y -i "$S/stills/$v.jpg" -vf "scale=1920:1080:flags=lanczos,$G" -map_metadata -1 -c:v libwebp -q:v 80 "$O/amber-$n.webp"
    ffmpeg -v error -y -i "$S/stills/$v.jpg" -vf "scale=800:450:flags=lanczos,$G" -map_metadata -1 -c:v libwebp -q:v 76 "$O/amber-$n-sm.webp"
    n=$((n + 1))
  done
fi

if [ "$WHAT" != stills ]; then
  W=1280; H=536
  for n in hero wide detail; do
    ffmpeg -v error -y -framerate 24 -start_number 1 -i "$S/film/$n/%04d.jpg" -filter_complex "\
[0:v]scale=$W:$H:flags=lanczos,eq=contrast=1.09:saturation=1.14:gamma=0.97,\
colorbalance=rs=-0.035:bs=0.055:rm=0.015:bm=-0.01:rh=0.06:gh=0.015:bh=-0.07,split[base][glow];\
[glow]curves=all='0/0 0.62/0 1/1',gblur=sigma=22[g];\
[base][g]blend=all_mode=screen:all_opacity=0.32,vignette=PI/4.6,noise=alls=2:allf=t,format=yuv420p[v]" \
      -map "[v]" -an -map_metadata -1 -c:v libx264 -preset veryslow -crf 29 -pix_fmt yuv420p -movflags +faststart "$O/amber-film-$n.mp4"
    # poster: the first frame of the encoded clip, so the film takes over from the still without a jump
    ffmpeg -v error -y -i "$O/amber-film-$n.mp4" -frames:v 1 -map_metadata -1 -c:v libwebp -q:v 78 "$O/amber-film-$n.webp"
  done
fi
ls -l $O/amber-* | awk '{print $5, $9}'
