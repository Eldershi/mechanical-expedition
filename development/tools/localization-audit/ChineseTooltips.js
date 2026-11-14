// Translate native literal tooltip components while retaining their styles and siblings.
let ExpeditionTooltipSerializer = Java.loadClass('net.minecraft.network.chat.Component$Serializer')
let expeditionLiteralTooltips = JSON.parse(String(JsonIO.readJson('kubejs/config/expedition-literal-translations.json')))
let expeditionLiteralPatterns = expeditionLiteralTooltips.patterns.map(rule => ({
  expression: new RegExp(rule.pattern, rule.flags || ''), replacement: rule.replacement
}))

function expeditionTranslateLiteral(text) {
  if (Object.prototype.hasOwnProperty.call(expeditionLiteralTooltips.exact, text)) {
    return expeditionLiteralTooltips.exact[text]
  }
  for (let index = 0; index < expeditionLiteralPatterns.length; index++) {
    let rule = expeditionLiteralPatterns[index]
    rule.expression.lastIndex = 0
    if (rule.expression.test(text)) {
      rule.expression.lastIndex = 0
      return text.replace(rule.expression, rule.replacement)
    }
  }
  return text
}

function expeditionTranslateTooltipTree(value) {
  let changed = false
  if (Array.isArray(value)) {
    value.forEach((entry, index) => {
      if (typeof entry === 'string') {
        let translated = expeditionTranslateLiteral(entry)
        if (translated !== entry) { value[index] = translated; changed = true }
      } else if (expeditionTranslateTooltipTree(entry)) changed = true
    })
  } else if (value != null && typeof value === 'object') {
    // Some rarity labels consist of separately colored glyph components.
    // Sample their original gradient for the translated glyphs.
    if (value.text === '' && Array.isArray(value.extra) && value.extra.length > 1) {
      let styles = ['text', 'color', 'font', 'bold', 'italic', 'underlined', 'strikethrough', 'obfuscated']
      let simple = value.extra.every(part => part != null && typeof part === 'object' &&
        typeof part.text === 'string' && part.text.length === 1 &&
        Object.keys(part).every(key => styles.indexOf(key) >= 0))
      if (simple) {
        let original = value.extra.map(part => part.text).join('')
        let translated = expeditionTranslateLiteral(original)
        if (translated !== original) {
          let glyphs = translated.split('')
          let source = value.extra
          value.extra = glyphs.map((glyph, index) => {
            let sample = glyphs.length < 2 ? 0 : Math.round(index * (source.length - 1) / (glyphs.length - 1))
            let part = JSON.parse(JSON.stringify(source[sample]))
            part.text = glyph
            if (typeof part.font === 'string' && /^lethality:/.test(part.font)) part.font = 'minecraft:default'
            return part
          })
          changed = true
        }
      }
    }
    if (typeof value.text === 'string') {
      let translated = expeditionTranslateLiteral(value.text)
      if (translated !== value.text) {
        value.text = translated
        if (typeof value.font === 'string' && /^lethality:/.test(value.font)) value.font = 'minecraft:default'
        changed = true
      }
    }
    Object.keys(value).forEach(key => {
      if (key !== 'text' && expeditionTranslateTooltipTree(value[key])) changed = true
    })
  }
  return changed
}

// The startup listener runs after mods finish adding their tooltip lines.
// Replacing this function also refreshes the transform on client-script reload.
global.expeditionTranslateTooltipLines = tooltip => {
  if (String(Client.options.languageCode) !== 'zh_cn') return
  for (let index = 0; index < tooltip.size(); index++) {
    let tree = JSON.parse(String(ExpeditionTooltipSerializer.toJson(tooltip.get(index))))
    if (expeditionTranslateTooltipTree(tree)) {
      tooltip.set(index, ExpeditionTooltipSerializer.fromJsonLenient(JSON.stringify(tree)))
    }
  }
}
