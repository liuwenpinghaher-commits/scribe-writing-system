export function resolveWorkSlugByExactTitle(works, bookTitle) {
  return works.find((work) => work?.title === bookTitle)?.slug || ''
}
