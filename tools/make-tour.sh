#!/usr/bin/env bash
# Virtual tour pictures for the Work page, from the studio's Revit model.
#   bash tools/make-tour.sh            grade and export what is already rendered
#   bash tools/make-tour.sh render     build the scene, render the six panoramas, then export
#
# Before the first render on a new machine, fetch the free BlenderKit assets once (uses the owner's
# logged in add-on; free assets only). The ids are listed in HANDOFF.md and in assets-src/amber/tour/bkit-assets.json:
#   blender -b -P tools/tour-bkit.py -- get <asset_base_id> ...
#
# Steps (the first three only with "render"):
#   1. tools/tour-scene.py   FBX -> assets-src/amber/tour-base.blend (finish classes, light, ceiling lamps, set)
#   2. tools/tour-dress.py   tour-base.blend -> tour.blend (BlenderKit materials, staging, open doors, neighbours, HDRI)
#   3. tools/tour-render.py  4096x2048 equirectangular PNGs into assets-src/amber/tour/
#   4. a gentle grade to sit with the other stills (no vignette or glow: they would show at the seam),
#      then public/media/tour/<room>.webp (4096x2048), <room>-sm.webp (2048x1024) and a flat poster
#   5. src/data/tour.json    rooms, hotspot directions and start views
set -e
cd "$(dirname "$0")/.."
B="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.1/blender.exe}"
S="$PWD/assets-src/amber/tour"
O=public/media/tour
ROOMS="entry living kitchen bedroom bathroom deck"
mkdir -p "$S" "$O"

if [ "$1" = "render" ]; then
  "$B" -b --factory-startup -P tools/tour-scene.py -- assets-src/amber/navis/amber.fbx assets-src/amber/tour-base.blend > "$S/scene.log" 2>&1
  grep -E "PRIVACY|TOUR_SCENE_OK" "$S/scene.log"
  "$B" -b --factory-startup assets-src/amber/tour-base.blend -P tools/tour-dress.py -- assets-src/amber/tour.blend > "$S/dress.log" 2>&1
  grep -E "DRESS" "$S/dress.log"
  "$B" -b assets-src/amber/tour.blend -P tools/tour-render.py -- final "$S" > "$S/final.log" 2>&1
  grep PANO_OK "$S/final.log"
fi

G="eq=contrast=1.09:saturation=1.07:gamma=0.97,colorbalance=rs=-0.015:bs=0.03:rh=-0.012:bh=0.02,unsharp=5:5:0.45"
for r in $ROOMS; do
  ffmpeg -v error -y -i "$S/$r.png" -vf "$G" -c:v libwebp -q:v "${TOUR_Q:-90}" -compression_level 6 "$O/$r.webp"
  ffmpeg -v error -y -i "$S/$r.png" -vf "scale=2048:1024:flags=lanczos,$G" -c:v libwebp -q:v 88 -compression_level 6 "$O/$r-sm.webp"
done
# poster: a flat 16:9 look at the living room, cut from its panorama
ffmpeg -v error -y -i "$S/living.png" -vf "v360=input=e:output=flat:yaw=${POSTER_YAW:-78}:pitch=${POSTER_PITCH:--6}:h_fov=108:v_fov=74:w=1600:h=900:interp=lanczos,$G" -frames:v 1 -c:v libwebp -q:v 80 "$O/poster.webp"
ffmpeg -v error -y -i "$O/poster.webp" -vf scale=800:450:flags=lanczos -c:v libwebp -q:v 76 "$O/poster-sm.webp"

"$B" -b assets-src/amber/tour.blend -P tools/tour-render.py -- json "$PWD/src/data/tour.json" 2>&1 | grep TOUR_JSON_OK
ls -l $O | awk '{print $5, $9}'
