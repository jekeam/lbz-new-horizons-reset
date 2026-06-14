# Инструкция публикации

Эта инструкция нужна для последующих публикаций репозитория и релиза. Ничего не копировать в `C:\Games\Tanki`, если пользователь прямо не попросил.

## 1. Проверить состояние

```powershell
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" status --short
gh auth status
```

Если `gh auth status` в sandbox показывает старый токен, проверять через escalated shell от пользователя.

## 2. Собрать релиз

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

Проверить, что архив содержит путь для распаковки в корень игры:

```text
mods/1.43.0.0/lbz_new_horizons_reset_1.43.mtmod
```

Релизный ZIP:

```text
release/1.43/lbz-new-horizons-reset.zip
```

## 3. Закоммитить

```powershell
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" add -- README.md PUBLISHING.md scripts/build_release.ps1 mod_lbz_dynamic_reset.py docs/panel-screenshot.png
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" add -f -- release/1.43/lbz-new-horizons-reset.zip
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" commit -m "Краткое описание изменения"
```

Если изменился только README, релизный ZIP пересобирать и добавлять не нужно.

## 4. Запушить

```powershell
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" push origin master
```

## 5. Обновить тег релиза

Тег должен быть через точку:

```text
1.43
```

Если изменился релизный ZIP или код мода:

```powershell
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" tag -f -a "1.43" -m "Релиз 1.43"
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" push -f origin "1.43"
```

Если менялся только README, тег не двигать.

## 6. Обновить GitHub Release

Если release уже существует:

```powershell
gh release upload "1.43" "release/1.43/lbz-new-horizons-reset.zip" --repo jekeam/lbz-new-horizons-reset --clobber
```

Если release ещё не создан:

```powershell
gh release create "1.43" "release/1.43/lbz-new-horizons-reset.zip" --repo jekeam/lbz-new-horizons-reset --title "1.43" --notes "Релиз для Мир Танков 1.43.0.0. Архив распаковывается в корень игры и содержит mods/1.43.0.0/lbz_new_horizons_reset_1.43.mtmod."
```

## 7. Проверить

```powershell
gh release view "1.43" --repo jekeam/lbz-new-horizons-reset --json tagName,url,assets
git -c safe.directory="C:/Users/jekeam/Documents/Tanki Mods" status --short
```
