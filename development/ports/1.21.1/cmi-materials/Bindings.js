// priority: 100

const Cmi = {
  MODID: 'cmi',
  loadResource(path) {
    return `cmi:${path}`
  },
  applyModel(model, source) {
    model.parent(source.parent)
    if (source.textures) model.textures(source.textures)
  }
}
