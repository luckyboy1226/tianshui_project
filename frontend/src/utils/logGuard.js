const noop = () => {}

export function installProductionLogGuard() {
  if (import.meta.env.DEV) return

  console.log = noop
  console.debug = noop
  console.info = noop
}
