import type { ReactElement } from 'react';
import { Trans } from 'react-i18next';
import { Link } from 'react-router';

import type { LineageAncestor } from '../api/marketplace';
import { publicTemplatePath } from '../constants/routes';
import { textLinkClassName } from './ui/text-link';

type LineageKey =
  | 'lineage.copiedFrom'
  | 'lineage.copiedFromWithoutOwner'
  | 'lineage.itselfCopiedFrom'
  | 'lineage.itselfCopiedFromWithoutOwner';

function lineageKey(first: boolean, ancestor: LineageAncestor): LineageKey {
  if (first) {
    return ancestor.owner_name === null ? 'lineage.copiedFromWithoutOwner' : 'lineage.copiedFrom';
  }
  return ancestor.owner_name === null
    ? 'lineage.itselfCopiedFromWithoutOwner'
    : 'lineage.itselfCopiedFrom';
}

function ancestorName(ancestor: LineageAncestor): ReactElement {
  if (ancestor.template_id === null) return <span className="text-foreground" />;
  return <Link to={publicTemplatePath(ancestor.template_id)} className={textLinkClassName} />;
}

export function TemplateLineage({ lineage }: { lineage: LineageAncestor[] }) {
  return (
    <span>
      {lineage.map((ancestor: LineageAncestor, index: number) => (
        <Trans
          key={`${index}-${ancestor.name}`}
          i18nKey={lineageKey(index === 0, ancestor)}
          values={{ name: ancestor.name, owner: ancestor.owner_name ?? '' }}
          components={{ name: ancestorName(ancestor) }}
        />
      ))}
    </span>
  );
}
