# Sticker pack manager
This is a python project meant to make organizing telegram stickers much easier.
It allows to save sticker packs sent to a bot, then, with a web UI, you can delete them and
create custom sticker packs out of them.

---

## TO-DO List:
- Implement signal sticker pack uploads
- Flags in the packs page to show whether a sticker has been uploaded to signal and/or is present in a custom pack
  - A custom pack contains a sticker pack if any sticker from the pack is present in the custom one
  - If already uploaded, just show link to signal sticker
  - If in custom pack, move to custom packs and show pack
- Improve export to json (maybe exporting everything within a zip?)
  - Make it work properly with both individual packs, custom ones and entire database
