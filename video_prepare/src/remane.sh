#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="../tracks"
cd "$INPUT_DIR"

for file in *.mov; do
  # Витягуємо перший токен (число перед пробілом)
  num=$(echo "$file" | awk -F' ' '{print $1}')
  # Інтерпретуємо як десяткове число (10#)
  num_dec=$((10#$num))
  # Форматуємо у 4 цифри
  num_padded=$(printf "%04d" "$num_dec")
  new="${num_padded}.mov"

  echo "🔄 $file → $new"
  mv -i -- "$file" "$new"
done

echo "✅ Перейменування завершено!"




# #!/usr/bin/env bash
# set -euo pipefail

# INPUT_DIR="./s1/e1/tracks"

# cd "$INPUT_DIR"

# for file in *.mov; do
#   # Витягуємо число без розширення
#   num="${file%.mov}"
#   # Форматуємо у 4 цифри (0091, 0100, 0132)
#   num_padded=$(printf "%04d" "$num")
#   new="${num_padded}.mov"

#   echo "🔄 $file → $new"
#   mv -i -- "$file" "$new"
# done

# echo "✅ Перейменування завершено!"



# #!/usr/bin/env bash
# set -euo pipefail

# INPUT_DIR="./s1/e1/tracks"

# cd "$INPUT_DIR"

# for file in *" - 720WebShareName.mov"; do
#   # Витягуємо число на початку (до пробілу)
#   num=$(echo "$file" | cut -d' ' -f1)
#   new="${num}.mov"

#   echo "🔄 $file → $new"
#   mv -i -- "$file" "$new"
# done

# echo "✅ Перейменування завершено!"
