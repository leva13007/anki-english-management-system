# #!/bin/bash

# INPUT_DIR="s1/e1/tracks"
# OUTPUT_DIR="converted_webm"
# mkdir -p "$OUTPUT_DIR"

# counter=91

# # Збираємо файли у відсортованому алфавітному порядку
# files=$(find "$INPUT_DIR" -maxdepth 1 -type f -name "*.mov" | sort)

# for file in $files; do
#   index=$(printf "%04d" $counter)
#   output="$OUTPUT_DIR/sherlok_$index.webm"

#   echo "🎞️ Обробка: $(basename "$file") → $(basename "$output")"

#   ffmpeg -i "$file" \
#     -vf "crop=iw-80:ih-60, hflip, hue=s=0.5, scale=500:-2" \
#     -c:v libvpx-vp9 -b:v 500k -c:a libopus \
#     -y "$output"

#   ((counter++))
# done

# echo "✅ Готово! Всі файли збережено в $OUTPUT_DIR"

#!/bin/bash

INPUT_DIR="../tracks"
OUTPUT_DIR="../converted_webm"
mkdir -p "$OUTPUT_DIR"

# silicon_valley_0380.webm
counter=381

for file in "$INPUT_DIR"/*.mov; do
  # Створюємо імʼя з ведучими нулями: 0001, 0002, ...
  index=$(printf "%04d" $counter)
  output="$OUTPUT_DIR/silicon_valley_$index.webm"

  echo "🎞️ Обробка: $(basename "$file") → $output"

  # ffmpeg -i "$file" \
  #   -vf "crop=iw-80:ih-60, hflip, hue=s=0.3, scale=500:-2" \
  #   -c:v libvpx-vp9 -b:v 500k -c:a libopus \
  #   -y "$output"

  # ffmpeg -i "$file" \
  #   -vf "
  #     crop=iw-80:ih-60,
  #     hflip,
  #     scale=503:-2,
  #     fps=18,
  #     setpts=1.08*PTS,
  #     noise=alls=8:allf=t,
  #     hue=s=0.25,
  #     boxblur=1:1
  #   " \
  #   -c:v libvpx-vp9 -b:v 450k \
  #   -y "$output"


  ffmpeg -i "$file" -loop 1 -i watermark.png \
  -filter_complex "
    [0:v]crop=iw-80:ih-60,hflip,scale=503:-2,fps=18,setpts=1.08*PTS,noise=alls=8:allf=t,hue=s=0.25,boxblur=1:1[v];
    [v][1:v]overlay=(W-w)/2:(H-h)/2:shortest=1[out]
  " \
  -map "[out]" -map 0:a? \
  -c:v libvpx-vp9 -b:v 450k -c:a libopus \
  -y "$output"

  ((counter++))
done

echo "✅ Готово! Всі файли збережено в $OUTPUT_DIR"