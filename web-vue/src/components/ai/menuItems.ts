import type { ActionMenuItem } from 'nanocat-ui'

export type ActionMenuGroup = ActionMenuItem[]

export function actionMenuGroups(...groups: ActionMenuGroup[]): ActionMenuItem[] {
  return groups
    .filter((group) => group.length > 0)
    .flatMap((group, groupIndex) => (
      group.map((item, itemIndex) => ({
        ...item,
        dividerBefore: Boolean(item.dividerBefore || (groupIndex > 0 && itemIndex === 0)),
      }))
    ))
}
