import { ICONS, DEFAULT_ICON } from './iconList'

export function MenuIcon({ name, ...props }) {
  const Cmp = ICONS[name] || DEFAULT_ICON
  return <Cmp {...props} />
}
