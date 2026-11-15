#!/usr/bin/env bash
# Film grade and encode for the amber house film (frames from tools/amber-cine-render.py).
#   bash tools/make-amber-cine.sh            all four shots, the cut, the master and posters
#   bash tools/make-amber-cine.sh a b        only those shots (the cut is rebuilt from whatever graded shots exist)
# Grade, in order: gentle contrast, split tone (teal shadows, warm highlights), halation (warm glow off the
# highlights only), chromatic aberration that grows towards the frame edges (the colour planes are scaled about
# the centre, so the centre stays clean), soft vignette, fine moving grain. Native frame is 1920x804 (2.39:1).
set -e
cd "$(dirname "$0")/.."
F=assets-src/amber/renders/film2
O=public/media
M=assets-src/amber/renders
W=1920; H=804
SHOTS=${@:-a b c d stills}

# grade W H [grain]: the film look for a frame of that size
grade() {
  local w=$1 h=$2 g=${3:-5}
  echo "format=gbrp,split=3[r0][g0][b0];[r0]extractplanes=r,scale=$((w * 10026 / 10000)):$((h * 10026 / 10000)),crop=$w:$h,setsar=1[r];[g0]extractplanes=g,scale=$((w * 10013 / 10000)):$((h * 10013 / 10000)),crop=$w:$h,setsar=1[g];[b0]extractplanes=b,setsar=1[b];[g][b][r]mergeplanes=0x001020:gbrp,format=rgb24,eq=contrast=1.07:saturation=1.06:gamma=0.98,colorbalance=rs=-0.04:gs=-0.005:bs=0.05:rm=0.01:bm=-0.01:rh=0.05:gh=0.012:bh=-0.055,split[base][glow];[glow]curves=all='0/0 0.70/0 1/1',gblur=sigma=20,colorchannelmixer=rr=1.0:gg=0.62:bb=0.32[g2];[base][g2]blend=all_mode=screen:all_opacity=0.24,vignette=PI/5.2,noise=alls=$g:allf=t+u,format=yuv420p"
}
GRADE=$(grade $W $H 5)

for n in $SHOTS; do
  if [ "$n" = stills ]; then
    # six stills (tools/amber-cine-stills.py), same look, 1920x1080 and 800x450
    i=1
    for v in s1 s2 s3 s4 s5 s6; do
      [ -f "$M/cine-stills/$v.jpg" ] || continue
      ffmpeg -v error -y -i "$M/cine-stills/$v.jpg" -filter_complex "[0:v]scale=1920:1080:flags=lanczos,$(grade 1920 1080 3)[v]" -map "[v]" -map_metadata -1 -c:v libwebp -q:v 82 "$O/amber-$v.webp"
      ffmpeg -v error -y -i "$O/amber-$v.webp" -vf "scale=800:450:flags=lanczos" -map_metadata -1 -c:v libwebp -q:v 78 "$O/amber-$v-sm.webp"
    done
    continue
  fi
  # graded intermediate at full size, near lossless, used for the cut and the master
  ffmpeg -v error -y -framerate 24 -start_number 1 -i "$F/$n/%04d.jpg" -filter_complex "[0:v]$GRADE[v]" -map "[v]" \
    -an -map_metadata -1 -c:v libx264 -preset slow -crf 12 -pix_fmt yuv420p "$M/cine-graded-$n.mp4"
  # web clip: 1280x536, silent, faststart
  ffmpeg -v error -y -i "$M/cine-graded-$n.mp4" -vf "scale=1280:536:flags=lanczos" -an -map_metadata -1 \
    -c:v libx264 -preset veryslow -crf 25 -pix_fmt yuv420p -movflags +faststart "$O/amber-cine-$n.mp4"
  # poster: the first frame, so the clip takes over from the still without a jump
  ffmpeg -v error -y -i "$O/amber-cine-$n.mp4" -frames:v 1 -map_metadata -1 -c:v libwebp -q:v 80 "$O/amber-cine-$n.webp"
done

# the 40 s film: four 10 s shots joined with half second dissolves (38.5 s), faded in and out
if [ -f "$M/cine-graded-a.mp4" ] && [ -f "$M/cine-graded-b.mp4" ] && [ -f "$M/cine-graded-c.mp4" ] && [ -f "$M/cine-graded-d.mp4" ]; then
  CUT="[0][1]xfade=transition=fade:duration=0.5:offset=9.5[x1];[x1][2]xfade=transition=fade:duration=0.5:offset=19[x2];\
[x2][3]xfade=transition=fade:duration=0.5:offset=28.5,fade=t=in:st=0:d=0.6,fade=t=out:st=37.7:d=0.8"
  # master for the portfolio: 1080p, letterboxed 2.39:1, high bitrate
  ffmpeg -v error -y -i "$M/cine-graded-a.mp4" -i "$M/cine-graded-b.mp4" -i "$M/cine-graded-c.mp4" -i "$M/cine-graded-d.mp4" \
    -filter_complex "$CUT,pad=1920:1080:0:138:black,format=yuv420p[v]" -map "[v]" -an -map_metadata -1 \
    -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart "$M/amber-cine-master.mp4"
  # web cut
  ffmpeg -v error -y -i "$M/cine-graded-a.mp4" -i "$M/cine-graded-b.mp4" -i "$M/cine-graded-c.mp4" -i "$M/cine-graded-d.mp4" \
    -filter_complex "$CUT,scale=1280:536:flags=lanczos,format=yuv420p[v]" -map "[v]" -an -map_metadata -1 \
    -c:v libx264 -preset veryslow -crf 26 -pix_fmt yuv420p -movflags +faststart "$O/amber-cine.mp4"
fi
ls -l $O/amber-cine* $M/amber-cine-master.mp4 2>/dev/null | awk '{print $5, $9}'
